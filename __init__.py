"""ComfyUI-Prompto: the ComfyUI side of the Prompto Chrome extension.

No nodes yet. It ships a frontend extension (web/) and a few routes that let
the Chrome extension load recipes into the graph and collect captures.
"""

# ComfyUI imports this as a package; pytest may import it bare while collecting tests.
if __package__:
    from . import prompto_routes  # noqa: F401  (registers the /prompto routes)

WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
