// The Prompto tab in ComfyUI's sidebar: a read-only view of the library the
// Chrome extension last synced, with one-click load and insert.
import { apply, getLibrary, onLibrary } from "./bridge.js";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const pad = (n) => String(n).padStart(3, "0");

function ago(ts) {
  if (!ts) return "never";
  const m = Math.round((Date.now() - ts) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return m + "m ago";
  const h = Math.round(m / 60);
  return h < 24 ? h + "h ago" : Math.round(h / 24) + "d ago";
}

export function renderSidebar(el, notify) {
  let lib = null, q = "", section = "recipes";
  el.classList.add("prompto-side");

  const matches = (...f) => !q || f.join(" ").toLowerCase().includes(q.toLowerCase());

  function recipes() {
    const list = (lib.recipes || []).filter((r) => matches(r.title, r.profile, r.positive));
    if (!list.length) return empty("No recipes match.");
    return list.map((r) => `<article class="pm-ticket">
      ${r.thumb ? `<img class="pm-thumb" src="${esc(r.thumb)}" alt="">` : ""}
      <div class="pm-head"><span class="pm-tag">${esc(r.profile)}</span><span class="pm-num">No. <b>${pad(r.no)}</b>${r.fav ? " ✦" : ""}</span></div>
      <h3 class="pm-title">${esc(r.title)}</h3>
      <p class="pm-text">${esc(r.positive)}</p>
      <div class="pm-tear"></div>
      <div class="pm-actions">
        <button class="pm-btn pm-primary" data-act="load" data-id="${esc(r.id)}">Load into workflow</button>
        <button class="pm-btn" data-act="node" data-id="${esc(r.id)}">Selected node</button>
      </div>
    </article>`).join("");
  }

  function snippets() {
    const list = (lib.snippets || []).filter((s) => matches(s.name, s.cat, (s.tags || []).join(" "), s.prose));
    if (!list.length) return empty("No snippets match.");
    return list.map((s) => `<div class="pm-row">
      <div class="pm-row-head"><span class="pm-name">${esc(s.name)}</span><span class="pm-cat">${esc(s.cat)}</span></div>
      ${s.tags?.length ? `<div class="pm-chips">${s.tags.map((t) => `<span class="pm-chip">${esc(t)}</span>`).join("")}</div>` : ""}
      ${s.prose ? `<p class="pm-prose">${esc(s.prose)}</p>` : ""}
      <div class="pm-actions">
        ${s.tags?.length ? `<button class="pm-btn" data-act="snip" data-id="${esc(s.id)}" data-k="tags">Add tags to node</button>` : ""}
        ${s.prose ? `<button class="pm-btn" data-act="snip" data-id="${esc(s.id)}" data-k="prose">Add prose to node</button>` : ""}
      </div>
    </div>`).join("");
  }

  function cast() {
    const list = (lib.cast || []).filter((c) => matches(c.name, c.series, (c.tags || []).join(" ")));
    if (!list.length) return empty("No cast members match.");
    return list.map((c) => `<div class="pm-row">
      <div class="pm-row-head"><span class="pm-name">${esc(c.name)}</span><span class="pm-cat">${esc(c.series)}</span></div>
      <div class="pm-chips">${(c.tags || []).map((t) => `<span class="pm-chip">${esc(t)}</span>`).join("")}</div>
      <div class="pm-actions">
        <button class="pm-btn" data-act="cast" data-id="${esc(c.id)}">Add tags to node</button>
        ${(c.outfits || []).map((o, i) => `<button class="pm-btn" data-act="outfit" data-id="${esc(c.id)}" data-o="${i}">+ ${esc(o.name)}</button>`).join("")}
      </div>
    </div>`).join("");
  }

  const empty = (msg) => `<p class="pm-empty">${esc(msg)}</p>`;

  function draw() {
    if (!lib || !lib.syncedAt) {
      el.innerHTML = `<div class="pm-wrap">
        <div class="pm-brand">Prompt<span class="pm-o"></span></div>
        <div class="pm-empty pm-big"><b>Nothing synced yet</b>
          <p>Open the Prompto side panel in Chrome while this tab is open. Your recipes, snippets and cast show up here a few seconds later.</p></div>
      </div>`;
      return;
    }
    const counts = { recipes: lib.recipes?.length || 0, snippets: lib.snippets?.length || 0, cast: lib.cast?.length || 0 };
    el.innerHTML = `<div class="pm-wrap">
      <div class="pm-top"><div class="pm-brand">Prompt<span class="pm-o"></span></div>
        <button class="pm-link" data-act="refresh" title="Reload the synced library">Synced ${esc(ago(lib.syncedAt))}</button></div>
      <div class="pm-tabs" role="tablist">${["recipes", "snippets", "cast"].map((k) =>
        `<button role="tab" data-act="section" data-k="${k}" aria-selected="${section === k}">${k} <small>${counts[k]}</small></button>`).join("")}</div>
      <input class="pm-search" type="search" placeholder="Search" value="${esc(q)}" aria-label="Search the library">
      <div class="pm-list">${section === "recipes" ? recipes() : section === "snippets" ? snippets() : cast()}</div>
    </div>`;
  }

  function send(payload, okLabel) {
    const res = apply(payload);
    notify(res.ok ? `${okLabel}: ${res.applied.join(", ")}` : res.error, res.ok ? "success" : "warn");
  }

  el.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    const find = (key) => (lib[key] || []).find((x) => x.id === b.dataset.id);
    switch (b.dataset.act) {
      case "refresh": lib = await getLibrary(); draw(); break;
      case "section": section = b.dataset.k; draw(); break;
      case "load": { const r = find("recipes"); send({ mode: "recipe", positive: r.positive, negative: r.negative, settings: r.settings }, "Loaded"); break; }
      case "node": { const r = find("recipes"); send({ mode: "selected", text: r.positive, append: false }, "Sent"); break; }
      case "snip": { const s = find("snippets"); send({ mode: "selected", text: b.dataset.k === "tags" ? s.tags.join(", ") : s.prose, append: true }, "Added"); break; }
      case "cast": { const c = find("cast"); send({ mode: "selected", text: c.tags.join(", "), append: true }, "Added"); break; }
      case "outfit": { const o = find("cast").outfits[b.dataset.o]; send({ mode: "selected", text: o.tags.join(", "), append: true }, "Added"); break; }
    }
  });
  el.addEventListener("input", (e) => {
    if (!e.target.classList.contains("pm-search")) return;
    q = e.target.value;
    const caret = e.target.selectionStart;
    draw();
    const input = el.querySelector(".pm-search");
    input.focus();
    input.setSelectionRange(caret, caret);
  });

  const off = onLibrary(async () => { lib = await getLibrary(); draw(); });
  getLibrary().then((l) => { lib = l; draw(); });
  draw();
  return off;
}

