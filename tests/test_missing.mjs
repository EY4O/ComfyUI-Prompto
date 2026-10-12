// node --test tests/test_missing.mjs   (web/missing.js has no ComfyUI imports)
import { test } from "node:test";
import assert from "node:assert/strict";
import { toRecipe1, findMissing, offerDownloads } from "../web/missing.js";

const OPTIONS = {
  LoraLoader: { lora_name: [["Illustrious\\watercolor_v3.safetensors", "other.safetensors"]] },
  CheckpointLoaderSimple: { ckpt_name: [["illustriousXL_v20.safetensors"]] },
  UNETLoader: { unet_name: ["COMBO", { options: ["flux1-dev.safetensors"] }] }, // newer combo format
};
const api = {
  calls: [],
  async fetchApi(path) {
    this.calls.push(path);
    const node = decodeURIComponent(path.split("/").pop());
    return new Response(JSON.stringify({ [node]: { input: { required: OPTIONS[node] || {} } } }));
  },
};

const payload = {
  title: "Lighthouse", positive: "a lighthouse", negative: "blurry", image: "data:image/jpeg;base64,AAAA",
  settings: {
    model: "illustriousXL_v20.safetensors", modelRef: { hash: "1A2B3C4D5E", versionId: 999 }, baseModel: "Illustrious",
    sampler: "euler_ancestral", steps: 28, cfg: 5, seed: 7, width: 832, height: 1216, clipSkip: 2,
    loras: [
      { name: "watercolor_v3", w: 0.8, hash: "aaaa1111bb", versionId: 111, label: "Watercolor Wash" },
      { name: "soft_pastel", w: 0.55, clip: 0.4 },
    ],
  },
};

test("toRecipe1 keeps the model references Prompto captured", () => {
  const r = toRecipe1(payload);
  assert.equal(r.schema, "recipe/1");
  assert.deepEqual(r.prompt, { positive: "a lighthouse", negative: "blurry" });
  assert.deepEqual(r.model, { name: "illustriousXL_v20", file: "illustriousXL_v20.safetensors", hash: "1a2b3c4d5e", civitai_version_id: 999, civitai_model_id: null });
  assert.deepEqual(r.loras[0], { name: "Watercolor Wash", file: "watercolor_v3", hash: "aaaa1111bb", civitai_version_id: 111, civitai_model_id: null, display_name: "Watercolor Wash", weight: 0.8, clip_weight: null });
  assert.deepEqual([r.loras[1].name, r.loras[1].weight, r.loras[1].clip_weight], ["soft_pastel", 0.55, 0.4]);
  assert.deepEqual([r.settings.clip_skip, r.base_model], [2, "Illustrious"]);
  assert.doesNotThrow(() => JSON.stringify(r));
});

test("findMissing compares by file name, both combo formats", async () => {
  assert.deepEqual(await findMissing(api, payload.settings), { loras: ["soft_pastel"], model: null });
  assert.deepEqual(await findMissing(api, { model: "flux1-dev", loras: [] }), { loras: [], model: null });
  assert.deepEqual(await findMissing(api, { model: "gone.safetensors" }), { loras: [], model: "gone.safetensors" });
});

// a few DOM methods are enough for the notice
function fakeDoc() {
  const make = (tag) => {
    const el = { tag, children: [], listeners: {}, attrs: {}, className: "", textContent: "", title: "",
      append(...k) { this.children.push(...k); }, remove() { this.removed = true; },
      setAttribute(k, v) { this.attrs[k] = v; }, addEventListener(t, f) { this.listeners[t] = f; } };
    return el;
  };
  return { body: make("body"), createElement: make };
}

test("the notice appears only with Model Librarian, and hands the recipe over", async () => {
  const doc = fakeDoc();
  delete globalThis.window;
  assert.equal(await offerDownloads(api, payload, doc), null, "no Model Librarian → nothing");
  assert.equal(doc.body.children.length, 0);

  const opened = [];
  globalThis.window = { ModelLibrarian: { openRecipe: async (r, o) => opened.push([r, o]) } };
  await offerDownloads(api, payload, doc);
  const n = doc.body.children[0];
  assert.equal(n.className, "pm-notice");
  assert.equal(n.children[0].textContent, "soft_pastel isn't installed, so it was skipped.");
  n.children[1].listeners.click();
  assert.equal(n.removed, true);
  assert.equal(opened.length, 1);
  assert.equal(opened[0][0].loras.length, 2);
  assert.equal(opened[0][1].thumb, payload.image);

  const doc2 = fakeDoc();
  await offerDownloads(api, { settings: { model: "illustriousXL_v20.safetensors", loras: [{ name: "other", w: 1 }] } }, doc2);
  assert.equal(doc2.body.children.length, 0, "everything installed → no notice");
  delete globalThis.window;
});
