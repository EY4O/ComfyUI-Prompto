// Missing models after a recipe is applied. When Model Librarian is installed
// (window.ModelLibrarian.openRecipe), a notice offers to download what's missing:
// the recipe is handed over in the shared recipe/1 format, keeping the hashes and
// Civitai version ids Prompto captured, so the exact files can be found.
// No ComfyUI imports here (ComfyUI loads every .js in web/): callers pass `api`.

const stem = (p) => String(p || "").split(/[\\/]/).pop().replace(/\.(safetensors|ckpt|pt|pth|bin|gguf|sft)$/i, "");
const key = (p) => stem(p).toLowerCase();
const num = (v) => (v == null || v === "" || !Number.isFinite(Number(v)) ? null : Number(v));

// Prompto's apply payload ({ positive, negative, settings, title? }) → recipe/1.
export function toRecipe1(payload) {
  const s = payload.settings || {};
  const mr = s.modelRef || {};
  const ref = (name, file, hash, versionId) => ({
    name: name || stem(file) || null, file: file || null, hash: hash ? String(hash).toLowerCase() : null,
    civitai_version_id: num(versionId), civitai_model_id: null
  });
  return {
    schema: "recipe/1",
    title: payload.title || "",
    format: "prompto",
    prompt: { positive: payload.positive || "", negative: payload.negative || "" },
    settings: {
      sampler: s.sampler || null, scheduler: s.scheduler || null, steps: num(s.steps), cfg: num(s.cfg), seed: num(s.seed),
      width: num(s.width), height: num(s.height), clip_skip: num(s.clipSkip)
    },
    model: s.model || mr.hash || mr.versionId ? ref(stem(s.model), s.model || null, mr.hash, mr.versionId) : null,
    loras: (s.loras || []).filter((l) => l && l.name).map((l) => ({
      ...ref(l.label || stem(l.name), l.name, l.hash, l.versionId),
      ...(l.label ? { display_name: l.label } : {}),
      weight: num(l.w) ?? 1, clip_weight: num(l.clip)
    })),
    base_model: s.baseModel || null
  };
}

async function options(api, node, input) {
  try {
    const res = await api.fetchApi(`/object_info/${encodeURIComponent(node)}`);
    if (!res.ok) return [];
    const spec = (await res.json())?.[node]?.input?.required?.[input];
    if (!spec) return [];
    return Array.isArray(spec[0]) ? spec[0] : spec[1]?.options || [];
  } catch { return []; }
}

// → { loras: [names], model: name | null } that ComfyUI doesn't list.
export async function findMissing(api, settings) {
  const s = settings || {};
  const out = { loras: [], model: null };
  const loras = (s.loras || []).filter((l) => l && l.name);
  if (loras.length) {
    const have = new Set((await options(api, "LoraLoader", "lora_name")).map(key));
    out.loras = loras.filter((l) => !have.has(key(l.name))).map((l) => l.name);
  }
  if (s.model) {
    const [ck, unet] = await Promise.all([options(api, "CheckpointLoaderSimple", "ckpt_name"), options(api, "UNETLoader", "unet_name")]);
    if (![...ck, ...unet].some((o) => key(o) === key(s.model))) out.model = s.model;
  }
  return out;
}

let notice = null;

export function closeNotice() {
  notice?.remove();
  notice = null;
}

// Shows "N models aren't installed — Get them with Model Librarian" in ComfyUI.
export async function offerDownloads(api, payload, doc = globalThis.document) {
  const ml = globalThis.window?.ModelLibrarian;
  if (!ml || typeof ml.openRecipe !== "function" || !doc) return null;
  const missing = await findMissing(api, payload.settings);
  const names = [...(missing.model ? [missing.model] : []), ...missing.loras].map(stem);
  closeNotice();
  if (!names.length) return missing;
  const el = doc.createElement("div");
  el.className = "pm-notice";
  el.setAttribute("role", "status");
  const text = doc.createElement("span");
  text.textContent = `${names.length === 1 ? `${names[0]} isn't` : `${names.length} models aren't`} installed, so ${names.length === 1 ? "it was" : "they were"} skipped.`;
  text.title = names.join("\n");
  const go = doc.createElement("button");
  go.className = "pm-notice-go";
  go.textContent = "Get them with Model Librarian";
  go.addEventListener("click", () => {
    closeNotice();
    Promise.resolve(ml.openRecipe(toRecipe1(payload), { thumb: payload.image || null })).catch((e) => console.warn("[Prompto] Model Librarian:", e));
  });
  const x = doc.createElement("button");
  x.className = "pm-notice-x";
  x.textContent = "×";
  x.title = "Dismiss";
  x.addEventListener("click", closeNotice);
  el.append(text, go, x);
  doc.body.append(el);
  notice = el;
  return missing;
}
