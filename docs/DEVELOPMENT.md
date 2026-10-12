# Development

The repository root is the custom node package: ComfyUI imports `__init__.py` and serves `web/`.

```
__init__.py        registers the routes and the web directory (no nodes yet)
prompto_routes.py  /prompto HTTP routes, on ComfyUI's PromptServer
prompto_store.py   JSON storage for the library snapshot and capture queue (no ComfyUI imports)
web/prompto.js     frontend extension: bridge install, sidebar tab, node menus, auto-capture
web/bridge.js      window.PromptoBridge, graph editing, image capture
web/sidebar.js     the Prompto sidebar tab
web/prompto.css    sidebar styles (prefixed pm-)
tests/             pytest suites
docs/              this file
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
| `test_store` | Library snapshot round trip and validation; the capture queue: add, validate, acknowledge, and the 100-item cap |

## Releasing

1. Bump `version` in `pyproject.toml` and `VERSION` in `prompto_routes.py` and `web/bridge.js`.
2. Commit and push to `main`.
3. Publish to the Comfy Registry with `comfy node publish`. One-time setup: fill in `PublisherId` in `pyproject.toml` and create a registry API key.
