// The Item Database page: sortable columns, filters kept in the address (#rarity=relic&type=weapon), and the game's
// item tooltip on hover, focus or tap (its text from itemtip.js, its look from items.css).
(() => {
  const table = document.querySelector(".item-table table"), form = document.querySelector(".item-filters");
  if (!table || !form || !globalThis.ItemTip) return;
  const data = JSON.parse(document.getElementById("item-data").textContent);
  const body = table.tBodies[0], rows = [...body.rows], heads = [...table.tHead.rows[0].cells];
  const count = document.querySelector(".item-count"), none = document.querySelector(".item-none");
  const TEXT_COLS = new Set([0, 2]);
  const hex = c => "#" + c.toString(16).padStart(6, "0");

  // --- sorting ---
  let sortCol = 0, sortDir = 1;
  function sort() {
    const key = r => r.cells[sortCol].dataset.v;
    rows.sort((a, b) => sortDir * (TEXT_COLS.has(sortCol) ? key(a).localeCompare(key(b)) : parseFloat(key(a)) - parseFloat(key(b)))
      || a.cells[0].dataset.v.localeCompare(b.cells[0].dataset.v));
    body.append(...rows);
    heads.forEach((h, i) => i === sortCol ? h.setAttribute("aria-sort", sortDir > 0 ? "ascending" : "descending") : h.removeAttribute("aria-sort"));
  }
  table.tHead.addEventListener("click", e => {
    const b = e.target.closest("button[data-col]");
    if (!b) return;
    const col = +b.dataset.col;
    sortDir = col === sortCol ? -sortDir : 1;
    sortCol = col;
    sort();
  });

  // --- filters, mirrored in the address so a link opens the same view ---
  const fields = ["q", "rarity", "type", "tier"];
  function filter(write = true) {
    const f = Object.fromEntries(fields.map(k => [k, form.elements[k].value.trim().toLowerCase()]));
    let shown = 0;
    for (const r of rows) {
      const ok = (!f.q || r.dataset.find.includes(f.q)) && (!f.rarity || r.dataset.rarity === f.rarity)
        && (!f.type || r.dataset.type === f.type) && (!f.tier || r.dataset.tier === f.tier);
      r.hidden = !ok;
      shown += ok;
    }
    count.textContent = shown === rows.length ? `${rows.length} items` : `${shown} of ${rows.length} items`;
    none.hidden = shown > 0;
    if (write) {
      const h = new URLSearchParams(fields.filter(k => f[k]).map(k => [k, form.elements[k].value.trim()])).toString();
      history.replaceState(null, "", h ? "#" + h : location.pathname + location.search);
    }
  }
  form.addEventListener("input", () => filter());
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    for (const k of fields) form.elements[k].value = h.get(k) || "";
    filter(false);
    const id = h.get("item"), link = id && body.querySelector(`a.item[data-id="${CSS.escape(id)}"]`);
    if (link) {
      link.closest("tr").scrollIntoView({ block: "center" });
      link.focus({ preventScroll: true });
    }
  }
  addEventListener("hashchange", readHash);

  // --- the tooltip: GearScreen's Cut-skin card ---
  const tipEl = document.createElement("div");
  tipEl.className = "itip";
  tipEl.id = "item-tip";
  tipEl.setAttribute("role", "tooltip");
  tipEl.hidden = true;
  document.body.append(tipEl);
  let openFor = null;
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  function diamond(colour) {
    const ns = "http://www.w3.org/2000/svg", s = document.createElementNS(ns, "svg");
    s.setAttribute("viewBox", "-2.6 -2.6 5.2 5.2");
    s.setAttribute("class", "dia");
    s.setAttribute("aria-hidden", "true");
    for (const [r, fill] of [[2.6, "#232B42"], [1.8, hex(colour)]]) {
      const p = document.createElementNS(ns, "polygon");
      p.setAttribute("points", `0,${-r} ${r},0 0,${r} ${-r},0`);
      p.setAttribute("fill", fill);
      s.append(p);
    }
    return s;
  }
  // GearScreen.Tip.width(): as wide as its widest line wants, measured in the game's fonts (canvas units), 110 to 165
  const FONTS = { anton: '"WoD Anton"', body: '"WoD Fira Sans"', strong: '600 1px "WoD Fira Sans"', tab: '700 1px "WoD Fira Mono"', caption: 'italic 1px "WoD Garamond"' };
  const ctx = document.createElement("canvas").getContext("2d");
  for (const f of Object.values(FONTS)) document.fonts.load(f.includes("1px") ? f.replace("1px", "10px") : `10px ${f}`);  // measured before first use
  function measure(font, size, s) {
    const f = FONTS[font];
    ctx.font = f.includes("1px") ? f.replace("1px", size * 20 + "px") : `${size * 20}px ${f}`;
    return ctx.measureText(s).width / 20;
  }
  function tipWidth(t) {
    const PAD = 7;
    let w = measure("anton", 11, t.name) + 16, row = -3;
    for (const [text, colour] of t.chips) row += measure("tab", 5.5, text.toUpperCase()) + 7 + (colour !== null ? 6 : 0) + 3;
    w = Math.max(w, row + 2 * PAD);
    if (t.big !== null) w = Math.max(w, measure("anton", 13, t.big) + measure("body", 6.5, t.small) + 12 + 2 * PAD);
    if (t.use) w = Math.max(w, measure("body", 6.5, t.use) + 2 * PAD);
    for (const b of t.bonus) w = Math.max(w, measure("strong", 6.5, b) + 7 + 2 * PAD);
    if (t.lore) w = Math.max(w, measure("caption", 7.5, t.lore) + 8 + 2 * PAD);
    w = Math.max(w, measure("tab", 5.5, t.foot) + 2 * PAD);
    return Math.max(110, Math.min(165, w));
  }
  function fill(id) {
    const t = ItemTip.tip(ItemTip.clean(data[id]));
    tipEl.style.width = `calc(${tipWidth(t)} * var(--u))`;
    const chips = el("div", "chips");
    for (const [text, colour] of t.chips) {
      const c = el("span", "chip");
      if (colour !== null) c.append(diamond(colour));
      c.append(el("span", null, text.toUpperCase()));
      chips.append(c);
    }
    const parts = [el("div", "tag", t.name), chips];
    if (t.big !== null) {
      const slab = el("div", "slab");
      slab.append(el("b", null, t.big), el("span", null, t.small));
      parts.push(slab);
    }
    if (t.use) parts.push(el("p", "use", t.use));
    if (t.bonus.length) {
      const ul = el("ul", "bonus");
      t.bonus.forEach(b => ul.append(el("li", null, b)));
      parts.push(ul);
    }
    if (t.lore) {
      const lore = el("p", "lore", t.lore);
      lore.style.borderLeftColor = hex(t.rarity);
      parts.push(lore);
    }
    parts.push(el("p", "foot", t.foot));
    tipEl.replaceChildren(...parts);
  }
  function place(x, y) {
    const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    tipEl.style.left = Math.max(6, Math.min(x + 12, innerWidth - w - 8)) + "px";
    tipEl.style.top = Math.max(8, Math.min(y + 12, innerHeight - h - 8)) + "px";
  }
  function show(a, x, y) {
    if (openFor !== a) {
      fill(a.dataset.id);
      openFor = a;
      a.setAttribute("aria-describedby", "item-tip");
    }
    tipEl.hidden = false;
    if (x === undefined) {
      const r = a.getBoundingClientRect();
      x = r.left;
      y = r.bottom;
    }
    place(x, y);
  }
  function hide() {
    tipEl.hidden = true;
    if (openFor) openFor.removeAttribute("aria-describedby");
    openFor = null;
  }
  const touch = () => matchMedia("(hover: none)").matches;
  body.addEventListener("mouseover", e => { const a = e.target.closest("a.item"); if (a && !touch()) show(a, e.clientX, e.clientY); });
  body.addEventListener("mousemove", e => { if (openFor && e.target.closest("a.item") === openFor) place(e.clientX, e.clientY); });
  body.addEventListener("mouseout", e => { if (e.target.closest("a.item") && !touch()) hide(); });
  // keyboard focus only: a tap focuses too, and its click below does the opening
  body.addEventListener("focusin", e => { const a = e.target.closest("a.item"); if (a && a.matches(":focus-visible")) show(a); });
  body.addEventListener("focusout", e => { if (e.target.closest("a.item")) hide(); });
  document.addEventListener("click", e => {
    const a = e.target.closest("a.item");
    if (a) {
      e.preventDefault();
      if (openFor === a && touch()) hide();
      else show(a, e.clientX, e.clientY);
      return;
    }
    if (!tipEl.contains(e.target)) hide();
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape") hide(); });
  addEventListener("scroll", () => { if (openFor && !touch()) hide(); }, { passive: true });

  sort();
  readHash();
})();
