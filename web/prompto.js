// ComfyUI-Prompto frontend: installs the bridge, adds a sidebar tab, node menu
// items, and optional auto-capture of finished images.
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { install, captureImage, captureText, version } from "./bridge.js";
import { renderSidebar } from "./sidebar.js";

const AUTO_CAPTURE = "Prompto.AutoCapture";

function setting(id) {
  return app.extensionManager?.setting?.get?.(id) ?? app.ui?.settings?.getSettingValue?.(id);
}

function notify(detail, severity = "success") {
  if (app.extensionManager?.toast?.add) {
    app.extensionManager.toast.add({ severity, summary: "Prompto", detail, life: 3000 });
  } else {
    console.info("[Prompto]", detail);
  }
}

async function run(task, okMessage) {
  try { await task(); notify(okMessage); }
  catch (e) { notify(e.message || "Something went wrong", "error"); }
}

const textOf = (node) =>
  (node.widgets || []).find((w) => ["text", "prompt", "text_g", "string"].includes(w.name) && typeof w.value === "string");

app.registerExtension({
  name: "Prompto.Bridge",

  settings: [
    {
      id: AUTO_CAPTURE,
      name: "Send every saved image to the Prompto inbox",
      tooltip: "Images from Save Image nodes are queued with their prompt. The Chrome extension collects them when this tab is open.",
      type: "boolean",
      defaultValue: false,
      category: ["Prompto", "Capture", "Auto capture"]
    }
  ],

  async setup() {
    install();

    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = new URL("./prompto.css", import.meta.url).href;
    document.head.append(css);

    app.extensionManager?.registerSidebarTab?.({
      id: "prompto",
      icon: "pi pi-ticket",
      title: "Prompto",
      tooltip: "Prompto library",
      type: "custom",
      render: (el) => renderSidebar(el, notify)
    });

    // Only Save Image outputs ("output" type); previews are skipped.
    api.addEventListener("executed", ({ detail }) => {
      if (!setting(AUTO_CAPTURE)) return;
      const images = (detail?.output?.images || []).filter((i) => i.type === "output");
      for (const img of images) captureImage(img, "ComfyUI · auto").catch((e) => console.warn("[Prompto] capture failed", e));
    });

    version.then((v) => console.info(`[Prompto] bridge ${v} ready`));
  },

  async beforeRegisterNodeDef(nodeType) {
    const original = nodeType.prototype.getExtraMenuOptions;
    nodeType.prototype.getExtraMenuOptions = function (canvas, options) {
      const result = original?.apply(this, arguments);
      const items = [];
      const text = textOf(this);
      if (text && text.value.trim()) {
        items.push({
          content: "Save text to Prompto",
          callback: () => run(() => captureText(text.value, "ComfyUI · " + (this.title || this.type)), "Text sent to the Prompto inbox")
        });
      }
      const imgs = this.images || [];
      if (imgs.length) {
        items.push({
          content: imgs.length > 1 ? `Save ${imgs.length} images to Prompto` : "Save image to Prompto",
          callback: () => run(() => Promise.all(imgs.map((img) => captureImage(img, "ComfyUI · " + (this.title || this.type)))), "Sent to the Prompto inbox")
        });
      }
      if (items.length) options.push(null, ...items);
      return result;
    };
  }
});
