"""ComfyUI-Prompto: the ComfyUI side of the Prompto Chrome extension.

It ships a frontend extension (web/), routes that let the Chrome extension
load recipes into the graph and collect captures, and Prompto nodes that read
the synced library (recipes, cast, snippets, wildcards).
"""

WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# ComfyUI imports this as a package; pytest may import it bare while collecting tests.
if __package__:
    from . import prompto_routes  # noqa: F401  (registers the /prompto routes)
    from .prompto_nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from .prompto_banner import show

    show(prompto_routes.VERSION, len(NODE_CLASS_MAPPINGS))

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
