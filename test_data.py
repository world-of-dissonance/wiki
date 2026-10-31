"""Checks what build.py publishes for the site's tools. Run after a build: python test_data.py"""
import json

trees = {t["id"]: t for t in json.load(open("site/trees.json", encoding="utf-8"))}
assert set(trees) >= {"mind", "trait", "balance", "element", "infuse", "deceive", "rampart"}, sorted(trees)
assert trees["mind"]["name"] == "Mind"
assert trees["mind"]["main"] == ["Telepathy", "Telekinesis", "Thought"], trees["mind"]["main"]
assert [b["name"] for b in trees["mind"]["branches"]] == ["Control", "Bind", "Perception", "Concept"], trees["mind"]["branches"]
assert trees["mind"]["branches"][0]["tiers"] == ["Puppet", "Combine", "Tinker"]
assert [b["name"] for b in trees["element"]["branches"]] == ["Optimized", "Destruction", "Traditional", "New Age"], trees["element"]["branches"]  # the doc repeats Traditional
skills = json.load(open("site/skills.json", encoding="utf-8"))
assert all(1 <= s["slot"] <= 5 for s in skills), [s["name"] for s in skills if not 1 <= s.get("slot", 0) <= 5]
assert next(s for s in skills if s["name"] == "Connective Net")["slot"] == 2
print("ok")
