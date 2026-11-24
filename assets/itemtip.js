// The game's item tooltip text, ported from the mod (wod-charsheet): Gear.clean, Gear.useText, Gear.bonusList and
// GearScreen's Tip, rarityColour, rarityName, typeName and spread. Keep in step with those; test_itemtip.js checks the port
// against tooltip_golden.json, which the mod's ItemTipGoldenTest writes.
(() => {
  const TYPES = ["weapon", "ranged", "shield", "armor", "head", "cloak", "hands", "feet", "amulet", "ring", "clothing", "consumable", "misc"];
  const RARITIES = ["mundane", "trinket", "relic", "legendary"];
  const INSTANT = 0xBCE1EC, PRIMARY = 0xEEE1B8;
  const has = (o, k) => o != null && Object.prototype.hasOwnProperty.call(o, k);
  const str = (o, k, f) => has(o, k) && o[k] !== null && typeof o[k] !== "object" ? String(o[k]) : f;
  const javaRound = x => Math.floor(x + 0.5);
  const num = (o, k, f) => { if (!has(o, k)) return f; const x = Number(o[k]); return Number.isFinite(x) ? javaRound(x) : f; };
  const dec = (o, k, f) => { if (!has(o, k)) return f; const x = Number(o[k]); return Number.isFinite(x) ? x : f; };
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
  const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
  const signed = n => (n >= 0 ? "+" : "") + n;
  const validDice = s => /^(\d{0,2}d\d{1,3}([+-]\d{1,3})?|\d{1,3})$/.test(s);
  const javaDouble = x => Number.isInteger(x) ? x.toFixed(1) : String(x); // Java's "" + double

  function defaultWeight(type, d) {
    switch (type) {
      case "weapon": return num(d, "hands", 1) >= 2 ? 7 : 3;
      case "ranged": return 2;
      case "shield": return 6;
      case "armor": return 8 + 12 * Math.max(0, num(d, "ap", 1));
      case "head": case "hands": case "feet": return 2;
      case "cloak": case "clothing": return 3;
      case "amulet": case "ring": return 0.1;
      case "consumable": return 0.5;
      default: return 1;
    }
  }

  /** Gear.clean: an item as the game holds it once given. */
  function clean(i) {
    const d = {};
    d.name = str(i, "name", "").trim().slice(0, 60);
    let type = str(i, "type", "misc");
    if (type === "item") type = "misc";
    d.type = TYPES.includes(type) ? type : "misc";
    const rarity = str(i, "rarity", "mundane");
    d.rarity = RARITIES.includes(rarity) ? rarity : "mundane";
    d.weight = clamp(javaRound(dec(i, "weight", defaultWeight(d.type, i)) * 10) / 10, 0, 500);
    d.value = clamp(num(i, "value", 0), 0, 1_000_000);
    const text = str(i, "text", "");
    if (text.trim()) d.text = text.slice(0, 1000);
    if (/^(weapon|ranged)$/.test(d.type)) {
      d.dmg = str(i, "dmg", "1d4").replace(/ /g, "");
      d.range = clamp(num(i, "range", d.type === "ranged" ? 12 : 1), 1, 60);
      const aspect = str(i, "aspect", "shell");
      d.aspect = ["core", "shell", "essence"].includes(aspect) ? aspect : "shell";
      d.hands = clamp(num(i, "hands", d.type === "ranged" ? 2 : 1), 1, 2);
    }
    if (has(i, "ap")) d.ap = clamp(num(i, "ap", 0), -10, 20);
    if (i.bonus && typeof i.bonus === "object") {
      const b = i.bonus, out = {};
      for (const k of ["core", "shell", "essence", "ap", "hp", "ep", "mp", "init"]) {
        const v = num(b, k, 0);
        if (v !== 0) out[k] = clamp(v, -30, 30);
      }
      for (const k of ["adv", "resist"]) if (Array.isArray(b[k])) {
        const a = b[k].filter(x => typeof x !== "object").slice(0, 8).map(x => String(x).toLowerCase());
        if (a.length) out[k] = a;
      }
      const skill = str(b, "skill", "");
      if (skill.trim()) out.skill = skill.slice(0, 60);
      if (Object.keys(out).length) d.bonus = out;
    }
    if (d.type === "consumable") {
      const u = i.use && typeof i.use === "object" ? i.use : {}, out = {};
      out.action = str(u, "action", "instant") === "primary" ? "primary" : "instant";
      const target = str(u, "target", "self");
      out.target = ["self", "one", "area"].includes(target) ? target : "self";
      if (out.target !== "self") out.range = clamp(num(u, "range", 6), 1, 30);
      if (out.target === "area") out.radius = clamp(num(u, "radius", 2), 1, 6);
      for (const k of ["heal", "ep", "dmg"]) {
        const dice = str(u, k, "").replace(/ /g, "");
        if (dice && validDice(dice)) out[k] = dice;
      }
      if (Array.isArray(u.cure)) out.cure = u.cure;
      if (u.apply && typeof u.apply === "object") out.apply = u.apply;
      const aspect = str(u, "aspect", "essence");
      out.aspect = ["core", "shell", "essence"].includes(aspect) ? aspect : "essence";
      d.use = out;
    }
    return d;
  }

  function bonusList(b) {
    const out = [];
    for (const k of ["core", "shell", "essence"]) if (has(b, k)) out.push(signed(num(b, k, 0)) + " to " + cap(k) + " rolls");
    if (has(b, "ap")) out.push(signed(num(b, "ap", 0)) + " AP");
    if (has(b, "hp")) out.push(signed(num(b, "hp", 0)) + " max HP");
    if (has(b, "ep")) out.push(signed(num(b, "ep", 0)) + " max EP");
    if (has(b, "mp")) out.push(signed(num(b, "mp", 0)) + " ft movement");
    if (has(b, "init")) out.push(signed(num(b, "init", 0)) + " initiative");
    if (has(b, "adv")) b.adv.forEach(x => out.push("advantage on " + cap(String(x)) + " rolls"));
    if (has(b, "resist")) b.resist.forEach(x => out.push("can't be " + x));
    if (has(b, "skill")) out.push("grants " + b.skill);
    return out;
  }

  function useText(u) {
    const out = [];
    if (has(u, "heal")) out.push("heals " + u.heal + " HP");
    if (has(u, "ep")) out.push("restores " + u.ep + " EP");
    if (has(u, "dmg")) out.push("deals " + u.dmg + " damage (" + cap(str(u, "aspect", "essence")) + " vs AP)");
    if (has(u, "cure")) u.cure.forEach(x => out.push("ends " + x));
    if (has(u, "apply")) Object.entries(u.apply).forEach(([k, v]) => out.push("gives " + javaRound(Number(v)) + " " + k));
    const target = str(u, "target", "self");
    const who = target === "one" ? "one creature within " + num(u, "range", 6) * 5 + " ft"
      : target === "area" ? "everyone within " + num(u, "radius", 2) * 5 + " ft of a point" : "yourself";
    return "Use (" + (str(u, "action", "instant") === "primary" ? "Primary" : "Instant") + " action, " + who + "): " + out.join(", ") + ".";
  }

  const rarityColour = r => ({ trinket: 0x55C7B4, relic: 0xB07CF0, legendary: 0xF0A53C }[r] ?? 0xB4AC9C);
  const rarityName = r => ({ trinket: "Trinket", relic: "Relic", legendary: "Legendary Relic" }[r] ?? "Mundane");
  function typeName(d) {
    const t = str(d, "type", "misc");
    if (t === "weapon") return num(d, "hands", 1) >= 2 ? "Two-handed weapon" : "Weapon";
    return { ranged: "Ranged weapon", shield: "Shield", armor: "Armour", head: "Headwear", cloak: "Cloak", hands: "Gloves", feet: "Boots",
      amulet: "Amulet", ring: "Ring", clothing: "Clothing", consumable: "Consumable" }[t] ?? "Item";
  }
  function spread(dice) {
    const m = /^(\d+)d(\d+)(?:\+(\d+))?$/.exec(dice.trim());
    if (!m) return dice;
    const n = +m[1], s = +m[2], b = m[3] ? +m[3] : 0;
    return (n + b) + "–" + (n * s + b);
  }

  /** GearScreen.Tip's content for an item as the game holds it: name, chips, the gold slab, use, bonuses, lore, foot. */
  function tip(d, qty = 1) {
    const rarity = str(d, "rarity", "mundane"), u = d.use || null;
    const t = { name: str(d, "name", "?").toUpperCase(), rarity: rarityColour(rarity), chips: [[rarityName(rarity), rarityColour(rarity)]],
      big: null, small: null, use: null, bonus: [], lore: null, foot: "" };
    if (has(d, "dmg")) {
      t.chips.push([num(d, "range", 1) * 5 + " ft", null]);
      if (str(d, "type", "misc") === "weapon") t.chips.push([num(d, "hands", 1) >= 2 ? "Two hands" : "One hand", null]);
      t.big = spread(String(d.dmg));
      t.small = d.dmg + " " + cap(str(d, "aspect", "shell")) + " damage";
    } else if (u) {
      const primary = str(u, "action", "instant") === "primary";
      t.chips.push([primary ? "Primary" : "Instant", primary ? PRIMARY : INSTANT]);
    } else t.chips.push([typeName(d), null]);
    if (t.big === null && has(d, "ap")) { t.big = signed(num(d, "ap", 0)) + " AP"; t.small = "while worn"; }
    if (t.big === null && u)
      for (const [k, label] of [["heal", "HP"], ["dmg", cap(str(u, "aspect", "essence")) + " damage"], ["ep", "EP"]])
        if (t.big === null && has(u, k)) { t.big = spread(String(u[k])); t.small = u[k] + " " + label; }
    if (u) t.use = useText(u);
    if (d.bonus) t.bonus = bonusList(d.bonus).map(cap);
    if (has(d, "text")) t.lore = String(d.text);
    const value = num(d, "value", 0);
    t.foot = (javaDouble(dec(d, "weight", 0)) + " lb" + (value > 0 ? " · " + value + " marks" : "") + (qty > 1 ? " · ×" + qty : "")).toUpperCase();
    return t;
  }

  const api = { clean, tip, useText, bonusList, spread, rarityColour, rarityName, typeName };
  if (typeof module !== "undefined") module.exports = api;
  else globalThis.ItemTip = api;
})();
