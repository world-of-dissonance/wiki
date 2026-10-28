// Search, picture strips, § links, the running head's guide words and the last-read ribbon.
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

  // § numbers are the section links: click one to get a link you can share ("see §4.3")
  document.querySelectorAll(".text :is(h2,h3)[id] > .sec").forEach(sec => {
    const a = document.createElement("a");
    a.className = "sec"; a.href = "#" + sec.parentElement.id; a.textContent = sec.textContent;
    a.setAttribute("aria-label", `Link to ${sec.textContent}`);
    sec.replaceWith(a);
  });

  // where you are: highlight in "In this entry", guide words in the running head, and the last-read ribbon
  const store = {
    get() { try { return JSON.parse(localStorage.getItem("wod-last") || "null"); } catch { return null; } },
    set(v) { try { localStorage.setItem("wod-last", JSON.stringify(v)); } catch {} },
  };
  const body = document.body, page = body.dataset.page;
  const marginLinks = [...document.querySelectorAll(".margin a")];
  const guide = document.querySelector(".run .guide");
  const heads = [...document.querySelectorAll(".text h2[id], .text h3[id]")];
  function markSection(h) {
    const id = h ? h.id : "";
    marginLinks.forEach(a => a.classList.toggle("on", decodeURIComponent(a.hash.slice(1)) === id));
    if (guide && h) guide.textContent = h.textContent.replace(/\s+/g, " ").trim();
    if (page) store.set({ page, id, title: body.dataset.title, vol: body.dataset.vol, section: h ? h.textContent.replace(/\s+/g, " ").trim() : "" });
  }
  if (heads.length && "IntersectionObserver" in window) {
    const seen = new Set();
    const io = new IntersectionObserver(es => {
      es.forEach(e => e.isIntersecting ? seen.add(e.target) : seen.delete(e.target));
      const top = heads.find(h => seen.has(h));
      if (top) markSection(top);
      else {  // between headings: the last one above the fold
        const above = heads.filter(h => h.getBoundingClientRect().top < 120).pop();
        if (above) markSection(above);
      }
    }, { rootMargin: "0px 0px -70% 0px" });
    heads.forEach(h => io.observe(h));
  } else if (page) markSection(null);

  const last = store.get();
  if (last && last.vol) {
    const tab = document.querySelector(`.thumb[data-vol="${last.vol}"]`);
    if (tab) { tab.classList.add("last"); tab.title = `You were reading ${last.title}`; }
    const resume = document.querySelector(".btn.resume");
    if (resume && last.page) {
      resume.href = last.page + (last.id ? "#" + last.id : "");
      resume.textContent = `Continue: ${last.title}`;
      resume.hidden = false;
    }
  }

  // glossary terms: a definition on hover or first tap; a second tap (or a click on desktop) opens the entry
  let gloss = null, pop = null, openFor = null, hideTimer = 0;
  const loadGloss = () => gloss || (gloss = fetch("glossary.json").then(r => r.json()).catch(() => ({})));
  function hidePop() { if (pop) pop.hidden = true; openFor = null; }
  async function showPop(a) {
    const g = (await loadGloss())[a.dataset.term];
    if (!g) return;
    if (!pop) {
      pop = document.createElement("div"); pop.className = "pop"; pop.id = "term-pop"; pop.setAttribute("role", "tooltip");
      pop.addEventListener("mouseenter", () => clearTimeout(hideTimer));
      pop.addEventListener("mouseleave", () => { hideTimer = setTimeout(hidePop, 160); });
      document.body.append(pop);
    }
    pop.replaceChildren();
    const t = document.createElement("strong"); t.textContent = g.t;
    const d = document.createElement("p"); d.textContent = g.d;
    const more = document.createElement("a"); more.href = a.getAttribute("href"); more.textContent = `Read it in ${g.p}`;
    pop.append(t, d, more);
    pop.hidden = false; openFor = a; a.setAttribute("aria-describedby", "term-pop");
    const r = a.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
    const below = r.bottom + 8 + h < innerHeight;
    pop.style.left = Math.max(12, Math.min(innerWidth - w - 12, r.left)) + "px";
    pop.style.top = (below ? r.bottom + 8 : Math.max(8, r.top - h - 8)) + "px";
  }
  document.addEventListener("mouseover", e => {
    const a = e.target.closest("a.term");
    if (a && a !== openFor) { clearTimeout(hideTimer); showPop(a); }
  });
  document.addEventListener("mouseout", e => {
    if (e.target.closest("a.term")) hideTimer = setTimeout(hidePop, 160);
  });
  document.addEventListener("focusin", e => { const a = e.target.closest("a.term"); if (a) showPop(a); });
  document.addEventListener("click", e => {
    const a = e.target.closest("a.term");
    if (a && matchMedia("(hover: none)").matches && openFor !== a) { e.preventDefault(); showPop(a); return; }
    if (!a && pop && !pop.contains(e.target)) hidePop();
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape") hidePop(); });
  addEventListener("scroll", () => { if (openFor && !matchMedia("(hover: none)").matches) hidePop(); }, { passive: true });

  // phones: "In this entry" starts folded so the text comes first
  const margin = document.querySelector(".margin");
  if (margin && matchMedia("(max-width: 820px)").matches) margin.open = false;
})();
