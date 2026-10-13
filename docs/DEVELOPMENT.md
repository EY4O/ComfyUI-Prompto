# Development

The repository root is the custom node package: ComfyUI imports `__init__.py` and serves `web/`.

```
__init__.py        registers the routes and the web directory (no nodes yet)
prompto_routes.py  /prompto HTTP routes, on ComfyUI's PromptServer
prompto_store.py   JSON storage for the library snapshot and capture queue (no ComfyUI imports)
prompto_nodes.py   the Prompto Recipe, Character, Snippet and Wildcards nodes
prompto_logic.py   text logic behind the nodes: labels, wildcards, outfits (no ComfyUI imports)
web/prompto.js     frontend extension: bridge install, sidebar tab, node menus, auto-capture
web/bridge.js      window.PromptoBridge, graph editing, image capture
web/missing.js     missing models after a recipe loads; hands the recipe to Model Librarian (recipe/1)
web/sidebar.js     the Prompto sidebar tab
web/prompto.css    sidebar styles (prefixed pm-)
tests/             pytest suites
docs/              this file, docs/images/icon.png (drawn by tools/make-icons.py in the Prompto repo)
```

ComfyUI imports every `.js` file in `web/`, so helper modules only export functions. `prompto.js` is the only one that registers anything.

## Run it locally

Link the checkout into ComfyUI so edits show up without copying:

```powershell
New-Item -ItemType Junction -Path "C:/StabilityMatrix/Data/Packages/ComfyUI/custom_nodes/ComfyUI-Prompto" -Target "C:/path/to/ComfyUI-Prompto"
```

Restart ComfyUI after changing Python files. For JS or CSS changes, reload the browser tab.

The Chrome extension side lives in the Prompto repository. It finds the bridge through `chrome.scripting.executeScript` on the ComfyUI tab.

## Tests

Requires Python 3.10+ and pytest. ComfyUI isn't needed.

```
python -m pytest tests
```

| Suite | Covers |
|---|---|
| `test_store` | Library snapshot round trip and validation, earlier names kept across syncs; the capture queue: add, validate, acknowledge, and the 100-item cap; reading the version from `pyproject.toml` |
| `test_logic` | Node logic: dropdown labels, wildcard rolls, outfits (fixed, none, random), character formats, recipe values and defaults, finding renamed items by their old label |

`web/missing.js` has its own Node test (Node 18+, no ComfyUI): `node --test tests/test_missing.mjs`. It covers the recipe/1 conversion, missing-model detection and the Model Librarian notice.

## Releasing

1. Bump `version` in `pyproject.toml`. It's the only place the version is written: the server reads it for `/prompto/status`, and the bridge asks the server.
2. Commit and push to `main`.
3. `.github/workflows/publish.yml` publishes to the [Comfy Registry](https://registry.comfy.org) whenever `pyproject.toml` changes on `main` (or run it by hand from the Actions tab). A push that only changes docs (`README.md`, `docs/`, `LICENSE`, `.github/`, or just the version line) is skipped; `.github/scripts/needs-publish.sh` decides. It needs a `REGISTRY_ACCESS_TOKEN` repository secret: a publisher API key for `looneth` from registry.comfy.org. Without it the run only leaves a notice.
