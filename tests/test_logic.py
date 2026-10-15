import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import prompto_logic as L  # noqa: E402

SNIPPETS = [
    {"cat": "Wildcards", "name": "Hair color", "tags": ["silver hair", "red hair", "black hair"], "prose": ""},
    {"cat": "Lighting", "name": "Golden hour", "tags": ["golden hour", "lens flare"], "prose": "lit by low golden-hour sun"},
    {"cat": "Lighting", "name": "Moody rim", "tags": ["rim light"], "prose": ""},
]
CAST = [{
    "name": "Rin Aozora", "series": "Original", "tags": ["rin_aozora", "1girl", "silver hair"],
    "prose": "", "proseDraft": "Rin Aozora, a girl with silver hair",
    "outfits": [{"name": "street", "tags": ["hoodie", "shorts"], "prose": "wearing a hoodie and shorts"},
                {"name": "battle", "tags": ["armored coat"], "prose": ""}],
}]


def test_labels_and_lookup():
    recipes = [{"no": 1, "title": "Rainy neon alley"}, {"no": 12, "title": "Deck"}]
    assert L.labels(recipes, L.recipe_label) == ["No. 001 · Rainy neon alley", "No. 012 · Deck"]
    assert L.find(recipes, "No. 012 · Deck", L.recipe_label)["no"] == 12
    assert L.labels([], L.recipe_label) == [L.EMPTY]
    assert L.labels(SNIPPETS, L.snippet_label)[0] == "Wildcards · Hair color"


def test_outfit_names_include_none_and_random():
    assert L.outfit_names(CAST) == [L.NONE, L.RANDOM, "street", "battle"]


def test_expand_is_seeded_and_resolves_snippets():
    text = "1girl, __hair_color__, {red|blue|green} eyes, __lighting__, __unknown__"
    a, b = L.expand(text, 7, SNIPPETS), L.expand(text, 7, SNIPPETS)
    assert a == b
    assert "__unknown__" in a and "__hair_color__" not in a and "{" not in a
    assert any(L.expand(text, s, SNIPPETS) != a for s in range(1, 30))


def test_expand_nesting_and_empty_options():
    out = L.expand("a {big {red|blue}|small} cat, {|shiny}", 3, [])
    assert "{" not in out and not out.endswith(",")


def test_character_formats_and_outfits():
    text, used = L.character_text(CAST[0], "street", "tags", 0)
    assert text == "rin_aozora, 1girl, silver hair, hoodie, shorts" and used == "street"
    prose, _ = L.character_text(CAST[0], "street", "prose", 0)
    assert prose == "Rin Aozora, a girl with silver hair, wearing a hoodie and shorts."
    both, _ = L.character_text(CAST[0], L.NONE, "tags + prose", 0)
    assert both.startswith("rin_aozora") and "\n\n" in both
    # an outfit this character doesn't have counts as none
    assert L.character_text(CAST[0], "swimsuit", "tags", 0)[1] == ""
    picks = {L.character_text(CAST[0], L.RANDOM, "tags", s)[1] for s in range(20)}
    assert picks == {"street", "battle"}


def test_recipe_values_rolls_and_defaults():
    r = {"positive": "1girl, __hair_color__", "negative": "lowres", "settings": {"seed": "42", "steps": 30, "cfg": "4.5", "width": 832, "height": 1216, "sampler": "euler_ancestral", "scheduler": "karras"}}
    v = L.recipe_values(r, 5, SNIPPETS)
    assert v["positive"] == L.recipe_values(r, 5, SNIPPETS)["positive"] and "__" not in v["positive"]
    assert (v["seed"], v["steps"], v["cfg"], v["width"], v["sampler"]) == (42, 30, 4.5, 832, "euler_ancestral")
    blank = L.recipe_values({"positive": "x"}, 1, [])
    assert (blank["negative"], blank["steps"], blank["sampler"], blank["scheduler"]) == ("", 28, "euler", "normal")


def test_renamed_items_are_found_by_their_old_label():
    old = {"snippets": [{"id": "s1", "cat": "Lighting", "name": "Golden hour"}],
           "recipes": [{"id": "r1", "no": 1, "title": "Rainy neon alley"}],
           "cast": [{"id": "c1", "name": "Rin"}]}
    new = {"snippets": [{"id": "s1", "cat": "Light setups", "name": "Magic hour"}],
           "recipes": [{"id": "r1", "no": 1, "title": "Rainy alley"}],
           "cast": [{"id": "c1", "name": "Rin Aozora"}]}
    aliases = L.update_aliases(old, new)
    assert aliases["snippets"] == {"Lighting · Golden hour": "s1"}
    s = L.find(new["snippets"], "Lighting · Golden hour", L.snippet_label, aliases["snippets"])
    assert s["name"] == "Magic hour"
    assert L.find(new["recipes"], "No. 001 · Rainy neon alley", L.recipe_label, aliases["recipes"])["id"] == "r1"
    assert L.find(new["cast"], "Rin", L.cast_label, aliases["cast"])["id"] == "c1"
    # a second rename keeps the first old label working
    newer = {"snippets": [{"id": "s1", "cat": "Light setups", "name": "Blue hour"}]}
    chained = L.update_aliases(new, newer, aliases)
    assert chained["snippets"]["Lighting · Golden hour"] == "s1"
    assert chained["snippets"]["Light setups · Magic hour"] == "s1"


def test_a_label_in_use_belongs_to_the_live_item():
    old = {"cast": [{"id": "c1", "name": "Rin"}]}
    mid = {"cast": [{"id": "c1", "name": "Rin Aozora"}]}
    aliases = L.update_aliases(old, mid)
    later = {"cast": [{"id": "c1", "name": "Rin Aozora"}, {"id": "c2", "name": "Rin"}]}
    aliases = L.update_aliases(mid, later, aliases)
    assert "Rin" not in aliases["cast"]
    assert L.find(later["cast"], "Rin", L.cast_label, aliases["cast"])["id"] == "c2"


def test_deleted_items_are_not_found_through_aliases():
    aliases = {"Rin": "c1"}
    assert L.find([{"id": "c2", "name": "Vale"}], "Rin", L.cast_label, aliases) is None


ANIMA = {"id": "anima", "label": "Anima", "format": "hybrid", "prefix": ["masterpiece", "best quality", "score_7", "safe"],
         "negative": "worst quality, score_1", "artistAt": True,
         "settings": {"sampler": "er_sde", "scheduler": "simple", "steps": 30, "cfg": 4, "width": 896, "height": 1152}}
ILLUS = {"id": "illustrious", "label": "Illustrious", "format": "tags", "prefix": ["masterpiece"], "negative": "lowres",
         "artistAt": False, "settings": {"sampler": "euler_ancestral", "scheduler": "normal", "steps": 28, "cfg": 5}}
KREA = {"id": "krea", "label": "Flux Krea", "format": "prose", "prefix": [], "negative": None, "settings": {"cfg": 1}}


def test_artist_style_keeps_or_drops_the_at():
    text = "@big chungus, @_@, smile, (@foo:1.2)\n@bar, mail@home"
    assert L.artist_style(text, True) == text
    assert L.artist_style(text, False) == "big chungus, @_@, smile, (foo:1.2)\nbar, mail@home"


def test_profile_text_adds_the_quality_tags_once():
    assert L.profile_text(ANIMA, "1girl, @artist") == "masterpiece, best quality, score_7, safe, 1girl, @artist"
    assert L.profile_text(ANIMA, "Masterpiece, 1girl") == "best quality, score_7, safe, Masterpiece, 1girl"
    assert L.profile_text(ILLUS, "1girl, @artist") == "masterpiece, 1girl, artist"
    assert L.profile_text(KREA, "A girl on a bench.") == "A girl on a bench."
    assert L.profile_text(ANIMA, "") == "masterpiece, best quality, score_7, safe"


def test_profile_values():
    v = L.profile_values(ANIMA, "{red|red} hair", [], 3)
    assert v["positive"].endswith("red hair") and v["negative"] == "worst quality, score_1"
    assert (v["sampler"], v["scheduler"], v["steps"], v["cfg"], v["width"], v["height"]) == ("er_sde", "simple", 30, 4.0, 896, 1152)
    k = L.profile_values(KREA, "x")
    assert k["negative"] == "" and k["cfg"] == 1.0 and k["steps"] == 28


def test_recipe_values_for_another_profile():
    r = {"profileId": "illustrious", "positive": "masterpiece, 1girl", "negative": "lowres",
         "renders": {"anima": {"positive": "masterpiece, best quality, score_7, safe, 1girl", "negative": "worst quality"}},
         "settings": {"seed": 5, "sampler": "euler_ancestral", "steps": 28, "cfg": 5, "width": 832, "height": 1216}}
    own = L.recipe_values(r, 1, [])
    assert own["positive"] == "masterpiece, 1girl" and own["sampler"] == "euler_ancestral"
    assert L.recipe_values(r, 1, [], ILLUS)["positive"] == "masterpiece, 1girl", "its own profile changes nothing"
    a = L.recipe_values(r, 1, [], ANIMA)
    assert a["positive"].startswith("masterpiece, best quality, score_7") and a["negative"] == "worst quality"
    assert (a["sampler"], a["steps"], a["cfg"], a["width"], a["seed"]) == ("er_sde", 30, 4.0, 896, 5)
    # A snapshot from before renders existed: the profile's wrapping is added to the recipe's prompt.
    old = {k: v for k, v in r.items() if k != "renders"}
    assert L.recipe_values(old, 1, [], ANIMA)["positive"] == "best quality, score_7, safe, masterpiece, 1girl"


def test_loras_for_and_match_lora():
    r = {"settings": {"loras": [{"name": "chars/rin_aozora_v2.safetensors", "w": 0.8}, {"name": "detail.safetensors"}]}}
    c = {"lora": {"name": "Rin_Aozora_V2.safetensors", "w": 0.6}}
    assert L.loras_for(r, c) == [("chars/rin_aozora_v2.safetensors", 0.8), ("detail.safetensors", 1.0)]
    assert L.loras_for(None, c) == [("Rin_Aozora_V2.safetensors", 0.6)]
    installed = [r"Illustrious\characters\rin_aozora_v2.safetensors", "other.safetensors"]
    assert L.match_lora("rin_aozora_v2", installed) == installed[0]
    assert L.match_lora("missing.safetensors", installed) is None


def test_profile_renames_are_remembered():
    old = {"profiles": [{"id": "anima", "label": "Anima"}]}
    new = {"profiles": [{"id": "anima", "label": "Anima v1"}]}
    assert L.update_aliases(old, new)["profiles"] == {"Anima": "anima"}
