"""Our item database: items/items.json (our own content, never from or to the doc), checked against the item rules and
set as the Item Database page. Each item is a game item definition as the mod's Gear reads it, plus our own fields
(id, quality, base, grade, enchant), which the game ignores. The tooltip on the page is the game's, drawn by
assets/itemtip.js.
"""
import html
import json
import re
from pathlib import Path

FILE = Path(__file__).resolve().parent / "items/items.json"
GAME_FIELDS = {"name", "type", "rarity", "weight", "value", "text", "icon", "dmg", "range", "aspect", "hands", "ap", "look", "bonus", "use"}
OUR_FIELDS = {"id", "quality", "base", "grade", "enchant"}
TYPES = ["weapon", "ranged", "shield", "armor", "head", "cloak", "hands", "feet", "amulet", "ring", "clothing", "consumable", "misc"]
RARITIES = ["mundane", "trinket", "relic", "legendary"]
QUALITIES = ["crude", "common", "fine", "masterwork"]
GRADES = ["minor", "medium", "major", "majestic", "mythic"]
DIE = [2, 3, 4, 6, 8, 10, 12]
BASE_DMG = {"dagger": "1d4", "longsword": "1d8", "greataxe": "1d12", "spear": "1d6", "staff": "1d6", "shortbow": "1d6", "crossbow": "1d8"}  # the mod's looks.json weapons
BASE_AP = {"leather": 1, "chain": 2, "plate": 3}
# keep in step with the mod's sheet/conditions.json
CONDITIONS = {"burning", "freezing", "crushed", "winded", "withered", "blooming", "melting", "shocked", "confused", "frightened", "dazed",
              "charmed", "panicked", "hallucinating", "nightmare", "dreaming", "unconscious", "paralyze", "bleeding", "drowning", "broken",
              "deafened", "blinded", "restrained", "grappled", "nauseated", "poisoned", "sick", "blasted", "blungeoned", "piercing", "slashing",
              "hexed", "allured", "invisible", "infused", "sorrowful", "joyous", "enraged", "calmed"}
TYPE_NAMES = {"weapon": "Weapon", "ranged": "Ranged weapon", "shield": "Shield", "armor": "Armour", "head": "Headwear", "cloak": "Cloak",
              "hands": "Gloves", "feet": "Boots", "amulet": "Amulet", "ring": "Ring", "clothing": "Clothing", "consumable": "Consumable", "misc": "Item"}


class ItemError(ValueError):
    pass


def load(path: Path) -> list[dict]:
    out = json.loads(Path(path).read_text(encoding="utf-8"))
    check_all(out)
    return out


def check_all(all_items: list[dict]) -> None:
    seen = set()
    for i in all_items:
        check(i)
        if i["id"] in seen:
            raise ItemError(f"{i['id']}: the id is used twice")
        seen.add(i["id"])


def dice(s: str) -> tuple[int, int] | None:
    m = re.fullmatch(r"(\d+)d(\d+)", s or "")
    return (int(m[1]), int(m[2])) if m else None


def step(base: str, by: int) -> str:
    n, s = dice(base)
    return f"{n}d{DIE[max(0, min(len(DIE) - 1, DIE.index(s) + by))]}"


def grade_of(item: dict) -> str | None:
    """A relic's grade: its strongest enchantment's, by the item rules."""
    best = -1
    for e in item.get("enchant", []):
        if e.get("kind") == "damage":
            n, s = dice(e["dice"])
            best = max(best, 4 if n >= 4 else 3 if n == 3 else 2 if n == 2 else 0 if s <= 4 else 1)
        else:
            b = item.get("bonus", {})
            for k in ("core", "shell", "essence"):
                if k in b:
                    best = max(best, 2 if b[k] >= 2 else 0)
            if b.get("ap", 0) >= 2 or b.get("hp", 0) >= 4 or b.get("ep", 0) >= 2:
                best = max(best, 1)
            if any(k in b for k in ("ap", "hp", "ep", "mp", "init", "resist")):
                best = max(best, 0)
            if "skill" in b:
                best = max(best, 2)
    return GRADES[best] if best >= 0 else None


def check(i: dict) -> None:
    name = i.get("id") or i.get("name") or "?"

    def bad(why):
        raise ItemError(f"{name}: {why}")

    for k in i:
        if k not in GAME_FIELDS | OUR_FIELDS:
            bad(f"unknown field {k}")
    if not re.fullmatch(r"[a-z0-9-]+", i.get("id", "")):
        bad("needs an id of lowercase letters, digits and dashes")
    if not i.get("name"):
        bad("needs a name")
    if i.get("type") not in TYPES:
        bad(f"type {i.get('type')} isn't one of {TYPES}")
    if i.get("rarity") not in RARITIES:
        bad(f"rarity {i.get('rarity')} isn't one of {RARITIES}")
    if "weight" not in i:
        bad("needs a weight")
    t, r = i["type"], i["rarity"]
    if t in ("weapon", "ranged") and not all(k in i for k in ("dmg", "range", "hands", "aspect")):
        bad("a weapon needs dmg, range, hands and aspect")
    q = i.get("quality")
    if q is not None and q not in QUALITIES:
        bad(f"quality {q} isn't one of {QUALITIES}")
    if i.get("base"):
        if q is None:
            bad("a base item needs a quality")
        by = QUALITIES.index(q) - 1
        if i["base"] in BASE_DMG:
            want = step(BASE_DMG[i["base"]], by)
            if i.get("dmg") != want:
                bad(f"{q} {i['base']} should be {want}")
        elif i["base"] in BASE_AP:
            want = BASE_AP[i["base"]] + by
            if i.get("ap") != want:
                bad(f"{q} {i['base']} should be +{want} AP")
        else:
            bad(f"base {i['base']} isn't a game weapon or armour")
    b = i.get("bonus", {})
    if "adv" in b:
        bad("no advantage bonuses: advantage isn't a rule, use a flat bonus")
    if r == "mundane" and b:
        bad("mundane items have no bonus")
    if r == "trinket" and t in ("weapon", "ranged", "shield", "armor"):
        bad(f"a trinket can't be a {'weapon' if t == 'ranged' else t}")
    u = i.get("use", {})
    for c in b.get("resist", []) + u.get("cure", []) + list(u.get("apply", {})) + [e["causes"] for e in i.get("enchant", []) if e.get("causes")]:
        if c not in CONDITIONS:
            bad(f"condition {c} isn't one the game has")
    if r == "relic":
        if not i.get("grade"):
            bad("a relic needs a grade")
        if not i.get("enchant"):
            bad("a relic needs at least one enchantment")
        if i["grade"] != grade_of(i):
            bad(f"grade should be {grade_of(i)} for its enchantments, not {i['grade']}")
    elif i.get("grade") or i.get("enchant"):
        bad("only relics have a grade and enchantments")


# ---------- the page ----------

def game_def(i: dict) -> dict:
    return {k: v for k, v in i.items() if k in GAME_FIELDS}


def avg(d: str) -> float:
    n, s = dice(d) or (0, 0)
    return n * (s + 1) / 2


def power(i: dict) -> tuple[str, float]:
    """The Damage / AP cell and its sort value."""
    if "dmg" in i:
        extra = [e for e in i.get("enchant", []) if e.get("kind") == "damage"]
        return " + ".join([i["dmg"]] + [f"{e['dice']} {e.get('element', '')}".strip() for e in extra]), avg(i["dmg"]) + sum(avg(e["dice"]) for e in extra)
    if "ap" in i:
        return f"+{i['ap']} AP", i["ap"]
    u = i.get("use", {})
    for k, label in (("dmg", "{}"), ("heal", "heals {}"), ("ep", "{} EP")):
        if k in u:
            return label.format(u[k]), avg(u[k])
    return "—", -1


def reach(i: dict) -> tuple[str, int]:
    feet = i["range"] * 5 if "range" in i else i.get("use", {}).get("range", 0) * 5
    return (f"{feet} ft", feet) if feet else ("—", -1)


def rarity_label(i: dict) -> str:
    r = {"legendary": "Legendary relic"}.get(i["rarity"], i["rarity"].capitalize())
    return f"{r} · {i['grade'].capitalize()}" if i.get("grade") else r


def tier(i: dict) -> str:
    return i.get("grade") or i.get("quality") or ""


def weight(w) -> str:
    return f"{w:g} lb"


def row(i: dict) -> str:
    e = html.escape
    pw, pv = power(i)
    rg, rv = reach(i)
    order = RARITIES.index(i["rarity"]) * 10 + (GRADES.index(i["grade"]) if i.get("grade") else QUALITIES.index(i["quality"]) if i.get("quality") else 1)
    find = e(f"{i['name']} {i.get('text', '')}".lower())
    return (f'<tr data-id="{i["id"]}" data-rarity="{i["rarity"]}" data-type="{i["type"]}" data-tier="{tier(i)}" data-find="{find}">'
            f'<th scope="row" data-v="{e(i["name"])}"><a class="item" href="#item={i["id"]}" data-id="{i["id"]}">{e(i["name"])}</a></th>'
            f'<td data-v="{order}">{rarity_label(i)}</td>'
            f'<td data-v="{e(TYPE_NAMES[i["type"]])}">{TYPE_NAMES[i["type"]]}</td>'
            f'<td data-v="{pv}">{e(pw)}</td>'
            f'<td data-v="{rv}">{rg}</td>'
            f'<td data-v="{i["weight"]}">{weight(i["weight"])}</td>'
            f'<td data-v="{i.get("value", 0)}">{i.get("value", 0)}</td></tr>')


def options(values: list[tuple[str, str]], all_label: str) -> str:
    return f'<option value="">{all_label}</option>' + "".join(f'<option value="{v}">{html.escape(l)}</option>' for v, l in values)


def page(all_items: list[dict]) -> dict:
    """The Item Database page, as build.py's page dict (it numbers the § and renders it like any other entry)."""
    types = [t for t in TYPES if any(i["type"] == t for i in all_items)]
    heads = [("name", "Name"), ("rarity", "Rarity"), ("type", "Type"), ("power", "Damage / AP"), ("range", "Range"), ("weight", "Weight"), ("value", "Value (marks)")]
    head = "".join(f'<th scope="col"{" aria-sort=\"ascending\"" if k == "name" else ""}><button type="button" data-col="{n}">{l}</button></th>'
                   for n, (k, l) in enumerate(heads))
    data = json.dumps({i["id"]: game_def(i) for i in all_items}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    lede = ("Every item we've set down so far: mundane gear graded by craft, trinkets for the odd job, and relics graded by the strength "
            "of their enchantment. Hover or tap a name to see it as it shows in game.")
    body = f"""<h2 id="the-items">The items</h2>
<p>{lede}</p>
<form class="item-filters" role="search" aria-label="Filter the items" onsubmit="return false">
  <label>Search<input type="search" name="q" placeholder="Name or words in it" autocomplete="off"></label>
  <label>Rarity<select name="rarity">{options([(r, {"legendary": "Legendary relic"}.get(r, r.capitalize())) for r in RARITIES], "Any rarity")}</select></label>
  <label>Type<select name="type">{options([(t, TYPE_NAMES[t]) for t in types], "Any type")}</select></label>
  <label>Craft or grade<select name="tier">{options([(q, q.capitalize()) for q in QUALITIES] + [(g, g.capitalize()) for g in GRADES], "Any")}</select></label>
</form>
<p class="item-count" aria-live="polite">{len(all_items)} items</p>
<div class="table-wrap item-table"><table>
<thead><tr>{head}</tr></thead>
<tbody>{"".join(row(i) for i in sorted(all_items, key=lambda i: i["name"].lower()))}</tbody>
</table></div>
<p class="item-none" hidden>No item matches those filters.</p>
<script type="application/json" id="item-data">{data}</script>"""
    return {"title": "Item Database", "slug": "item-database", "file": "item-database.html", "depth": 0, "empty": False, "vol": "catalogs",
            "md": "", "body": body, "text": lede, "toc": [{"id": "the-items", "num": "", "name": "The items", "children": []}],
            "extra": '<link rel="stylesheet" href="assets/items.css?v={v}">\n<script src="assets/itemtip.js?v={v}" defer></script>\n'
                     '<script src="assets/items.js?v={v}" defer></script>\n'}


def search(all_items: list[dict], p: dict) -> list[dict]:
    """One search entry per item, opening its tooltip."""
    return [{"p": p["title"], "h": i["name"], "u": f'{p["file"]}#item={i["id"]}',
             "x": f'{rarity_label(i)} · {TYPE_NAMES[i["type"]]} · {power(i)[0]}. {i.get("text", "")}'} for i in all_items]
