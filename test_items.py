"""Checks the item database: the items file, its rules, and the page it becomes. Run: python test_items.py"""
import copy
import json

import items

ALL = items.load(items.FILE)
BY = {i["id"]: i for i in ALL}


def fails(item, why):
    try:
        items.check(item)
    except items.ItemError as e:
        assert why in str(e), (why, str(e))
        return
    raise AssertionError(f"accepted: {why}")


def changed(id_, **kw):
    i = copy.deepcopy(BY[id_])
    i.update(kw)
    return i


def test_starter_set_loads():
    assert len(ALL) == 18, len(ALL)
    assert [i["rarity"] for i in ALL].count("relic") == 4


def test_rules():
    fails(changed("emberbite", sharpness=3), "unknown field sharpness")
    fails(changed("mud-sung-spear", dmg="1d6"), "fine spear should be 1d8")
    fails(changed("fine-chain-coat", ap=2), "fine chain should be +3 AP")
    fails(changed("crude-shortbow", quality="rusty"), "quality rusty")
    fails(changed("emberbite", grade="major"), "grade should be minor")
    fails(changed("tread-ring", bonus={"adv": ["shell"]}), "advantage")
    fails(changed("tread-ring", type="weapon", dmg="1d4", range=1, hands=1, aspect="shell", bonus={}), "trinket can't be a weapon")
    fails(changed("lincuel-salt", use={"action": "instant", "target": "self", "cure": ["tired"]}), "condition tired")
    fails(changed("masterwork-longsword", bonus={"hp": 2}), "mundane items have no bonus")
    fails(changed("emberbite", grade=None), "relic needs a grade")
    dup = [BY["tread-ring"], BY["tread-ring"]]
    try:
        items.check_all(dup)
        raise AssertionError("accepted duplicate ids")
    except items.ItemError as e:
        assert "tread-ring" in str(e)


def test_grades():
    dmg = lambda d: {"rarity": "relic", "enchant": [{"kind": "damage", "dice": d}]}
    assert [items.grade_of(dmg(d)) for d in ("1d2", "1d4", "1d6", "1d8", "2d6", "2d8", "3d6", "3d8", "4d6", "6d10")] == \
        ["minor", "minor", "medium", "medium", "major", "major", "majestic", "majestic", "mythic", "mythic"]
    bonus = lambda b: {"rarity": "relic", "bonus": b, "enchant": [{"kind": "bonus"}]}
    assert items.grade_of(bonus({"essence": 1})) == "minor"
    assert items.grade_of(bonus({"resist": ["frightened"]})) == "minor"
    assert items.grade_of(bonus({"hp": 4})) == "medium"
    assert items.grade_of(bonus({"essence": 2})) == "major"
    assert items.grade_of(bonus({"skill": "Mediate"})) == "major"


def test_page():
    p = items.page(ALL)
    assert p["file"] == "item-database.html" and p["vol"] == "catalogs"
    assert p["body"].count('<tr data-id=') == 18
    row = p["body"].split('<tr data-id="emberbite"')[1].split("</tr>")[0]
    assert "Relic · Minor" in row and "1d10 + 1d4 fire" in row, row
    assert ">5 ft<" in row and ">3 lb<" in row and ">400<" in row, row
    data = json.loads(p["body"].split('<script type="application/json" id="item-data">')[1].split("</script>")[0])
    assert data["emberbite"]["name"] == "Emberbite" and "grade" not in data["emberbite"]  # only what the game reads
    assert any(e["u"] == "item-database.html#item=emberbite" for e in items.search(ALL, p))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
