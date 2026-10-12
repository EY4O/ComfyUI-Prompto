"""HTTP routes under /prompto (ComfyUI also mirrors them under /api/prompto).

They're called from the ComfyUI page itself, so ComfyUI's same-origin check
passes. The Chrome extension reaches them through the open ComfyUI tab.
"""

import json
import logging
import os

from aiohttp import web
from server import PromptServer

from .prompto_store import MAX_CAPTURE_BYTES, MAX_LIBRARY_BYTES, Store

VERSION = "0.4.0"

try:
    import folder_paths

    DATA_DIR = os.path.join(folder_paths.get_user_directory(), "prompto")
except Exception:  # older ComfyUI without a user directory
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

store = Store(DATA_DIR)
routes = PromptServer.instance.routes


async def _json_body(request, limit):
    raw = await request.read()
    if len(raw) > limit:
        raise web.HTTPRequestEntityTooLarge(max_size=limit, actual_size=len(raw))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise web.HTTPBadRequest(text="Body isn't valid JSON")


@routes.get("/prompto/status")
async def status(request):
    return web.json_response({"ok": True, "version": VERSION, **store.status()})


@routes.get("/prompto/library")
async def get_library(request):
    return web.json_response(store.get_library() or {})


@routes.post("/prompto/library")
async def set_library(request):
    body = await _json_body(request, MAX_LIBRARY_BYTES)
    try:
        synced = store.set_library(body)
    except ValueError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response({"ok": True, "syncedAt": synced})


@routes.get("/prompto/captures")
async def list_captures(request):
    return web.json_response(store.list_captures())


@routes.post("/prompto/captures")
async def add_capture(request):
    body = await _json_body(request, MAX_CAPTURE_BYTES)
    try:
        capture_id = store.add_capture(body)
    except ValueError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response({"ok": True, "id": capture_id})


@routes.post("/prompto/captures/ack")
async def ack_captures(request):
    body = await _json_body(request, 64 * 1024)
    removed = store.ack_captures(body.get("ids") if isinstance(body, dict) else None)
    return web.json_response({"ok": True, "removed": removed})


logging.info("[Prompto] routes ready, data in %s", DATA_DIR)
