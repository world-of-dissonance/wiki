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
GENERATOR_VERSION = "3"


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
            f'<button class="prev" type="button" aria-label="Previous picture">&#8249;</button>'
            f'<button class="next" type="button" aria-label="Next picture">&#8250;</button>'
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


def clean(md: str, images: dict[str, str]) -> str:
    """The doc uses '#' for emphasis paragraphs and empty spacer headings; keep real headings, demote the rest."""
    out = []
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
            elif p.lower() == "main path":
                level = 3
            out.append(f"{'#' * level} {html.escape(p, quote=False)}")
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
    source, galleries, images = tab["md"], {}, {}
    if tab.get("imgs"):
        source, galleries = place_images(source, tab["imgs"], slug, out_dir)
    else:
        images = extract_images(source, slug, out_dir)
    md = markdown.Markdown(extensions=["tables", "sane_lists", "toc"], extension_configs={"toc": {"slugify": lambda v, sep: slugify(v), "toc_depth": "2-3"}})
    body = md.convert(clean(source, images))
    for marker, files in galleries.items():
        body = body.replace(f"<p>{marker}</p>", gallery_html(files))
    body = re.sub(r"<table>", '<div class="table-wrap"><table>', body).replace("</table>", "</table></div>")
    body = body.replace("<img ", '<img loading="lazy" ')
    toc = [{"id": t["id"], "name": t["name"], "children": [{"id": c["id"], "name": c["name"]} for c in t.get("children", [])]} for t in md.toc_tokens]
    text = re.sub(r"<[^>]+>", " ", body)
    return body, toc, html.unescape(re.sub(r"\s+", " ", text)).strip()


def sections_for_search(body: str, page: dict) -> list[dict]:
    """Search entries: one per heading, with the text that follows it."""
    parts = re.split(r'(<h[2-4] id="([^"]+)">(.*?)</h[2-4]>)', body)
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
        page = {"title": title, "slug": slug, "file": f"{slug}.html", "depth": len(t["path"]) - 1, "empty": not t["md"].strip()}
        if page["empty"]:
            page.update(body="", toc=[], text="")
        else:
            page["body"], page["toc"], page["text"] = render(t, slug, out)
        pages.append(page)

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
    return {"hash": digest, "pages": len(pages), "search": len(search)}


# ---------- templates ----------

def head(title: str, desc: str) -> str:
    robots = '<meta name="robots" content="noindex, nofollow">\n' if HIDDEN else ""
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{robots}<meta name="theme-color" content="#121826">
<link rel="icon" type="image/png" href="assets/favicon.png">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="{SITE_URL}assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600&family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Fira+Mono:wght@700&family=Fira+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/wiki.css">
"""


def topbar() -> str:
    return """<header class="topbar">
  <a class="brand" href="index.html"><img src="assets/moon.png" alt="" width="30" height="30"><span><small>World of Dissonance</small>Wiki</span></a>
  <div class="search" role="search">
    <label for="q" class="sr-only">Search the wiki</label>
    <input id="q" type="search" placeholder="Search the wiki" autocomplete="off" aria-controls="results">
    <ol id="results" class="results" hidden></ol>
  </div>
  <button class="menu" id="menu" type="button" aria-expanded="false" aria-controls="nav">Contents</button>
</header>"""


def nav(pages: list[dict], current: int | None) -> str:
    items = []
    for i, p in enumerate(pages):
        cls = ["sub"] if p["depth"] else []
        if p["empty"]:
            cls.append("soon")
        cur = ' aria-current="page"' if i == current else ""
        label = html.escape(p["title"]) + (' <span class="tag">soon</span>' if p["empty"] else "")
        items.append(f'<li class="{" ".join(cls)}"><a href="{p["file"]}"{cur}>{label}</a></li>')
    return f'<nav class="nav" id="nav" aria-label="Wiki pages"><ol>{"".join(items)}</ol>\n<a class="maker" href="{MAKER_URL}">Make a character &rarr;</a></nav>'


def footer(synced: str) -> str:
    return f"""<footer class="foot">
  <span>Updated from the World of Dissonance doc. Last synced {synced}.</span>
  <a href="{DOC_URL}">Open the source doc</a>
</footer>
<script src="assets/wiki.js" defer></script>
</html>
"""


def page_html(p: dict, pages: list[dict], i: int, synced: str) -> str:
    toc = ""
    if p["toc"]:
        def item(t):
            kids = "".join(f'<li><a href="#{c["id"]}">{c["name"]}</a></li>' for c in t["children"])
            return f'<li><a href="#{t["id"]}">{t["name"]}</a>' + (f"<ol>{kids}</ol>" if kids else "") + "</li>"
        toc = f'<aside class="toc" aria-label="On this page"><h2>On this page</h2><ol>{"".join(item(t) for t in p["toc"])}</ol></aside>'
    prev_ = next((pages[j] for j in range(i - 1, -1, -1) if not pages[j]["empty"]), None)
    next_ = next((pages[j] for j in range(i + 1, len(pages)) if not pages[j]["empty"]), None)
    pager = '<nav class="pager" aria-label="Previous and next page">'
    pager += f'<a class="prev" href="{prev_["file"]}"><small>Previous</small>{html.escape(prev_["title"])}</a>' if prev_ else "<span></span>"
    pager += f'<a class="next" href="{next_["file"]}"><small>Next</small>{html.escape(next_["title"])}</a>' if next_ else "<span></span>"
    pager += "</nav>"
    body = p["body"] if not p["empty"] else '<p class="empty">This section of the doc hasn\'t been written yet. It will appear here as soon as it is.</p>'
    desc = (p["text"][:155] + "…") if len(p["text"]) > 155 else (p["text"] or p["title"])
    return head(f'{p["title"]} | World of Dissonance Wiki', desc) + f"""<body>
{topbar()}
<div class="layout">
{nav(pages, i)}
<main class="page" id="main">
  <article class="prose">
    <h1>{html.escape(p["title"])}</h1>
    {body}
  </article>
  {pager}
</main>
{toc}
</div>
{footer(synced)}"""


def clip(text: str, n: int) -> str:
    text = re.sub(r"[—-]{4,}", " ", text).strip()  # the doc's long dash rules
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def home_html(pages: list[dict], synced: str) -> str:
    cards = []
    for p in pages:
        if p["depth"]:
            continue
        blurb = clip(" ".join(strip(m) for m in re.findall(r"<p>(.*?)</p>", p["body"], re.S)[:3]), 170)
        sections = len(p["toc"])
        meta = "Coming soon" if p["empty"] else (f"{sections} sections" if sections else "One page")
        cards.append(f'<li class="card{" soon" if p["empty"] else ""}"><a href="{p["file"]}"><span class="name">{html.escape(p["title"])}</span>'
                     f'<span class="blurb">{html.escape(blurb) if blurb else "Not written yet."}</span><span class="meta">{meta}</span></a></li>')
    intro = next((p for p in pages if p["slug"] == "introduction"), None)
    lede = ""
    if intro:
        m = re.search(r"<p>(.*?)</p>", intro["body"], re.S)
        lede = clip(strip(m.group(1)), 420) if m else ""
    return head("World of Dissonance Wiki", "The world, peoples, aspects, Arcana and rules of World of Dissonance, the Minecraft TTRPG.") + f"""<body class="home">
{topbar()}
<main class="home-main" id="main">
  <section class="hero">
    <img class="hero-moon" src="assets/moon.png" alt="" width="160" height="160">
    <div>
      <p class="kickerless">The world of Tantalos, the shattered lands of Aeode, and the rules that bind them.</p>
      <h1>World of Dissonance</h1>
      <blockquote>{html.escape(lede)}</blockquote>
      <div class="hero-actions"><a class="btn primary" href="introduction.html">Start reading</a><a class="btn" href="{MAKER_URL}">Make a character</a></div>
    </div>
  </section>
  <h2 class="section-title">Everything in the doc</h2>
  <ol class="cards">{"".join(cards)}</ol>
</main>
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
