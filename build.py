"""Build the World of Dissonance wiki from the Google Doc (doc -> wiki only; nothing is ever written back).

    python build.py --out site            fetch every tab of the doc and build the static site
    python build.py --out site --cache c  also keep the raw exports in c/ (and reuse them with --offline)

The doc is link-shared, so everything is fetched anonymously: no Google account, nothing visible to the owner.
Each doc tab becomes a page; headings become the page's contents; the three item catalogs show as "coming soon"
until they have text. .github/workflows/sync.yml runs this hourly and deploys only when the doc changed.
"""
import argparse
import base64
import difflib
import hashlib
import html
import io
import json
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

import markdown
from PIL import Image

DOC_ID = "1M1IhapeJzbYW3Rs9hUHhS7oGkTHOuXiS8hxC0XlLKGk"
DOC_URL = f"https://docs.google.com/document/d/{DOC_ID}"
SITE_URL = "https://world-of-dissonance.github.io/wiki/"
MAKER_URL = "https://world-of-dissonance.github.io/wod-character-maker/"
# Kept out of search engines until the reveal. Set to False to let the wiki be found.
HIDDEN = True
ROOT = Path(__file__).resolve().parent
# changes to the stylesheet or script get a new URL, so browsers never run a stale copy against new pages
ASSET_V = hashlib.sha256((ROOT / "assets/wiki.css").read_bytes() + (ROOT / "assets/wiki.js").read_bytes()).hexdigest()[:10]
GENERATOR_VERSION = "7"


# ---------- fetching ----------

def get(url: str, tries: int = 3) -> bytes:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (wiki sync)"})
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("unreachable")


def list_tabs(edit_html: str) -> list[dict]:
    """Tab ids, titles and nesting from the doc's page data. The first tab is t.0."""
    tabs = [{"id": "t.0", "title": None, "path": [0]}]
    for m in re.finditer(r'\{"ty":"ac","d":\["(t\.[a-z0-9]+)",(.{0,400}?)\]\}', edit_html):
        title = re.search(r'\[1,"((?:[^"\\]|\\.)*)"\]', m.group(2))
        pos = re.findall(r'\[(\d+(?:,\d+)*)\]\s*$', m.group(2))
        tabs.append({"id": m.group(1), "title": json.loads(f'"{title.group(1)}"') if title else None,
                     "path": [int(x) for x in pos[-1].split(",")] if pos else [len(tabs)]})
    return tabs


def fetch(cache: Path | None, offline: bool) -> list[dict]:
    if offline:
        return json.loads((cache / "tabs.json").read_text(encoding="utf-8"))
    tabs = list_tabs(get(f"{DOC_URL}/edit").decode("utf-8", "ignore"))
    if len(tabs) < 2:  # page format changed: fall back to the whole doc as one page
        tabs = [{"id": None, "title": "World of Dissonance", "path": [0]}]
    for t in tabs:
        url = f"{DOC_URL}/export?format=md" + (f"&tab={t['id']}" if t["id"] else "")
        t["md"] = get(url).decode("utf-8")
        if t["md"].strip() and t["id"]:
            # the markdown export drops floating pictures; the HTML export keeps every one, in place
            t["imgs"] = html_images(get(url.replace("format=md", "format=html")).decode("utf-8"))
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "tabs.json").write_text(json.dumps(tabs, ensure_ascii=False), encoding="utf-8")
    return tabs


def is_label(line: str) -> bool:
    return len(line) <= 60 and line.rstrip("*_ ").endswith(":")


def html_images(page: str) -> list[list[str]]:
    """[text line the picture belongs under, data URI] for each picture in a doc HTML export, in order."""
    events: list[tuple[str, str]] = []  # ("t", text line) or ("i", data URI)
    for block in re.finditer(r"<(p|h\d|li|td)[^>]*>(.*?)</\1>", page[page.find("<body"):], re.S):
        for part in re.split(r"(<img[^>]*>)", block.group(2)):
            if part.startswith("<img"):
                src = re.search(r'src="(data:image/[^"]+)"', part)
                if src:
                    events.append(("i", src.group(1)))
                continue
            for x in re.split(r"<br\s*/?>", part):
                x = html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
                if x:
                    events.append(("t", x))
    anchors, anchor, last = [], "", None
    for kind, v in events:
        if kind == "t":
            if not (is_label(v) and last == "label"):  # "A Examples: / B Examples: / C Examples:" then pictures: they're A's
                anchor = v
            last = "label" if is_label(v) else "text"
        else:
            anchors.append(anchor)
            last = "image"
    uris = [v for k, v in events if k == "i"]
    # a run of pictures under prose, followed straight away by a label whose own pictures follow it: move them down
    i = 0
    while i < len(events):
        if events[i][0] != "i":
            i += 1
            continue
        j = i
        while j < len(events) and events[j][0] == "i":
            j += 1
        if j + 1 < len(events) and is_label(events[j][1]) and events[j + 1][0] == "i":
            first = sum(1 for k, _ in events[:i] if k == "i")
            prev = anchors[first]
            if not is_label(prev):
                for n in range(first, first + (j - i)):
                    anchors[n] = events[j][1]
        i = j
    return [[a, u] for a, u in zip(anchors, uris)]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\\(.)", r"\1", s).lower())


def place_images(md: str, imgs: list[list[str]], slug: str, out_dir: Path) -> tuple[str, dict[str, list[str]]]:
    """Put each run of pictures right after the line it follows in the doc; returns md with @@GALLERYn@@ markers."""
    lines = [l for l in md.splitlines() if not re.match(r"^\[image\d+\]:\s*<data:", l)]
    lines = [re.sub(r"!\[[^\]]*\]\[image\d+\]", "", l) for l in lines]
    runs: list[tuple[str, list[str]]] = []
    for anchor, uri in imgs:
        if runs and runs[-1][0] == anchor:
            runs[-1][1].append(uri)
        else:
            runs.append((anchor, [uri]))
    keyed = [norm(l) for l in lines]
    inserts: dict[int, list[str]] = {}
    galleries: dict[str, list[str]] = {}
    saved: dict[str, str] = {}
    at = 0
    for n, (anchor, uris) in enumerate(runs):
        files = []
        for uri in uris:
            data = base64.b64decode(uri.split(",", 1)[1])
            key = hashlib.sha1(data).hexdigest()[:12]
            if key not in saved:
                img = Image.open(io.BytesIO(data))
                img.thumbnail((1600, 1600))
                saved[key] = f"images/{slug}-{key}.webp"
                img.save(out_dir / saved[key], "WEBP", quality=85)
            files.append(saved[key])
        tail = norm(anchor)[-60:]
        # search forward from the last match first, so repeated lines ("Examples:") land in order
        hit = next((i for i in range(at, len(lines)) if tail and tail in keyed[i]), None)
        if hit is None:
            hit = next((i for i in range(len(lines)) if tail and tail in keyed[i]), len(lines) - 1)
        at = hit
        galleries[f"@@GALLERY{n}@@"] = files
        inserts.setdefault(hit, []).append(f"@@GALLERY{n}@@")
    pictured = [norm(lines[i]) for i in inserts]
    out = []
    for i, l in enumerate(lines):
        k = norm(l)
        if i not in inserts and is_label(re.sub(r"[*_\\]", "", l).strip()) and 12 <= len(k) and any(
                k != o and difflib.SequenceMatcher(None, k, o).ratio() > 0.9 for o in pictured):
            continue
        out.append(l)
        for marker in inserts.get(i, []):
            out += ["", marker, ""]
    return "\n".join(out), galleries


def gallery_html(files: list[str]) -> str:
    imgs = "".join(f'<img alt="" src="{f}">' for f in files)
    if len(files) == 1:
        return f'<figure class="gallery single">{imgs}</figure>'
    return (f'<figure class="gallery" aria-label="{len(files)} pictures">'
            f'<div class="strip" tabindex="0">{imgs}</div>'
            f'<button class="prev" type="button" aria-label="Previous picture">{ICON_PREV}</button>'
            f'<button class="next" type="button" aria-label="Next picture">{ICON_NEXT}</button>'
            f'<figcaption class="count">1 / {len(files)}</figcaption></figure>')


# ---------- cleaning Google's markdown ----------

def plain(s: str) -> str:
    """Heading text without markdown emphasis, escapes or the doc's [bracket] / -dash- framing."""
    s = re.sub(r"\\(.)", r"\1", s)
    s = s.replace("**", "").replace("__", "")
    s = re.sub(r"(?<![\w*])\*(?!\s)|(?<!\s)\*(?![\w*])", "", s)
    s = s.strip()
    for _ in range(3):
        s = re.sub(r"^\[(.*)\]$", r"\1", s).strip()
        s = re.sub(r"^-+\s*(.*?)\s*-+$", r"\1", s).strip()
    if s.count("[") != s.count("]"):  # a stray bracket from a half-tagged heading like "T3] Thought"
        s = re.sub(r"^\]\s*|\s*\[$", "", s)
        s = re.sub(r"^([A-Za-z]\d+)\]", r"[\1]", s)
    s = re.sub(r"^\[\s*(T\d+)\s*\]\s*", r"[\1] ", s)  # "[T1 ]Aspire"
    s = re.sub(r"^\[(T\d+)\s+([^\]]+)\]:?$", r"[\1] \2", s)  # "[T2 Block]:"
    return s.rstrip(":").strip()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "").replace("’", "")).strip("-") or "section"


BOLD_LINE = re.compile(r"\s*\*\*([^*]{2,60})\*\*\s*")


def clean(md: str, images: dict[str, str]) -> str:
    """The doc uses '#' for emphasis paragraphs and empty spacer headings; keep real headings, demote the rest."""
    out = []
    # tabs written without headings mark their sections with bold lines; those become sections (needs two or more)
    real_heads = any(re.match(r"^#{1,6}\s+\S", l) and plain(re.sub(r"^#+", "", l)) for l in md.splitlines())
    promote = not real_heads and sum(1 for l in md.splitlines() if BOLD_LINE.fullmatch(l)) >= 2
    branches = {n.lower() for n in tree_paths(md)}
    for line in md.splitlines():
        m = re.match(r"^(\[image\d+\]):\s*<data:", line)
        if m:
            name = m.group(1)[1:-1]
            if name in images:
                out.append(f"[{name}]: {images[name]}")
            continue
        h = re.match(r"^(#{1,6})\s+(.*)$", line) or re.match(r"^(#{1,6})\s*$", line)
        if h:
            text = h.group(2) if h.lastindex == 2 else ""
            p = plain(text)
            if not p or p in {".", "-"}:
                out.append("")
                continue
            sentence = len(p) > 90 or (len(p) > 45 and re.search(r"[.!?”\"]$", p)) or p.count(":") >= 2
            if sentence:  # a paragraph the author made big; keep its words, lose the heading
                out.append(text.strip())
                continue
            level = min(len(h.group(1)) + 1, 4)  # the page title is the only h1
            if re.match(r"\[T\d+\]", p):
                level = 4
            elif p.lower() == "main path" or (level == 4 and p.lower() in branches):
                level = 3
            out.append(f"{'#' * level} {html.escape(p, quote=False)}")
            continue
        b = BOLD_LINE.fullmatch(line)
        if b and re.match(r"\[T\d+\]", plain(b.group(1))):  # "**[T1]  Puppet:**" is a tier like the headed ones
            out.append(f"#### {html.escape(re.sub(r'\s+', ' ', plain(b.group(1))), quote=False)}")
            continue
        # a label ending in a hard break ("**Bleeding:**  ") is one line of a list, not a section title
        b = b if promote and not line.endswith("  ") else None
        if b and plain(b.group(1)):
            out.append(f"## {html.escape(plain(b.group(1)), quote=False)}")
            continue
        if re.match(r"^(\t| {4,})", line) and not re.match(r"^\s*([*+-]|\d+\.)\s", line):
            line = line.lstrip()  # the doc's hand-spaced diagrams would otherwise become code blocks
        out.append(line)
    text = "\n".join(out)
    # raw angle brackets in prose would be read as HTML
    text = re.sub(r"<(?!data:|https?:)", "&lt;", text)
    text = text.replace("�", "")
    # a line of dashes under text would turn that text into a heading; make it a divider
    text = re.sub(r"(?m)^\s*[-—]{3,}\s*$", "\n---\n", text)
    # *** around escaped brackets trips the markdown parser; asterisks the author typed (\*word\*) were meant as italics
    text = re.sub(r"\*\*([,;]\s*)\*\*", r"\1", text)  # bold switched off and on around a comma: "***[A]**, **[B],***"
    text = re.sub(r"\*\*\*(\S(?:[^*\n]*?\S)?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\\\*(\S(?:[^*\n]{0,60}?\S)?)\\\*", r"*\1*", text)
    return text


def extract_images(md: str, slug: str, out_dir: Path) -> dict[str, str]:
    found = {}
    for m in re.finditer(r"^\[(image\d+)\]:\s*<data:image/(\w+);base64,([^>]*)>", md, re.M):
        name, data = m.group(1), base64.b64decode(m.group(3))
        img = Image.open(io.BytesIO(data))
        img.thumbnail((1600, 1600))
        fname = f"{slug}-{name}.webp"
        img.save(out_dir / "images" / fname, "WEBP", quality=85)
        found[name] = f"images/{fname}"
    return found


# ---------- rendering ----------

def render(tab: dict, slug: str, out_dir: Path) -> tuple[str, list[dict], str]:
    # a soft line break inside a table cell arrives as \v, which splitlines() would treat as a new row
    source, galleries, images = tab["md"].replace("\x0b", "@@BR@@"), {}, {}
    if tab.get("imgs"):
        source, galleries = place_images(source, tab["imgs"], slug, out_dir)
    else:
        images = extract_images(source, slug, out_dir)
    md = markdown.Markdown(extensions=["tables", "sane_lists", "toc"], extension_configs={"toc": {"slugify": lambda v, sep: slugify(v), "toc_depth": "2-3"}})
    body = md.convert(clean(source, images))
    for marker, files in galleries.items():
        body = body.replace(f"<p>{marker}</p>", gallery_html(files))
    body = body.replace("@@BR@@", "<br>")

    # the doc's one-row tables (every skill) arrive as a header plus an empty row: set them as a single record
    def record(m):
        cells = re.findall(r"<th[^>]*>(.*?)</th>", m.group(1), re.S)
        # line breaks only matter in the effect text; elsewhere they join words ("RadiusSelf")
        cells = [c if i == 2 else re.sub(r"\s*<br>\s*", " ", c).strip() for i, c in enumerate(cells)]
        tds = []
        for i, c in enumerate(cells):
            if i >= 3:
                # the doc's blank records drop the colon ("Cast Time"), so known labels match without it
                c = re.sub(r"^(Cast Time|Lasts For|Range|Cooldown|[^:<]{1,24}(?=:)):?\s*", r"<b>\1</b> ", c)
            blank = ' class="blank"' if i == 1 and not re.search(r"\d", c) else ""
            tds.append(f"<td{blank}>{c}</td>")
        return '<table class="record"><tbody><tr>' + "".join(tds) + "</tr></tbody></table>"
    body = re.sub(r"<table>\s*<thead>(.*?)</thead>\s*<tbody>\s*<tr>(?:\s*<td[^>]*></td>)+\s*</tr>\s*</tbody>\s*</table>", record, body, flags=re.S)
    body = re.sub(r"<table>", '<div class="table-wrap"><table>', body).replace("</table>", "</table></div>")
    body = body.replace('<table class="record">', '<div class="table-wrap record-wrap"><table class="record">')
    body = body.replace("<img ", '<img loading="lazy" ')
    body = tree_diagrams(tab["md"], fold_blanks(body))
    toc = [{"id": t["id"], "name": t["name"], "children": [{"id": c["id"], "name": c["name"]} for c in t.get("children", [])]} for t in md.toc_tokens]
    text = re.sub(r"<[^>]+>", " ", readable(body))
    return body, toc, html.unescape(re.sub(r"\s+", " ", text)).strip()



# ---------- organizing: skill trees, unwritten slots, glossary ----------

def tree_paths(md: str) -> dict[str, list[str]]:
    """The doc sums up every skill path as "NAME: tier -> tier -> tier"; those lines are the trees' source of truth."""
    paths: dict[str, list[str]] = {}
    for line in md.splitlines():
        if "\\-\\>" not in line and "->" not in line:
            continue
        line = re.sub(r"\\(.)", r"\1", line)
        line = re.sub(r"[*↘↗↕^|\\/]", " ", line)
        for m in re.finditer(r"([A-Z][A-Z ]{1,20}[A-Z]):\s*(.*?)(?=\s[A-Z][A-Z ]{1,20}[A-Z]:|$)", line):
            tiers = [t.strip(" .-") for t in re.split(r"->|-(?=>)|\s{2,}", m.group(2)) if t.strip(" .->")]
            tiers = [re.sub(r"\s+", " ", t) for t in tiers if not re.fullmatch(r"[A-Z ]+", t)][:4]
            if tiers:
                paths.setdefault(m.group(1).strip(), tiers)
    return paths


def fold_blanks(body: str) -> str:
    """Runs of unwritten skill slots (#3 EP Cast Time … with no effect) fold into one line you can open."""
    blank = (r'<div class="table-wrap record-wrap"><table class="record"><tbody><tr><td>[^<]*</td><td[^>]*>[^<]*</td><td></td>'
             r'.*?</tr></tbody></table></div>')

    def fold(m):
        run = m.group(0).strip()
        nums = re.findall(r"<tr><td>([^<]*)</td>", run)
        n = len(nums)
        span = nums[0] if n == 1 else f"{nums[0]}–{nums[-1]}"
        label = f"{n} unwritten slot{'s' if n != 1 else ''}"
        return f'<details class="unwritten"><summary>{label} <span>{html.escape(span)}</span></summary>{run}</details>\n'
    return re.sub(rf"(?:{blank}\s*)+", fold, body, flags=re.S)


def named(name: str, paths: dict) -> str | None:
    """The path a heading names, allowing the doc's spelling slips ("DECIEVE" for DECEIVE)."""
    if name in paths:
        return name
    close = difflib.get_close_matches(name, list(paths), n=1, cutoff=0.8)
    return close[0] if close else None


def tree_diagrams(md: str, body: str) -> str:
    """A diagram under each skill tree's heading: the main path, then each branch, tier by tier, linked to the entries."""
    paths = tree_paths(md)
    if not paths:
        return body
    parts = re.split(r'(<h2 id="[^"]+">.*?</h2>)', body)
    for i in range(1, len(parts), 2):
        tree = named(strip(parts[i]).upper(), paths)
        if not tree:
            continue
        section = parts[i + 1]
        h3s = [(m.group(1), strip(m.group(2)), m.start()) for m in re.finditer(r'<h3 id="([^"]+)">(.*?)</h3>', section)]

        def region(start):
            nxt = [s for _, _, s in h3s if s > start]
            return section[start:nxt[0] if nxt else len(section)]

        def row(label, anchor, tiers, start, main=False):
            reg = region(start) if start is not None else ""
            nodes = []
            for n, name in enumerate(tiers, 1):
                hit = re.search(rf'<h4 id="([^"]+)">\[T{n}\]\s*{re.escape(name)}\s*</h4>', reg, re.I)
                href = f"#{hit.group(1)}" if hit else (f"#{anchor}" if anchor else "")
                inner = f"<span>T{n}</span>{html.escape(name)}"
                nodes.append(f'<li><a href="{href}">{inner}</a></li>' if href else f"<li><b>{inner}</b></li>")
            name = f'<a class="pname" href="#{anchor}">{html.escape(label)}</a>' if anchor else f'<span class="pname">{html.escape(label)}</span>'
            return f'<div class="path{" main" if main else ""}">{name}<ol>{"".join(nodes)}</ol></div>'

        main = next(((a, s) for a, t, s in h3s if t.lower() == "main path"), (None, None))
        rows = [row("Main path", main[0], paths[tree], main[1], main=True)]
        for a, t, s in h3s:
            b = named(t.upper(), paths)
            if b and b != tree:
                rows.append(row(t, a, paths[b], s))
        cap = f"{tree.title()} · main path and {len(rows) - 1} branch{'es' if len(rows) != 2 else ''}"
        parts[i] += f'\n<figure class="tree" aria-label="{html.escape(tree.title())} skill tree"><figcaption>{cap}</figcaption>{"".join(rows)}</figure>\n'
    return "".join(parts)


def collect_terms(pages: list[dict]) -> dict[str, dict]:
    """Terms the doc defines as a paragraph that opens in bold ("Burning: …", "One [Instant]: …"); the first definition wins."""
    gloss: dict[str, dict] = {}
    for p in pages:
        if p["empty"]:
            continue
        ids = set(re.findall(r'id="([^"]+)"', p["body"]))

        def define(m):
            label = strip(m.group(1)).rstrip(":").strip()
            rest = strip(m.group(2)).lstrip(":").strip()
            bracket = re.search(r"\[([^\]]{2,30})\]", label)
            term = (bracket.group(1) if bracket else label).strip()
            key = term.lower()
            if (len(rest) < 20 or len(term) > 30 or key in gloss or re.match(r"t\d", key) or ":" in key
                    or re.search(r"example|appear|types and|forms of", key)):
                return m.group(0)
            tid = "term-" + slugify(term)
            if tid in ids:
                return m.group(0)
            ids.add(tid)
            gloss[key] = {"t": term, "d": clip(rest, 320), "u": f'{p["file"]}#{tid}', "p": p["title"]}
            return f'<p id="{tid}">' + m.group(0)[3:]
        p["body"] = re.sub(r"<p><strong>(.{2,60}?)</strong>(.*?)</p>", define, p["body"], flags=re.S)

    # skills are terms too ("[Connective Net]"): a written skill record gets an id and its effect as the definition
    for p in pages:
        if p["empty"]:
            continue

        def skill(m):
            name = re.sub(r"^#\d+\s*", "", strip(m.group(1)))
            effect = strip(m.group(2))
            key, sid = name.lower(), "skill-" + slugify(name)
            if not name or len(effect) < 20 or key in gloss or f'id="{sid}"' in p["body"]:
                return m.group(0)
            gloss[key] = {"t": name, "d": clip(effect, 320), "u": f'{p["file"]}#{sid}', "p": p["title"]}
            return m.group(0).replace('<div class="table-wrap record-wrap">', f'<div class="table-wrap record-wrap" id="{sid}">', 1)
        p["body"] = re.sub(r'<div class="table-wrap record-wrap"><table class="record"><tbody><tr><td>(.*?)</td><td[^>]*>.*?</td><td>(.*?)</td>',
                           skill, p["body"], flags=re.S)

    # last, short headings followed by text (the conditions on Elements, Effects, Conditions are headed this way)
    for p in pages:
        if p["empty"]:
            continue
        for m in re.finditer(r'<h([2-4]) id="([^"]+)">(.*?)</h\1>(.*?)(?=<h[1-4][ >]|$)', p["body"], re.S):
            term = re.sub(r"^§[\d.]+\s*", "", strip(m.group(3)))
            rest = strip(readable(m.group(4)))
            key = term.lower()
            if term.startswith("[") or len(term) > 30 or len(rest) < 40 or key in gloss or key == "main path":
                continue
            gloss[key] = {"t": term, "d": clip(rest, 320), "u": f'{p["file"]}#{m.group(2)}', "p": p["title"]}
    return gloss


def link_terms(body: str, gloss: dict[str, dict], file: str) -> str:
    """Every [Bracketed Term] the glossary knows becomes a link with a hover definition (not inside headings or links)."""
    out, in_a, in_h, defining = [], 0, 0, None
    for tok in re.split(r"(<[^>]+>)", body):
        if tok.startswith("<"):
            if re.match(r"<a[\s>]", tok):
                in_a += 1
            elif tok == "</a>":
                in_a = max(0, in_a - 1)
            elif re.match(r"<h[1-6][\s>]", tok):
                in_h += 1
            elif re.match(r"</h[1-6]>", tok):
                in_h = max(0, in_h - 1)
            m = re.match(r'<p id="(term-[^"]+)">', tok)
            if m:
                defining = m.group(1)
            elif tok == "</p>":
                defining = None
            out.append(tok)
            continue
        if in_a or in_h or "[" not in tok:
            out.append(tok)
            continue

        def link(m):
            key = html.unescape(m.group(1)).strip().lower()
            g = gloss.get(key) or gloss.get(key.removesuffix("s"))  # "[Reactions]" → Reaction
            if not g:
                return m.group(0)
            page, _, tid = g["u"].partition("#")
            if tid == defining and page == file:
                return m.group(0)
            href = f"#{tid}" if page == file else g["u"]
            return f'<a class="term" href="{href}" data-term="{html.escape(g["t"].lower())}">{m.group(0)}</a>'
        out.append(re.sub(r"\[([^\[\]<]{2,30})\]", link, tok))
    return "".join(out)


def skills_data(pages: list[dict]) -> list[dict]:
    """Every written skill with its tree, path and tier, for the character maker's skill picker (site/skills.json)."""
    out = []
    for p in pages:
        if p["empty"] or 'class="record"' not in p["body"]:
            continue
        paths = tree_paths(p.get("md", ""))
        tree = path = None
        tier, tier_id = 0, ""
        token = re.compile(r'<h2 id="[^"]+">(.*?)</h2>|<h3 id="[^"]+">(.*?)</h3>|<h4 id="([^"]+)">\[T(\d+)\][^<]*</h4>'
                           r'|<div class="table-wrap record-wrap"(?: id="([^"]+)")?><table class="record"><tbody><tr>(.*?)</tr>', re.S)
        for m in token.finditer(p["body"]):
            if m.group(1) is not None:
                name = named(re.sub(r"^§[\d.]+\s*", "", strip(m.group(1))).upper(), paths)
                tree, path, tier = name, None, 0
            elif m.group(2) is not None:
                path = re.sub(r"^§[\d.]+\s*", "", strip(m.group(2)))
            elif m.group(4):
                tier, tier_id = int(m.group(4)), m.group(3)
            elif m.group(6) is not None and tree and tier:
                cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(6), re.S)
                name = re.sub(r"^#\d+\s*", "", strip(cells[0])) if cells else ""
                if not name or len(cells) < 3 or not strip(cells[2]) or name.lower() in ("progression", "mastery"):
                    continue  # an unwritten slot, or the row saying where the path leads next
                if any(o["name"].lower() == name.lower() for o in out):
                    continue  # the doc pastes some skills under other trees, sometimes lightly edited; the first copy is the real one
                stats = {}
                for c in cells[3:]:
                    k = re.match(r"<b>(.*?)</b>\s*(.*)", c, re.S)
                    if k:
                        stats[strip(k.group(1)).lower()] = strip(k.group(2))
                ep = re.search(r"\d+", strip(cells[1])) if len(cells) > 1 else None
                out.append({
                    "name": re.sub(r"^#\d+\s*", "", strip(cells[0])), "tree": tree.lower(), "path": path or "Main Path", "tier": tier,
                    "ep": int(ep.group()) if ep else None, "effect": strip(cells[2]) if len(cells) > 2 else "",
                    "cast": stats.get("cast time", ""), "lasts": stats.get("lasts for", ""), "range": stats.get("range", ""),
                    "cooldown": stats.get("cooldown", ""), "url": f'{p["file"]}#{m.group(5) or tier_id}',
                })
    return out


def levels_data(pages: list[dict]) -> dict:
    """The doc's milestone table ("3. +1 Skill Slot +1 Stat Point +Arcana Advance ..."), one entry per level, plus the
    caps its totals state (the rows add up to more skill slots and trees than the totals allow), for site/levels.json."""
    md = next((p["md"] for p in pages if "Standard Leveling" in p.get("md", "")), "")
    md = md[md.find("Standard Leveling"):]
    totals = re.sub(r"\\(.)", r"\1", md[:md.find("Refinement")] if "Refinement" in md else md)
    cap = lambda pat: int(x.group(1)) if (x := re.search(pat, totals, re.I)) else None
    out = []
    for line in md.splitlines():
        m = re.match(r"^\s*(\d+)\\?\.\s*(.*)$", line)
        if not m:
            if out and line.strip().lower().startswith("total"):
                break  # the table's own totals follow it
            continue
        t = re.sub(r"\\(.)", r"\1", m.group(2))
        num = lambda pat: int(x.group(1)) if (x := re.search(pat, t, re.I)) else 0
        out.append({
            "level": int(m.group(1)),
            "skillSlots": num(r"\+(\d+)\s*Skill Slot"),
            "statPoints": num(r"\+(\d+)\s*Stat Point"),
            "arcanaAdvance": bool(re.search(r"Arcana Advance(?!ment)", t, re.I)),
            "newTreeOrAdvance": bool(re.search(r"New Arcana Tree", t, re.I)),
            "signatureAdvance": bool(re.search(r"Signature Advance", t, re.I)),
            "reslot": bool(re.search(r"Reslotting", t, re.I)),
            "baseTrees": 2 if re.search(r"Two Base Arcana", t, re.I) else 0,
            "text": re.sub(r"\s+", " ", t).strip(),
        })
    return {"levels": out, "maxSkillSlots": cap(r"Possible Skill Slots:\s*(\d+)"),
            "maxTrees": cap(r"Arcana Tree Choices:\s*\d+\s*/\s*(\d+)"), "maxStatPoints": cap(r"Bonus Stat Points:\s*(\d+)")}


def readable(body: str) -> str:
    """Body without the parts that are navigation, not text (diagrams, folded blank slots), for search and summaries."""
    return re.sub(r'<details class="unwritten">.*?</details>|<figure class="tree".*?</figure>', " ", body, flags=re.S)


def sections_for_search(body: str, page: dict) -> list[dict]:
    """Search entries: one per heading, with the text that follows it."""
    parts = re.split(r'(<h[2-4] id="([^"]+)">(.*?)</h[2-4]>)', readable(body))
    out = [{"p": page["title"], "h": page["title"], "u": page["file"], "x": strip(parts[0])[:600]}]
    section = ""
    for i in range(1, len(parts) - 1, 4):
        head = strip(parts[i + 2])
        where = page["title"] + (f" › {section}" if section and not parts[i].startswith("<h2") else "")
        if parts[i].startswith("<h2"):
            section = head
        out.append({"p": where, "h": head, "u": f'{page["file"]}#{parts[i + 1]}', "x": strip(parts[i + 3])[:600]})
    return [e for e in out if e["x"] or e["h"] != page["title"]]


def strip(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def build(tabs: list[dict], out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():  # empty it in place, so a server pointed at it keeps working
        shutil.rmtree(old) if old.is_dir() else old.unlink()
    (out / "images").mkdir()
    shutil.copytree(ROOT / "assets", out / "assets")
    pages = []
    for t in tabs:
        first = next((plain(m) for m in re.findall(r"^#{1,6}\s+(.+)$", t["md"], re.M) if plain(m)), None)
        title = t["title"] or first or "Introduction"
        slug = "introduction" if t["id"] == "t.0" else slugify(title)
        while any(p["slug"] == slug for p in pages):
            slug += "-2"
        page = {"title": title, "slug": slug, "file": f"{slug}.html", "depth": len(t["path"]) - 1, "empty": not t["md"].strip(),
                "vol": volume_of(title), "md": t["md"]}
        if page["empty"]:
            page.update(body="", toc=[], text="")
        else:
            page["body"], page["toc"], page["text"] = render(t, slug, out)
            number_sections(page)
        pages.append(page)

    gloss = collect_terms(pages)
    for p in pages:
        if not p["empty"]:
            p["body"] = link_terms(p["body"], gloss, p["file"])
    (out / "levels.json").write_text(json.dumps(levels_data(pages), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out / "skills.json").write_text(json.dumps(skills_data(pages), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out / "glossary.json").write_text(json.dumps(gloss, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    search = []
    for p in pages:
        if not p["empty"]:
            search += sections_for_search(p["body"], p)
    (out / "search.json").write_text(json.dumps(search, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    digest = hashlib.sha256((GENERATOR_VERSION + "".join(t["md"] for t in tabs)).encode()).hexdigest()
    synced = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    for i, p in enumerate(pages):
        (out / p["file"]).write_text(page_html(p, pages, i, synced), encoding="utf-8")
    (out / "index.html").write_text(home_html(pages, synced), encoding="utf-8")
    (out / "build.json").write_text(json.dumps({"hash": digest, "synced": synced, "pages": len(pages)}), encoding="utf-8")
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n" if HIDDEN else "User-agent: *\nAllow: /\n")
    (out / ".nojekyll").write_text("")
    return {"hash": digest, "pages": len(pages), "search": len(search), "terms": len(gloss)}


# ---------- templates ----------
# The wiki is set as a bound compendium: six volumes, each with a coloured thumb tab, § numbers for citing sections.

VOLUMES = [  # (key, name, numeral, words that place a doc tab in it)
    ("lore", "Lore", "I", ()),
    ("peoples", "Peoples", "II", ("cords", "species", "eon-kin")),
    ("aspects", "Aspects", "III", ("aspect", "signature")),
    ("arcana", "Arcana", "IV", ("arcana", "skill")),
    ("rules", "Rules", "V", ("levelling", "stat", "action", "roll", "combat", "element", "effect", "condition", "trait", "affliction", "curse")),
    ("catalogs", "Catalogs", "VI", ("catalog",)),
]
VOLUME_BLURB = {
    "lore": "History, regions, stories and the building of Lychgate.",
    "peoples": "The races of Tantalos and the Eon-Kin.",
    "aspects": "Astra, Fibero, Eternum and the four signatures.",
    "arcana": "Wonder, Will, Weapon and every skill tree.",
    "rules": "Levelling, rolls, combat, conditions and curses.",
    "catalogs": "Mundane items, trinkets and relics.",
}
VOLUME_HINT = {"lore": "History, regions", "peoples": "Races, Eon-Kin", "aspects": "Astra, Fibero, Eternum",
               "arcana": "Arcana, skill trees", "rules": "Rolls, combat", "catalogs": "Items, relics"}
ICON_SEARCH = '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5"/><path d="m13 13 4.5 4.5"/></svg>'
ICON_MOON = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M20.5 3.5a13 13 0 1 0 8 22.6A11.2 11.2 0 0 1 20.5 3.5z"/></svg>'
ICON_PREV = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12.5 4 6.5 10l6 6"/></svg>'
ICON_NEXT = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7.5 4 6 6-6 6"/></svg>'


def volume_of(title: str) -> str:
    t = title.lower()
    for key, _, _, words in reversed(VOLUMES):
        if any(w in t for w in words):
            return key
    return "lore"


def number_sections(page: dict) -> None:
    """§1, §1.1 … on h2/h3, in the body and in the contents, so any section can be cited."""
    nums, h2, h3 = {}, 0, 0

    def tag(m):
        nonlocal h2, h3
        level, hid = m.group(1), m.group(2)
        if level == "2":
            h2, h3 = h2 + 1, 0
            n = f"{h2}"
        else:
            h3 += 1
            n = f"{max(h2, 1)}.{h3}"
        nums[hid] = n
        return f'{m.group(0)}<span class="sec">§{n}</span> '
    page["body"] = re.sub(r'<h([23]) id="([^"]+)">', tag, page["body"])
    for t in page["toc"]:
        t["num"] = nums.get(t["id"], "")
        for c in t["children"]:
            c["num"] = nums.get(c["id"], "")


def head(title: str, desc: str) -> str:
    robots = '<meta name="robots" content="noindex, nofollow">\n' if HIDDEN else ""
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{robots}<meta name="theme-color" content="#1d4a52">
<link rel="icon" type="image/png" href="assets/favicon.png">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="{SITE_URL}assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Spectral+SC:wght@600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/wiki.css?v={ASSET_V}">
"""


def masthead() -> str:
    return f"""<nav class="sitebar" aria-label="World of Dissonance pages"><span class="sb-name">World of Dissonance</span><a href="https://world-of-dissonance.github.io/wiki/" aria-current="page">Wiki</a><a href="https://world-of-dissonance.github.io/wod-character-maker/">Character Maker</a><a href="https://world-of-dissonance.github.io/wod-character-maker/workshop.html">DM Workshop</a></nav>
<header class="mast">
  <a class="brand" href="index.html"><span class="seal">{ICON_MOON}</span><span class="name">World of Dissonance</span></a>
  <div class="search" role="search">
    <label for="q" class="sr-only">Search the compendium</label>
    {ICON_SEARCH}
    <input id="q" type="search" placeholder="Search races, skills, rules" autocomplete="off" aria-controls="results">
    <kbd aria-hidden="true">/</kbd>
    <ol id="results" class="results" hidden></ol>
  </div>
</header>"""


def first_page(pages: list[dict], vol: str) -> dict | None:
    in_vol = [p for p in pages if p["vol"] == vol]
    return next((p for p in in_vol if not p["empty"]), in_vol[0] if in_vol else None)


def thumbs(pages: list[dict], current: str | None) -> str:
    tabs = []
    for key, name, num, _ in VOLUMES:
        target = first_page(pages, key)
        if not target:
            continue
        cur = ' aria-current="true"' if key == current else ""
        tabs.append(f'<a class="thumb t-{key}" href="{target["file"]}" data-vol="{key}"{cur}><span class="num">{num}</span>'
                    f'<span class="label">{name}</span><small>{VOLUME_HINT[key]}</small><span class="ribbon" aria-hidden="true"></span></a>')
    return f'<nav class="thumbs" aria-label="Volumes">{"".join(tabs)}</nav>'


def footer(synced: str) -> str:
    return f"""<footer class="colophon">
  <p>Set from the World of Dissonance doc. Last synced {synced}.</p>
  <p><a href="{DOC_URL}">Open the source doc</a><a href="{MAKER_URL}">Make a character</a></p>
</footer>
<script src="assets/wiki.js?v={ASSET_V}" defer></script>
</html>
"""


def page_html(p: dict, pages: list[dict], i: int, synced: str) -> str:
    key, name, num = next((k, n, x) for k, n, x, _ in VOLUMES if k == p["vol"])
    siblings = "".join(
        f'<li><a href="{s["file"]}"{" aria-current=\"page\"" if s is p else ""}>{html.escape(s["title"])}</a></li>'
        for s in pages if s["vol"] == key)
    contents = ""
    if p["toc"]:
        def item(t):
            kids = "".join(f'<li><a href="#{c["id"]}"><span>§{c["num"]}</span>{c["name"]}</a></li>' for c in t["children"])
            return f'<li><a href="#{t["id"]}"><span>§{t["num"]}</span>{t["name"]}</a>' + (f"<ol>{kids}</ol>" if kids else "") + "</li>"
        contents = (f'<details class="margin" open><summary>In this entry</summary><nav aria-label="In this entry">'
                    f'<ol>{"".join(item(t) for t in p["toc"])}</ol></nav></details>')
    prev_ = next((pages[j] for j in range(i - 1, -1, -1) if not pages[j]["empty"]), None)
    next_ = next((pages[j] for j in range(i + 1, len(pages)) if not pages[j]["empty"]), None)
    pager = '<nav class="pager" aria-label="Previous and next entry">'
    pager += f'<a class="prev" href="{prev_["file"]}"><small>Previous entry</small>{html.escape(prev_["title"])}</a>' if prev_ else "<span></span>"
    pager += f'<a class="next" href="{next_["file"]}"><small>Next entry</small>{html.escape(next_["title"])}</a>' if next_ else "<span></span>"
    pager += "</nav>"
    body = p["body"] if not p["empty"] else '<p class="empty">This entry is still blank in the doc. It will be set here as soon as it is written.</p>'
    first = p["toc"][0] if p["toc"] else None
    guide = f'§{first["num"]} {first["name"]}' if first else ""
    desc = (p["text"][:155] + "…") if len(p["text"]) > 155 else (p["text"] or p["title"])
    return head(f'{p["title"]} | World of Dissonance Compendium', desc) + f"""<body class="v-{key}" data-vol="{key}" data-page="{p["file"]}" data-title="{html.escape(p["title"])}">
<a class="skip" href="#text">Skip to the entry</a>
{masthead()}
<div class="book">
  <main class="leaf" id="main">
    <header class="band">
      <p class="vol"><span>Vol. {num}</span>{name}</p>
      <h1>{html.escape(p["title"])}</h1>
      <nav class="vol-pages" aria-label="{name} entries"><ol>{siblings}</ol></nav>
    </header>
    <div class="run" aria-hidden="true"><span>{name} · {html.escape(p["title"])}</span><span class="guide">{guide}</span></div>
    <div class="spread">
      {contents}
      <article class="text" id="text">
        {body}
        {pager}
      </article>
    </div>
  </main>
  {thumbs(pages, key)}
</div>
{footer(synced)}"""


def clip(text: str, n: int) -> str:
    text = re.sub(r"[—-]{4,}", " ", text).strip()  # the doc's long dash rules
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def home_html(pages: list[dict], synced: str) -> str:
    vols = []
    for key, name, num, _ in VOLUMES:
        entries = [p for p in pages if p["vol"] == key]
        if not entries:
            continue
        rows = []
        for p in entries:
            n = len(p["toc"])
            count = "blank" if p["empty"] else (f"{n} §" if n else "1 §")
            rows.append(f'<li{" class=\"blank\"" if p["empty"] else ""}><a href="{p["file"]}"><span class="t">{html.escape(p["title"])}</span>'
                        f'<span class="dots" aria-hidden="true"></span><span class="c">{count}</span></a></li>')
        vols.append(f'<section class="volume v-{key}"><h2><span>Vol. {num}</span>{name}</h2><p>{VOLUME_BLURB[key]}</p><ol>{"".join(rows)}</ol></section>')
    intro = next((p for p in pages if p["slug"] == "introduction"), None)
    lede = ""
    if intro:
        m = re.search(r"<p>(.*?)</p>", intro["body"], re.S)
        lede = clip(strip(m.group(1)), 360) if m else ""
    total = sum(len(p["toc"]) for p in pages)
    return head("World of Dissonance Compendium", "The world, peoples, aspects, Arcana and rules of World of Dissonance, the Minecraft TTRPG.") + f"""<body class="home">
<a class="skip" href="#contents">Skip to the contents</a>
{masthead()}
<div class="book">
  <main class="leaf" id="main">
    <section class="title-page">
      <div class="stamp">{ICON_MOON}</div>
      <h1>World of Dissonance</h1>
      <p class="sub">A compendium of Tantalos and the shattered lands of Aeode, in six volumes and {total} sections.</p>
      <blockquote><p>{html.escape(lede)}</p></blockquote>
      <p class="actions"><a class="btn primary" href="introduction.html">Begin at Vol. I</a><a class="btn resume" href="introduction.html" hidden>Continue reading</a><a class="btn" href="{MAKER_URL}">Make a character</a></p>
    </section>
    <section class="contents" id="contents" aria-labelledby="contents-h">
      <h2 id="contents-h" class="sr-only">Contents</h2>
      {"".join(vols)}
    </section>
  </main>
  {thumbs(pages, None)}
</div>
{footer(synced)}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--cache")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    tabs = fetch(Path(a.cache) if a.cache else None, a.offline)
    info = build(tabs, Path(a.out))
    print(json.dumps(info))


if __name__ == "__main__":
    sys.exit(main())
