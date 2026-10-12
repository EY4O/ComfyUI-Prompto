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
