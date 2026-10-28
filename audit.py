"""Check a built wiki against the doc it came from.

    python build.py --out site --cache .cache && python audit.py site .cache

Reports, per page: doc text missing from the page, pictures lost, markdown symbols left in the text,
headings repeated on one page, picture labels with no pictures, and broken links or image files.
"""
import difflib
import html
import json
import re
import sys
from pathlib import Path

site, cache = Path(sys.argv[1]), Path(sys.argv[2])
tabs = json.loads((cache / "tabs.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(Path(__file__).parent))
from build import norm, plain, slugify  # noqa: E402

pages = {p.name: p.read_text(encoding="utf-8") for p in site.glob("*.html")}
problems = 0


def report(page, kind, detail):
    global problems
    problems += 1
    print(f"{page:45} {kind:18} {detail}")


for t in tabs:
    if not t["md"].strip():
        continue
    first = next((plain(m) for m in re.findall(r"^#{1,6}\s+(.+)$", t["md"], re.M) if plain(m)), None)
    title = t["title"] or first or "Introduction"
    name = ("introduction" if t["id"] == "t.0" else slugify(title)) + ".html"
    page = pages.get(name)
    if page is None:
        report(name, "missing page", title)
        continue
    article = page[page.find("<article"):page.find("</article>")]
    text = norm(html.unescape(re.sub(r"<[^>]+>", " ", article)))

    # 1. every line of the doc's text shows up on the page
    for line in t["md"].splitlines():
        if line.startswith("[image") or "data:image" in line:
            continue
        line = re.sub(r"\]\([^)]*\)", "]", line)  # a link's address isn't on the page, its words are
        key = norm(plain(re.sub(r"^\s*(#+|[*+-]|\d+\.)\s+", "", line)))
        if len(key) >= 12 and key not in text:
            report(name, "text missing", line.strip()[:90])

    # 2. pictures: as many on the page as in the doc
    want = len({uri for _, uri in t.get("imgs", [])}) if t.get("imgs") is not None else len(re.findall(r"^\[image\d+\]:", t["md"], re.M))
    got = len(set(re.findall(r'<img loading="lazy" alt="" src="([^"]+)"', article)))
    if got != want:
        report(name, "picture count", f"doc {want}, page {got}")

    # 3. markdown symbols that leaked into the reading text
    visible = html.unescape(re.sub(r"<[^>]+>", " ", article))
    for m in re.finditer(r".{0,30}(\*\*|\\[-\[\]>*_]|(?<![\w])\*(?=\w)|__).{0,30}", visible):
        report(name, "markdown symbols", m.group(0).strip())

    # 4. the same heading twice on one page (search and contents links get ambiguous)
    # only top-level sections: tier names repeat legitimately under different trees
    heads = [html.unescape(re.sub(r"<[^>]+>", "", h)).strip() for h in re.findall(r"<h2[^>]*>(.*?)</h2>", article)]
    seen = {}
    for h in heads:
        seen[h.lower()] = seen.get(h.lower(), 0) + 1
    for h, n in seen.items():
        if n > 1:
            report(name, "repeated heading", f"{h!r} x{n}")

    # 5. picture labels ("... Examples:") with no pictures after them, and near-duplicate labels
    labels = re.findall(r"<p>(?:<strong>)?([^<]{3,60}:)(?:</strong>)?</p>\s*(<figure)?", article)
    for i, (label, fig) in enumerate(labels):
        if not fig and re.search(r"example|reference|appearance|appearence", label, re.I):
            report(name, "label, no pictures", label)
    for i, (a, fa) in enumerate(labels):
        for b, fb in labels[i + 1:]:
            if a != b and not (fa and fb) and re.search(r"example|reference|appear", a + b, re.I) and difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() > 0.9:
                report(name, "near-duplicate", f"{a!r} / {b!r}")

# 6. links and files
for name, page in pages.items():
    for href in re.findall(r'href="([^"#:]+\.html)(?:#([^"]+))?"', page):
        target, frag = href
        if target not in pages:
            report(name, "broken link", target)
        elif frag and f'id="{frag}"' not in pages[target]:
            report(name, "broken anchor", f"{target}#{frag}")
    for src in re.findall(r'src="(images/[^"]+)"', page):
        if not (site / src).exists():
            report(name, "missing image file", src)
    for frag in re.findall(r'href="#([^"]+)"', page):
        if f'id="{frag}"' not in page:
            report(name, "broken anchor", "#" + frag)
search = json.loads((site / "search.json").read_text(encoding="utf-8"))
for e in search:
    f, _, frag = e["u"].partition("#")
    if f not in pages or (frag and f'id="{frag}"' not in pages[f]):
        report("search.json", "broken result", e["u"])

print(f"\n{problems} problems")
