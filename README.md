<h1 align="center">ComfyUI-Prompto</h1>

<p align="center"><b>Your Prompto prompt library inside ComfyUI, one click from the workflow.</b></p>

<p align="center">
  <a href="https://github.com/EY4O/ComfyUI-Prompto/blob/main/LICENSE"><img src="https://img.shields.io/github/license/EY4O/ComfyUI-Prompto?color=blue" alt="License"></a>
  <a href="https://github.com/EY4O/ComfyUI-Prompto/commits/main"><img src="https://img.shields.io/github/last-commit/EY4O/ComfyUI-Prompto?color=green&logo=github" alt="Last commit"></a>
  <a href="https://ko-fi.com/looneth"><img src="https://img.shields.io/badge/Ko--fi-Support-FF813F?logo=ko-fi&logoColor=white" alt="Support on Ko-fi"></a>
</p>

The ComfyUI half of **Prompto**, a Chrome extension for collecting and organizing Stable Diffusion prompts, image recipes and character tags. Prompto keeps your library in the browser so you can capture ideas even when ComfyUI isn't running. This extension brings that library into ComfyUI: a **Prompto** tab in the sidebar loads recipes straight into your workflow, and anything you make in ComfyUI can go back to Prompto's inbox. Open it from the **Prompto** icon in ComfyUI's sidebar.

<p align="center"><img src="docs/images/sidebar.png" width="360" alt="The Prompto sidebar in ComfyUI"><br><sub>The Prompto sidebar in ComfyUI. Screenshot uses sample data.</sub></p>

> **⚠ Needs the Prompto Chrome extension.** The library lives there; this extension shows and fills it. Prompto isn't published yet. Load it in Chrome from its folder with **chrome://extensions → Developer mode → Load unpacked**.

---

## ✨ Key Features

- 🎟️ **Prompto sidebar** — your recipes, snippets and cast, synced from Chrome and searchable inside ComfyUI.
- ⚡ **Load into workflow** — one click writes a recipe's prompt and negative into the open workflow, plus its seed, steps, CFG, sampler, scheduler, model, size and LoRAs where they match.
- ➕ **Add to the selected node** — append a snippet, a character's tags or an outfit to whichever text node you've selected.
- 🖱️ **Save to Prompto** — right-click any text node or image node to send its prompt or picture to the Prompto inbox.
- 📥 **Auto-capture** — an optional setting sends every image from a Save Image node to the inbox, with the prompt that made it.
- 🕒 **Waits for you** — captures queue on the ComfyUI server (up to 100) until Prompto collects them, so nothing is lost while Chrome is closed.
- 🔌 **A stable bridge** — Prompto talks to ComfyUI through this extension instead of ComfyUI's internals, so ComfyUI updates are less likely to break it.

---

## 📦 Installation

### Option 1: **Manual Installation** (Recommended)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/EY4O/ComfyUI-Prompto.git
```

Restart ComfyUI. There are no Python dependencies beyond ComfyUI itself.

### Option 2: **Copy the folder**

Download or copy the `ComfyUI-Prompto` folder into `ComfyUI/custom_nodes/` and restart ComfyUI.

<details>
<summary><b>Stability Matrix</b></summary>

Custom nodes go in the package's own folder, for example `C:/StabilityMatrix/Data/Packages/ComfyUI/custom_nodes/`. Restart the package from Stability Matrix afterwards (**Stop**, then **Launch**).
</details>

## 🚀 Getting Started

1. Install ComfyUI-Prompto and restart ComfyUI.
2. Open ComfyUI in Chrome and open the **Prompto** side panel next to it. The panel's header changes to **ComfyUI · linked** within a few seconds.
3. Click the **Prompto** icon in ComfyUI's sidebar. Your recipes, snippets and cast are there.
4. Press **Load into workflow** on a recipe. The prompt, negative and settings are written into the open workflow, ready to queue.
5. Right-click a Save Image node → **Save image to Prompto**. The image and its prompt arrive in Prompto's **Inbox**.
6. Optional: turn on **Settings → Prompto → Send every saved image to the Prompto inbox**.

---

## 📖 How It Works

<details>
<summary><b>🔌 The bridge</b></summary>

The frontend extension installs `window.PromptoBridge` in the ComfyUI page:

| Method | What it does |
|---|---|
| `info()` | Returns the bridge version, so Prompto knows it's installed. |
| `loras()` | Lists the installed LoRAs, for Prompto's LoRA autocomplete. |
| `queue()` | Presses Queue once, for Prompto's **Queue variants** (several wildcard rolls on one seed). |
| `apply(payload)` | Writes a recipe into the workflow, or text into the selected node. |
| `syncLibrary(snapshot)` | Saves the library snapshot that the sidebar shows. |
| `takeCaptures()` / `ackCaptures(ids)` | Hands queued captures to Prompto, then removes the ones it saved. |

Prompto calls these through the open ComfyUI tab. Without this extension it falls back to editing the graph directly, which works but relies on ComfyUI internals.
</details>

<details>
<summary><b>⚡ How a recipe is loaded</b></summary>

- The prompt node is found by following the sampler's **positive** and **negative** inputs back to the node holding the text, through ControlNet and guidance nodes. Flux-style workflows are found through their **Guider** node.
- Seed, steps, CFG, sampler and scheduler go to the first sampler, so a hires-fix pass keeps its own steps.
- Dropdown settings (sampler, scheduler, model) are only changed when the value is one of that dropdown's options. A model is matched by file name even if it sits in a subfolder.
- Size goes to the first node with both **width** and **height**.
- LoRAs fill the existing LoRA loader nodes in order, matched by file name, with the weight on both model and CLIP. Loaders the recipe doesn't use, or whose LoRA isn't installed, are bypassed. No nodes are added; you're told when more loaders are needed.
</details>

<details>
<summary><b>🔁 Sync and captures</b></summary>

- While a ComfyUI tab is open, Prompto pushes a snapshot of your library every few seconds after a change. Prompts are rendered by Prompto first, so the sidebar shows exactly what Prompto would copy.
- Captures are resolved in ComfyUI right away: the image is loaded, its prompt is read from the PNG, and a thumbnail is made. That way temporary previews survive a restart.
- Prompto collects captures on its next check, saves them to its inbox, and only then asks ComfyUI to delete them.
</details>

<details>
<summary><b>💾 Where data lives</b></summary>

- `ComfyUI/user/prompto/library.json` holds the last synced snapshot, read-only on the ComfyUI side.
- `ComfyUI/user/prompto/captures.json` holds captures waiting for Prompto, capped at 100.
- Your real library stays in the Chrome extension. Deleting these files loses nothing that Prompto has already collected.
</details>

<details>
<summary><b>🛡️ Safety</b></summary>

- It never queues a prompt by itself. Loading a recipe only fills in the workflow; you press **Queue**.
- It makes no network requests outside your ComfyUI server.
- Its routes (`/prompto/...`) only read and write the two files above, and reject anything over 25 MB for the library or 4 MB per capture.
</details>

---

## 🧪 Development

Tests, local installs and releasing are described in **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)**.

## 🗺️ Roadmap

- Prompto nodes, such as a character node that picks an outfit when you queue.

## 🤝 Contributing

Issues and pull requests are welcome. Please run the test suite before opening a PR.

## 🙏 Credits

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI): the extension and sidebar APIs this builds on

## ☕ Support

If Prompto saves you from retyping the same prompts, you can support its development:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/looneth)

## 📄 License

[MIT](LICENSE)
