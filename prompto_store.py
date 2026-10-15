"""JSON files behind the Prompto routes: a read-only library snapshot pushed by
the Chrome extension, and a queue of captures waiting to be collected by it.

Kept free of ComfyUI imports so it can be tested on its own.
"""

import json
import os
import re
import threading
import time
import uuid

try:
    from . import prompto_logic as L
except ImportError:  # imported bare, as the tests do
    import prompto_logic as L

MAX_CAPTURES = 100
MAX_LIBRARY_BYTES = 25 * 1024 * 1024
MAX_CAPTURE_BYTES = 4 * 1024 * 1024
CAPTURE_KINDS = {"generation", "text"}
LIBRARY_LISTS = ("recipes", "snippets", "cast", "profiles")


def read_version(path):
    """The [project] version from pyproject.toml, the one place it's written."""
    try:
        with open(path, encoding="utf-8") as f:
            m = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.M)
        return m.group(1) if m else "unknown"
    except OSError:
        return "unknown"


class Store:
    def __init__(self, base_dir):
        self.base = base_dir
        self.lock = threading.Lock()
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, name):
        return os.path.join(self.base, name)

    def _read(self, name, default):
        try:
            with open(self._path(name), encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _write(self, name, data):
        # Write to a temp file first so a crash never leaves half a file behind.
        tmp = self._path(name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self._path(name))

    # ---------- library ----------
    def get_library(self):
        return self._read("library.json", None)

    def set_library(self, snapshot):
        if not isinstance(snapshot, dict):
            raise ValueError("library must be an object")
        clean = {"syncedAt": snapshot.get("syncedAt") or int(time.time() * 1000)}
        for key in LIBRARY_LISTS:
            value = snapshot.get(key, [])
            if not isinstance(value, list):
                raise ValueError(f"{key} must be a list")
            clean[key] = value
        with self.lock:
            old = self._read("library.json", None) or {}
            clean["aliases"] = L.update_aliases(old, clean, old.get("aliases"))
            self._write("library.json", clean)
        return clean["syncedAt"]

    # ---------- captures ----------
    def list_captures(self):
        return self._read("captures.json", [])

    def add_capture(self, capture):
        if not isinstance(capture, dict) or capture.get("kind") not in CAPTURE_KINDS:
            raise ValueError("unknown capture kind")
        if capture["kind"] == "text" and not str(capture.get("text", "")).strip():
            raise ValueError("text capture is empty")
        if capture["kind"] == "generation" and not (capture.get("graph") or capture.get("thumb")):
            raise ValueError("generation capture needs a graph or an image")
        item = dict(capture)
        item["id"] = "cmf_" + uuid.uuid4().hex[:12]
        item["createdAt"] = int(time.time() * 1000)
        with self.lock:
            items = self.list_captures()
            items.append(item)
            # Oldest captures go first once the queue is full.
            self._write("captures.json", items[-MAX_CAPTURES:])
        return item["id"]

    def ack_captures(self, ids):
        ids = set(ids or [])
        with self.lock:
            items = self.list_captures()
            keep = [c for c in items if c.get("id") not in ids]
            self._write("captures.json", keep)
        return len(items) - len(keep)

    def status(self):
        library = self.get_library()
        return {
            "captures": len(self.list_captures()),
            "librarySyncedAt": library.get("syncedAt") if library else None,
        }
