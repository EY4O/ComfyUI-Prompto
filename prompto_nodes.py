"""Prompto nodes: recipes, cast members, snippets, wildcards, model profiles and
LoRAs from the library the Prompto Chrome extension syncs to this ComfyUI.

The dropdowns are read when ComfyUI loads node definitions, so after syncing
new items press R in ComfyUI (or refresh the page) to see them.

Prompto's sample library ships in samples.json. Until a library is synced the
dropdowns offer the samples, and an item a workflow names that isn't in the
synced library is looked up there, so the example workflows run as they are.
"""

import json
import logging
import os

import comfy.samplers
import folder_paths

from . import prompto_logic as L
from .prompto_routes import store

CATEGORY = "Prompto"
FORMATS = ["tags", "prose", "tags + prose"]
SAMPLERS = comfy.samplers.KSampler.SAMPLERS
SCHEDULERS = comfy.samplers.KSampler.SCHEDULERS


def library():
    return store.get_library() or {}


_samples = None


def samples():
    global _samples
    if _samples is None:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples.json"), encoding="utf-8") as f:
                _samples = json.load(f)
        except (OSError, ValueError):
            _samples = {}
    return _samples


def items(lib, kind):
    """The synced items of a kind, or the samples until something is synced.
    Profiles come from the samples too when Prompto is older than 0.24."""
    return lib.get(kind) or samples().get(kind) or []


def lookup(lib, kind, label, fn):
    """(item, snippets to roll its wildcards with). Falls back to the samples."""
    hit = L.find(lib.get(kind), label, fn, aliases(lib, kind))
    if hit:
        return hit, lib.get("snippets") or []
    hit = L.find(samples().get(kind), label, fn)
    return hit, samples().get("snippets") or []


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
            "recipe": (L.labels(items(lib, "recipes"), L.recipe_label),),
            "roll": ("INT", {"default": 1, "min": 0, "max": 0xFFFFFFFF, "control_after_generate": "fixed", "tooltip": "Seed for {a|b} and __snippet__ wildcards in the recipe"}),
            "profile": ([L.OWN] + L.labels(items(lib, "profiles"), L.profile_label), {"tooltip": "Write the recipe for another model: that profile's prompt and sampler settings, the recipe's seed"}),
        }}

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "FLOAT", "INT", "INT", SAMPLERS, SCHEDULERS)
    RETURN_NAMES = ("positive", "negative", "seed", "steps", "cfg", "width", "height", "sampler", "scheduler")
    FUNCTION = "run"
    DESCRIPTION = "A Prompto recipe's prompt and settings."

    def run(self, recipe, roll, profile=L.OWN):
        lib = library()
        r, snippets = lookup(lib, "recipes", recipe, L.recipe_label)
        if not r:
            raise ValueError(f"Prompto has no recipe called “{recipe}”. Open Prompto in Chrome with this ComfyUI tab open, then press R.")
        p = None
        if profile != L.OWN:
            p, _ = lookup(lib, "profiles", profile, L.profile_label)
            if not p:
                raise ValueError(f"Prompto has no model profile called “{profile}”. Sync from Chrome, then press R.")
        v = L.recipe_values(r, roll, snippets, p)
        sampler = v["sampler"] if v["sampler"] in SAMPLERS else SAMPLERS[0]
        scheduler = v["scheduler"] if v["scheduler"] in SCHEDULERS else SCHEDULERS[0]
        return (v["positive"], v["negative"], v["seed"], v["steps"], v["cfg"], v["width"], v["height"], sampler, scheduler)


class PromptoCharacter(_PromptoNode):
    @classmethod
    def INPUT_TYPES(cls):
        lib = library()
        return {"required": {
            "character": (L.labels(items(lib, "cast"), L.cast_label),),
            "outfit": (L.outfit_names(items(lib, "cast")), {"tooltip": "An outfit name that this character doesn't have is treated as (none)"}),
            "format": (FORMATS,),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF, "tooltip": "Picks the outfit when outfit is (random)"}),
        }}

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "outfit")
    FUNCTION = "run"
    DESCRIPTION = "A Prompto cast member's tags and/or prose, with an outfit."

    def run(self, character, outfit, format, seed):
        lib = library()
        c, _ = lookup(lib, "cast", character, L.cast_label)
        if not c:
            raise ValueError(f"Prompto has no cast member called “{character}”. Sync from Chrome, then press R.")
        return L.character_text(c, outfit, format, seed)


class PromptoSnippet(_PromptoNode):
    @classmethod
    def INPUT_TYPES(cls):
        lib = library()
        return {"required": {
            "snippet": (L.labels(items(lib, "snippets"), L.snippet_label),),
            "format": (["tags", "prose"],),
            "roll": ("INT", {"default": 1, "min": 0, "max": 0xFFFFFFFF, "control_after_generate": "fixed", "tooltip": "Seed for {a|b} and __snippet__ wildcards in the snippet"}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    DESCRIPTION = "A Prompto snippet as text."

    def run(self, snippet, format, roll):
        lib = library()
        s, snippets = lookup(lib, "snippets", snippet, L.snippet_label)
        if not s:
            raise ValueError(f"Prompto has no snippet called “{snippet}”. Sync from Chrome, then press R.")
        text = ", ".join(s.get("tags") or []) if format == "tags" else (s.get("prose") or ", ".join(s.get("tags") or []))
        return (L.expand(text, roll, snippets),)


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
        return (L.expand(text, seed, items(library(), "snippets")),)


class PromptoProfile(_PromptoNode):
    @classmethod
    def INPUT_TYPES(cls):
        lib = library()
        return {"required": {
            "profile": (L.labels(items(lib, "profiles"), L.profile_label),),
            "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Your prompt: wire in Prompto Character, Snippet or Wildcards, or type"}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF, "control_after_generate": "fixed", "tooltip": "Seed for any {a|b} and __snippet__ wildcards left in the text"}),
        }}

    RETURN_TYPES = ("STRING", "STRING", "INT", "FLOAT", "INT", "INT", SAMPLERS, SCHEDULERS)
    RETURN_NAMES = ("positive", "negative", "steps", "cfg", "width", "height", "sampler", "scheduler")
    FUNCTION = "run"
    DESCRIPTION = "Writes text the way a Prompto model profile does (quality tags first, artist tags in its style) and outputs the profile's negative and sampler settings."

    def run(self, profile, text, seed):
        lib = library()
        p, _ = lookup(lib, "profiles", profile, L.profile_label)
        if not p:
            raise ValueError(f"Prompto has no model profile called “{profile}”. Sync from Chrome, then press R.")
        v = L.profile_values(p, text, items(lib, "snippets"), seed)
        sampler = v["sampler"] if v["sampler"] in SAMPLERS else SAMPLERS[0]
        scheduler = v["scheduler"] if v["scheduler"] in SCHEDULERS else SCHEDULERS[0]
        return (v["positive"], v["negative"], v["steps"], v["cfg"], v["width"], v["height"], sampler, scheduler)


class PromptoLoras(_PromptoNode):
    @classmethod
    def INPUT_TYPES(cls):
        lib = library()
        return {"required": {
            "model": ("MODEL",),
            "clip": ("CLIP",),
            "recipe": ([L.NONE] + L.labels(items(lib, "recipes"), L.recipe_label), {"tooltip": "Apply the LoRAs listed in this recipe's settings"}),
            "character": ([L.NONE] + L.labels(items(lib, "cast"), L.cast_label), {"tooltip": "Apply this cast member's LoRA"}),
            "strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05, "tooltip": "Multiplies every LoRA's weight from Prompto"}),
        }}

    RETURN_TYPES = ("MODEL", "CLIP", "STRING")
    RETURN_NAMES = ("model", "clip", "loras")
    FUNCTION = "run"
    DESCRIPTION = "Applies a Prompto recipe's LoRAs and/or a cast member's LoRA, matched to your loras folder by file name."

    def run(self, model, clip, recipe, character, strength):
        from nodes import LoraLoader

        lib = library()
        r = lookup(lib, "recipes", recipe, L.recipe_label)[0] if recipe != L.NONE else None
        c = lookup(lib, "cast", character, L.cast_label)[0] if character != L.NONE else None
        installed = folder_paths.get_filename_list("loras")
        applied, missing = [], []
        loader = LoraLoader()
        for name, w in L.loras_for(r, c):
            f = L.match_lora(name, installed)
            if not f:
                missing.append(L.lora_stem(name))
                continue
            model, clip = loader.load_lora(model, clip, f, w * strength, w * strength)
            applied.append(f"{L.lora_stem(f)} {w * strength:g}")
        if missing:
            logging.warning("[Prompto] LoRAs not in the loras folder: %s", ", ".join(missing))
        summary = ", ".join(applied) + (("; missing: " + ", ".join(missing)) if missing else "")
        return (model, clip, summary)


NODE_CLASS_MAPPINGS = {
    "PromptoRecipe": PromptoRecipe,
    "PromptoCharacter": PromptoCharacter,
    "PromptoSnippet": PromptoSnippet,
    "PromptoWildcards": PromptoWildcards,
    "PromptoProfile": PromptoProfile,
    "PromptoLoras": PromptoLoras,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptoRecipe": "Prompto Recipe",
    "PromptoCharacter": "Prompto Character",
    "PromptoSnippet": "Prompto Snippet",
    "PromptoWildcards": "Prompto Wildcards",
    "PromptoProfile": "Prompto Profile",
    "PromptoLoras": "Prompto LoRAs",
}
