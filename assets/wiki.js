// Search over search.json, the mobile contents drawer, and the "on this page" highlight.
(() => {
  const q = document.getElementById("q"), list = document.getElementById("results");
  let index = null, hits = [], sel = -1;
  const esc = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const norm = s => s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");

  async function load() {
    if (!index) index = fetch("search.json").then(r => r.json()).then(rows => rows.map(r => ({ ...r, nh: norm(r.h), nx: norm(r.x), np: norm(r.p) })));
    return index;
  }
  function mark(text, words) {
    let out = esc(text);
    for (const w of words) out = out.replace(new RegExp("(" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"), "<mark>$1</mark>");
    return out;
  }
  function snippet(x, nx, words) {
    const at = Math.max(0, nx.indexOf(words[0]) - 50);
    return (at ? "…" : "") + x.slice(at, at + 150) + (x.length > at + 150 ? "…" : "");
  }
  async function run() {
    const words = norm(q.value).split(/\s+/).filter(w => w.length > 1);
    if (!words.length) { list.hidden = true; return; }
    const rows = await load();
    hits = rows.map(r => {
      let s = 0;
      for (const w of words) {
        const inH = r.nh.includes(w), inX = r.nx.includes(w), inP = r.np.includes(w);
        if (!inH && !inX && !inP) return null;
        s += (inH ? 10 : 0) + (r.nh.startsWith(w) ? 5 : 0) + (inP ? 2 : 0) + (inX ? 1 : 0);
      }
      return { r, s };
    }).filter(Boolean).sort((a, b) => b.s - a.s).slice(0, 12);
    sel = -1;
    list.innerHTML = hits.length ? hits.map(({ r }, i) =>
      `<li><a href="${r.u}" data-i="${i}"><span class="p">${esc(r.p)}</span><div class="h">${mark(r.h, words)}</div>` +
      (r.x ? `<span class="x">${mark(snippet(r.x, r.nx, words), words)}</span>` : "") + "</a></li>").join("")
      : `<li class="none">Nothing matches “${esc(q.value.trim())}”.</li>`;
    list.hidden = false;
  }
  function move(d) {
    const links = list.querySelectorAll("a");
    if (!links.length) return;
    sel = (sel + d + links.length) % links.length;
    links.forEach((a, i) => a.classList.toggle("on", i === sel));
    links[sel].scrollIntoView({ block: "nearest" });
  }
  if (q) {
    let t;
    q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(run, 80); });
    q.addEventListener("focus", () => { load(); if (q.value.trim()) run(); });
    q.addEventListener("keydown", e => {
      if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
      else if (e.key === "Enter") { const a = list.querySelectorAll("a")[Math.max(sel, 0)]; if (a) location.href = a.href; }
      else if (e.key === "Escape") { list.hidden = true; q.blur(); }
    });
    document.addEventListener("click", e => { if (!e.target.closest(".search")) list.hidden = true; });
    document.addEventListener("keydown", e => {
      if (e.key === "/" && document.activeElement !== q && !/input|textarea/i.test(document.activeElement.tagName)) { e.preventDefault(); q.focus(); }
    });
  }

  const menu = document.getElementById("menu"), nav = document.getElementById("nav");
  if (menu && nav) {
    menu.addEventListener("click", () => { const open = nav.classList.toggle("open"); menu.setAttribute("aria-expanded", open); });
    nav.addEventListener("click", e => { if (e.target.closest("a")) { nav.classList.remove("open"); menu.setAttribute("aria-expanded", false); } });
  }

  // picture strips: arrows, arrow keys and the "2 / 5" count
  document.querySelectorAll(".gallery .strip").forEach(strip => {
    const fig = strip.parentElement, n = strip.children.length;
    const prev = fig.querySelector(".prev"), next = fig.querySelector(".next"), count = fig.querySelector(".count");
    const at = () => Math.round(strip.scrollLeft / strip.clientWidth);
    const go = i => strip.scrollTo({ left: Math.max(0, Math.min(n - 1, i)) * strip.clientWidth });
    const sync = () => { const i = at(); count.textContent = `${i + 1} / ${n}`; prev.disabled = i === 0; next.disabled = i === n - 1; };
    prev.addEventListener("click", () => go(at() - 1));
    next.addEventListener("click", () => go(at() + 1));
    strip.addEventListener("keydown", e => {
      if (e.key === "ArrowRight") { e.preventDefault(); go(at() + 1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); go(at() - 1); }
    });
    strip.addEventListener("scroll", () => requestAnimationFrame(sync), { passive: true });
    sync();
  });

  // heading anchors and the current section in "On this page"
  document.querySelectorAll(".prose :is(h2,h3,h4)[id]").forEach(h => {
    const a = document.createElement("a"); a.className = "anchor"; a.href = "#" + h.id; a.textContent = "#"; a.setAttribute("aria-label", "Link to this section");
    h.prepend(a);
  });
  const tocLinks = [...document.querySelectorAll(".toc a")];
  if (tocLinks.length && "IntersectionObserver" in window) {
    const byId = new Map(tocLinks.map(a => [decodeURIComponent(a.hash.slice(1)), a]));
    const seen = new Set();
    const io = new IntersectionObserver(es => {
      es.forEach(e => e.isIntersecting ? seen.add(e.target.id) : seen.delete(e.target.id));
      const first = [...byId.keys()].find(id => seen.has(id));
      if (first) tocLinks.forEach(a => a.classList.toggle("on", a === byId.get(first)));
    }, { rootMargin: "-80px 0px -60% 0px" });
    byId.forEach((_, id) => { const el = document.getElementById(id); if (el) io.observe(el); });
  }
  const cur = document.querySelector(".nav [aria-current]");
  if (cur) cur.scrollIntoView({ block: "center" });
})();
