// Checks assets/itemtip.js against what the mod's GearScreen tooltip shows for the same items. Run: node test_itemtip.js
const assert = require("node:assert/strict");
const T = require("./assets/itemtip.js");
const items = Object.fromEntries(require("./items/items.json").map(i => [i.id, i]));
const tip = id => T.tip(T.clean(items[id]));

let t = tip("emberbite");
assert.equal(t.name, "EMBERBITE");
assert.deepEqual(t.chips, [["Relic", 0xB07CF0], ["5 ft", null], ["One hand", null]]);
assert.equal(t.big, "1–10");
assert.equal(t.small, "1d10 Shell damage");
assert.equal(t.foot, "3.0 LB · 400 MARKS");

t = tip("crude-shortbow");
assert.deepEqual(t.chips, [["Mundane", 0xB4AC9C], ["60 ft", null]]);  // ranged weapons show no hands chip

t = tip("fine-chain-coat");
assert.deepEqual(t.chips, [["Mundane", 0xB4AC9C], ["Armour", null]]);
assert.equal(t.big, "+3 AP");
assert.equal(t.small, "while worn");
assert.equal(t.foot, "20.0 LB · 200 MARKS");

t = tip("flashpowder-bomb");
assert.deepEqual(t.chips, [["Trinket", 0x55C7B4], ["Primary", 0xEEE1B8]]);
assert.equal(t.big, null);
assert.equal(t.use, "Use (Primary action, everyone within 10 ft of a point): gives 1 blinded.");

t = tip("field-dressing");
assert.equal(t.big, "1–4");
assert.equal(t.small, "1d4 HP");
assert.equal(t.use, "Use (Instant action, yourself): heals 1d4 HP, ends bleeding.");
assert.equal(t.foot, "0.1 LB · 5 MARKS");

t = tip("dissonance-shard");
assert.equal(t.small, "2d6 Essence damage");
assert.equal(t.use, "Use (Primary action, one creature within 30 ft): deals 2d6 damage (Essence vs AP).");

assert.deepEqual(tip("hushbell-charm").bonus, ["Can't be frightened"]);
assert.deepEqual(tip("tread-ring").bonus, ["+5 ft movement"]);
assert.deepEqual(tip("lincuel-censer").bonus, ["+2 to Essence rolls"]);
assert.deepEqual(tip("peraxian-climbing-line").chips, [["Mundane", 0xB4AC9C], ["Item", null]]);

// Gear.clean's defaults, as the game applies them to a catalogue item
const bare = T.clean({ name: " Club ", type: "weapon", rarity: "shiny" });
assert.deepEqual(bare, { name: "Club", type: "weapon", rarity: "mundane", weight: 3, value: 0, dmg: "1d4", range: 1, aspect: "shell", hands: 1 });
assert.equal(T.tip(bare).foot, "3.0 LB");
console.log("ok");
