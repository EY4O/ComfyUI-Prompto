// window.PromptoBridge: the small, versioned surface the Prompto Chrome
// extension calls through the open ComfyUI tab. Everything that touches the
// graph or the server lives here so the Chrome side never depends on
// ComfyUI internals.
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { offerDownloads } from "./missing.js";

// The version is written only in pyproject.toml; the server reads it.
export const version = api.fetchApi("/prompto/status")
  .then((r) => (r.ok ? r.json() : {}))
  .then((s) => s.version || "unknown")
  .catch(() => "unknown");

// ---------- Graph ----------
// Any text box counts: CLIP Text Encode's "text", SDXL/Flux encoders' split
// boxes, string primitives, wildcard nodes, and any other multiline widget.
const PROMPT_NAMES = ["text", "prompt", "text_g", "text_l", "clip_l", "t5xxl"];
const TEXT_NAMES = [...PROMPT_NAMES, "positive", "wildcard_text", "string", "value", "text_positive"];
const isTextWidget = (w) => typeof w.value === "string" && (TEXT_NAMES.includes(w.name) || w.type === "customtext" || !!(w.options && w.options.multiline));
const textWidgets = (n) => (n.widgets || []).filter(isTextWidget);
const textWidget = (n) => textWidgets(n)[0];

// Writes a prompt into every prompt box of an encoder (SDXL has text_g and
// text_l, Flux has clip_l and t5xxl), or its first text box otherwise.
function setPrompt(node, v) {
  const boxes = textWidgets(node).filter((w) => PROMPT_NAMES.includes(w.name));
  for (const w of boxes.length ? boxes : [textWidget(node)]) setWidgetValue(w, v);
}

// Adds text at the cursor, with commas where the neighbouring text needs them.
export function insertText(old, text, start = old.length, end = start) {
  const before = old.slice(0, start), after = old.slice(end);
  const left = before.trim() && !/[,(\n]\s*$/.test(before) ? before.replace(/\s*$/, "") + ", " : before;
  const right = after.trim() && !/^\s*[,)\n]/.test(after) ? ", " + after.replace(/^\s*/, "") : after;
  return { value: left + text + right, caret: (left + text).length };
}

// The prompt box you last clicked into. Clicking the canvas clears it, so
// selecting nodes afterwards takes over again.
let lastBox = null;
// Clicking or typing in a box counts too, in case the focus event doesn't arrive.
const remember = (e) => { if (e.target && e.target.tagName === "TEXTAREA") lastBox = e.target; };
for (const type of ["focusin", "input", "keyup"]) document.addEventListener(type, remember, true);
document.addEventListener("pointerdown", (e) => {
  if (e.target && e.target.tagName === "TEXTAREA") lastBox = e.target;
  else if (e.target && e.target.tagName === "CANVAS") lastBox = null;
}, true);

function widgetFor(el) {
  for (const n of app.graph?._nodes || app.graph?.nodes || []) {
    for (const w of n.widgets || []) if (w.element === el || w.inputEl === el || (w.element && w.element.contains && w.element.contains(el))) return { node: n, widget: w };
  }
  return null;
}

function setWidgetValue(w, v) {
  if (!w) return;
  w.value = v;
  if (w.callback) w.callback(v);
}

function dirty() {
  app.graph.setDirtyCanvas?.(true, true);
  app.canvas?.setDirty?.(true, true);
}

// Walks conditioning links back from a sampler input to the node holding the text.
function upstreamText(node, inputName, depth = 0) {
  if (!node || depth > 8 || !node.inputs) return null;
  const slot = node.inputs.findIndex((i) => i.name === inputName);
  if (slot < 0) return null;
  const src = node.getInputNode?.(slot);
  if (!src) return null;
  if (textWidget(src)) return src;
  for (const k of ["conditioning", "conditioning_1", "positive", "text"]) {
    const found = upstreamText(src, k, depth + 1);
    if (found) return found;
  }
  return null;
}

export function selectedTextNodes() {
  return Object.values(app.canvas?.selected_nodes || {}).filter(textWidget);
}

// Where "add to node" goes: the prompt box you were typing in, else the selected nodes.
function targets() {
  const el = lastBox && lastBox.isConnected ? lastBox : document.activeElement && document.activeElement.tagName === "TEXTAREA" ? document.activeElement : null;
  const hit = el && widgetFor(el);
  if (hit && isTextWidget(hit.widget)) return [{ ...hit, el }];
  return selectedTextNodes().map((node) => ({ node, widget: textWidget(node), el: null }));
}

export function apply(payload) {
  const nodes = app.graph?._nodes || app.graph?.nodes || [];

  if (payload.mode === "selected") {
    const list = targets();
    if (!list.length) return { ok: false, error: "Click into a prompt box, or select a text node, in ComfyUI first." };
    for (const { widget, el } of list) {
      if (!payload.append) { setWidgetValue(widget, payload.text); continue; }
      // In the box you were typing in, the text goes at the cursor; otherwise at the end.
      const atCursor = el && typeof el.selectionStart === "number";
      const { value, caret } = insertText(widget.value, payload.text, atCursor ? el.selectionStart : widget.value.length, atCursor ? el.selectionEnd : widget.value.length);
      setWidgetValue(widget, value);
      if (el) { el.value = value; try { el.setSelectionRange(caret, caret); } catch {} }
    }
    dirty();
    const where = list[0].el ? `${list[0].node.title || list[0].node.type}` : list.length === 1 ? "1 node" : list.length + " nodes";
    return { ok: true, applied: [where] };
  }

  let pos = null, neg = null;
  for (const n of nodes) {
    pos = pos || upstreamText(n, "positive");
    neg = neg || upstreamText(n, "negative");
  }
  if (!pos) for (const n of nodes) if (/Guider/.test(n.type || "")) pos = pos || upstreamText(n, "conditioning");
  if (!pos) return { ok: false, error: "Couldn't find the prompt node in this workflow." };

  const applied = ["prompt"], warnings = [];
  setPrompt(pos, payload.positive);
  if (neg && neg !== pos && payload.negative != null) {
    setPrompt(neg, payload.negative);
    applied.push("negative");
  }

  // First match wins, samplers first, so a hires-fix pass keeps its own steps.
  // Combo widgets only take values from their own option list.
  const hasCond = (n) => (n.inputs || []).some((i) => i.name === "positive" || i.name === "noise");
  const ordered = [...nodes].sort((a, b) => hasCond(b) - hasCond(a));
  const setFirst = (names, v, label) => {
    if (v == null || v === "") return;
    for (const n of ordered) {
      const w = (n.widgets || []).find((x) => names.includes(x.name));
      if (!w) continue;
      const opts = Array.isArray(w.options?.values) ? w.options.values : null;
      const base = (s) => String(s).split(/[\\/]/).pop();
      // Civitai names models without folder or extension, so the file stem matches too
      const stem = (s) => base(s).replace(/\.(safetensors|ckpt|pt|pth|bin|gguf|sft)$/i, "").toLowerCase();
      const val = opts ? opts.find((o) => o === v) ?? opts.find((o) => base(o) === base(v)) ?? opts.find((o) => stem(o) === stem(v)) : v;
      if (val == null) continue;
      setWidgetValue(w, val);
      applied.push(label);
      return;
    }
  };
  const s = payload.settings || {};
  setFirst(["seed", "noise_seed"], s.seed, "seed");
  setFirst(["steps"], s.steps, "steps");
  setFirst(["cfg"], s.cfg, "CFG");
  setFirst(["sampler_name"], s.sampler, "sampler");
  setFirst(["scheduler"], s.scheduler, "scheduler");
  setFirst(["ckpt_name", "unet_name"], s.model, "model");
  if (s.width && s.height) {
    const latent = nodes.find((n) => ["width", "height"].every((k) => (n.widgets || []).some((w) => w.name === k)));
    if (latent) {
      for (const k of ["width", "height"]) setWidgetValue(latent.widgets.find((w) => w.name === k), Number(s[k]));
      applied.push("size");
    }
  }
  applyLoras(nodes, s.loras, applied, warnings);
  dirty();
  // Missing models: Model Librarian, when installed, can download them (shown as a notice in ComfyUI).
  offerDownloads(api, payload).catch((e) => console.warn("[Prompto] missing-model check:", e));
  return { ok: true, applied, warnings };
}

// LoRAs fill the workflow's existing LoRA loader nodes in order; no nodes are
// added. Loaders the recipe doesn't use, or whose LoRA isn't installed, are bypassed.
const loraBase = (v) => String(v).split(/[\\/]/).pop().replace(/\.(safetensors|ckpt|pt|bin)$/i, "").toLowerCase();

function applyLoras(nodes, list, applied, warnings) {
  const loras = (list || []).filter((l) => l && l.name);
  if (!loras.length) return;
  const loaders = nodes.filter((n) => /LoraLoader/i.test(n.type || "") && (n.widgets || []).some((w) => w.name === "lora_name")).sort((a, b) => a.id - b.id);
  let set = 0;
  loras.forEach((l, i) => {
    const n = loaders[i];
    if (!n) return;
    const w = n.widgets.find((x) => x.name === "lora_name");
    const opts = Array.isArray(w.options?.values) ? w.options.values : null;
    const val = opts ? opts.find((o) => loraBase(o) === loraBase(l.name)) : l.name;
    if (val == null) { n.mode = 4; warnings.push(`${loraBase(l.name)} isn't installed, so its loader is bypassed`); return; }
    setWidgetValue(w, val);
    for (const k of ["strength_model", "strength_clip"]) {
      const sw = n.widgets.find((x) => x.name === k);
      if (sw) setWidgetValue(sw, Number(l.w));
    }
    if (n.mode === 4) n.mode = 0;
    set++;
  });
  const short = loras.length - loaders.length;
  if (short > 0) warnings.push(`${short} more LoRA loader node${short > 1 ? "s" : ""} needed`);
  const spare = loaders.slice(loras.length).filter((n) => n.mode !== 4);
  for (const n of spare) n.mode = 4;
  if (spare.length) warnings.push(`bypassed ${spare.length} unused LoRA loader${spare.length > 1 ? "s" : ""}`);
  if (set) applied.push(set === 1 ? "1 LoRA" : set + " LoRAs");
}

// Installed LoRAs, from LoraLoader's lora_name options (both old and new formats).
export async function listLoras() {
  const res = await api.fetchApi("/object_info/LoraLoader");
  if (!res.ok) return [];
  const spec = (await res.json())?.LoraLoader?.input?.required?.lora_name;
  if (!spec) return [];
  return Array.isArray(spec[0]) ? spec[0] : spec[1]?.options || [];
}

// ---------- Images ----------
const viewRoute = (img) =>
  `/view?filename=${encodeURIComponent(img.filename)}&subfolder=${encodeURIComponent(img.subfolder || "")}&type=${encodeURIComponent(img.type || "output")}`;

async function inflate(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

// ComfyUI writes the API graph into the PNG's "prompt" text chunk.
async function readPromptChunk(buffer) {
  const u8 = new Uint8Array(buffer);
  const view = new DataView(buffer);
  if (u8[0] !== 137 || u8[1] !== 80) return null;
  let p = 8;
  while (p + 8 <= u8.length) {
    const len = view.getUint32(p);
    const type = String.fromCharCode(...u8.subarray(p + 4, p + 8));
    const data = u8.subarray(p + 8, p + 8 + len);
    if (type === "tEXt" || type === "iTXt") {
      const z = data.indexOf(0);
      const key = new TextDecoder("latin1").decode(data.subarray(0, z));
      if (key === "prompt") {
        let body = data.subarray(z + 1);
        if (type === "iTXt") {
          const compressed = data[z + 1] === 1;
          let q = data.indexOf(0, z + 3) + 1;
          q = data.indexOf(0, q) + 1;
          body = compressed ? await inflate(data.subarray(q)) : data.subarray(q);
        }
        try { return JSON.parse(new TextDecoder().decode(body)); } catch { return null; }
      }
    }
    if (type === "IEND") break;
    p += 12 + len;
  }
  return null;
}

async function thumbnail(blob, max = 480) {
  const bmp = await createImageBitmap(blob);
  const k = Math.min(1, max / bmp.width);
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * k);
  c.height = Math.round(bmp.height * k);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", 0.82);
}

// ---------- Captures ----------
async function post(route, body) {
  const res = await api.fetchApi(route, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error((await res.text()) || "HTTP " + res.status);
  return res.json();
}

// Resolves the image right away (temp previews vanish on restart), then queues it.
export async function captureImage(img, source = "ComfyUI") {
  const res = await api.fetchApi(viewRoute(img));
  if (!res.ok) throw new Error("Couldn't load " + img.filename);
  const blob = await res.blob();
  const graph = blob.type === "image/png" ? await readPromptChunk(await blob.arrayBuffer()) : null;
  return post("/prompto/captures", { kind: "generation", source, filename: img.filename, graph, thumb: await thumbnail(blob) });
}

export function captureText(text, source = "ComfyUI") {
  return post("/prompto/captures", { kind: "text", text, source });
}

export async function getLibrary() {
  const res = await api.fetchApi("/prompto/library");
  return res.ok ? res.json() : {};
}

// ---------- Public surface ----------
const listeners = new Set();
export const onLibrary = (fn) => (listeners.add(fn), () => listeners.delete(fn));

export function install() {
  window.PromptoBridge = {
    info: async () => ({ version: await version }),
    loras: listLoras,
    // Presses Queue once, for Prompto's "Queue variants".
    async queue() {
      await app.queuePrompt(0, 1);
      return { ok: true };
    },
    apply,
    async syncLibrary(snapshot) {
      const out = await post("/prompto/library", snapshot);
      listeners.forEach((fn) => fn());
      return out;
    },
    async takeCaptures() {
      const res = await api.fetchApi("/prompto/captures");
      return res.ok ? res.json() : [];
    },
    ackCaptures: (ids) => post("/prompto/captures/ack", { ids })
  };
}
