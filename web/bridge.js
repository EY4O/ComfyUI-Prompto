// window.PromptoBridge: the small, versioned surface the Prompto Chrome
// extension calls through the open ComfyUI tab. Everything that touches the
// graph or the server lives here so the Chrome side never depends on
// ComfyUI internals.
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

export const VERSION = "0.1.0";

// ---------- Graph ----------
const textWidget = (n) =>
  (n.widgets || []).find((w) => ["text", "prompt", "text_g", "string"].includes(w.name) && typeof w.value === "string");

function setWidgetValue(w, v) {
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

export function apply(payload) {
  const nodes = app.graph?._nodes || app.graph?.nodes || [];

  if (payload.mode === "selected") {
    const sel = selectedTextNodes();
    if (!sel.length) return { ok: false, error: "Select a text node in ComfyUI first." };
    for (const n of sel) {
      const w = textWidget(n);
      setWidgetValue(w, payload.append && w.value.trim() ? w.value.replace(/[,\s]*$/, "") + ", " + payload.text : payload.text);
    }
    dirty();
    return { ok: true, applied: [sel.length === 1 ? "1 node" : sel.length + " nodes"] };
  }

  let pos = null, neg = null;
  for (const n of nodes) {
    pos = pos || upstreamText(n, "positive");
    neg = neg || upstreamText(n, "negative");
  }
  if (!pos) for (const n of nodes) if (/Guider/.test(n.type || "")) pos = pos || upstreamText(n, "conditioning");
  if (!pos) return { ok: false, error: "Couldn't find the prompt node in this workflow." };

  const applied = ["prompt"];
  setWidgetValue(textWidget(pos), payload.positive);
  if (neg && neg !== pos && payload.negative != null) {
    setWidgetValue(textWidget(neg), payload.negative);
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
      const val = opts ? opts.find((o) => o === v) ?? opts.find((o) => base(o) === base(v)) : v;
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
  dirty();
  return { ok: true, applied };
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
    version: VERSION,
    info: () => ({ version: VERSION }),
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
