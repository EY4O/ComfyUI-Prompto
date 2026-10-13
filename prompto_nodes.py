"""Prompto nodes: recipes, cast members, snippets and wildcards from the
library the Prompto Chrome extension syncs to this ComfyUI.

The dropdowns are read when ComfyUI loads node definitions, so after syncing
new items press R in ComfyUI (or refresh the page) to see them.
"""

import comfy.samplers

from . import prompto_logic as L
from .prompto_routes import store

CATEGORY = "Prompto"
FORMATS = ["tags", "prose", "tags + prose"]
SAMPLERS = comfy.samplers.KSampler.SAMPLERS
SCHEDULERS = comfy.samplers.KSampler.SCHEDULERS


def library():
    return store.get_library() or {}


def aliases(lib, kind):
    """Labels items had before they were renamed in Prompto."""
    return (lib.get("aliases") or {}).get(kind) or {}


def synced_at():
    return (store.get_library() or {}).get("syncedAt")


class _PromptoNode:
    CATEGORY = CATEGORY

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        # The library changes from Chrome; a name picked earlier may no longer be
        # in the dropdown, so run-time lookups report missing items instead.
        return True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return f"{synced_at()}|{sorted(kwargs.items())}"


class PromptoRecipe(_PromptoNode):
    @classmethod
    def INPUT_TYPES(cls):
        lib = library()
        return {"required": {
            "recipe": (L.labels(lib.get("recipes"), L.recipe_label),),
            "roll": ("INT", {"default": 1, "min": 0, "max": 0xFFFFFFFF, "tooltip": "Seed for {a|b} and __snippet__ wildcards in the recipe"}),
        }}

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "FLOAT", "INT", "INT", SAMPLERS, SCHEDULERS)
    RETURN_NAMES = ("positive", "negative", "seed", "steps", "cfg", "width", "height", "sampler", "scheduler")
    FUNCTION = "run"
    DESCRIPTION = "A Prompto recipe's prompt and settings."

    def run(self, recipe, roll):
        lib = library()
        r = L.find(lib.get("recipes"), recipe, L.recipe_label, aliases(lib, "recipes"))
        if not r:
            raise ValueError(f"Prompto has no recipe called “{recipe}”. Open Prompto in Chrome with this ComfyUI tab open, then press R.")
        v = L.recipe_values(r, roll, lib.get("snippets"))
        sampler = v["sampler"] if v["sampler"] in SAMPLERS else SAMPLERS[0]
        scheduler = v["scheduler"] if v["scheduler"] in SCHEDULERS else SCHEDULERS[0]
        return (v["positive"], v["negative"], v["seed"], v["steps"], v["cfg"], v["width"], v["height"], sampler, scheduler)


class PromptoCharacter(_PromptoNode):
    @classmethod
    def INPUT_TYPES(cls):
        lib = library()
        return {"required": {
            "character": (L.labels(lib.get("cast"), L.cast_label),),
            "outfit": (L.outfit_names(lib.get("cast")), {"tooltip": "An outfit name that this character doesn't have is treated as (none)"}),
            "format": (FORMATS,),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF, "tooltip": "Picks the outfit when outfit is (random)"}),
        }}

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "outfit")
    FUNCTION = "run"
    DESCRIPTION = "A Prompto cast member's tags and/or prose, with an outfit."

    def run(self, character, outfit, format, seed):
        lib = library()
        c = L.find(lib.get("cast"), character, L.cast_label, aliases(lib, "cast"))
        if not c:
            raise ValueError(f"Prompto has no cast member called “{character}”. Sync from Chrome, then press R.")
        return L.character_text(c, outfit, format, seed)


class PromptoSnippet(_PromptoNode):
    @classmethod
    def INPUT_TYPES(cls):
        lib = library()
        return {"required": {
            "snippet": (L.labels(lib.get("snippets"), L.snippet_label),),
            "format": (["tags", "prose"],),
            "roll": ("INT", {"default": 1, "min": 0, "max": 0xFFFFFFFF}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    DESCRIPTION = "A Prompto snippet as text."

    def run(self, snippet, format, roll):
        lib = library()
        s = L.find(lib.get("snippets"), snippet, L.snippet_label, aliases(lib, "snippets"))
        if not s:
            raise ValueError(f"Prompto has no snippet called “{snippet}”. Sync from Chrome, then press R.")
        text = ", ".join(s.get("tags") or []) if format == "tags" else (s.get("prose") or ", ".join(s.get("tags") or []))
        return (L.expand(text, roll, lib.get("snippets")),)


class PromptoWildcards(_PromptoNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "text": ("STRING", {"multiline": True, "default": "1girl, {silver|black|red} hair, __hair_color__"}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    DESCRIPTION = "Rolls {a|b} choices and __snippet__ wildcards from your Prompto snippets."

    def run(self, text, seed):
        return (L.expand(text, seed, library().get("snippets")),)


NODE_CLASS_MAPPINGS = {
    "PromptoRecipe": PromptoRecipe,
    "PromptoCharacter": PromptoCharacter,
    "PromptoSnippet": PromptoSnippet,
    "PromptoWildcards": PromptoWildcards,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptoRecipe": "Prompto Recipe",
    "PromptoCharacter": "Prompto Character",
    "PromptoSnippet": "Prompto Snippet",
    "PromptoWildcards": "Prompto Wildcards",
}
