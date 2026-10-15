import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import prompto_logic as L  # noqa: E402

SAMPLES = json.load(open(os.path.join(ROOT, "samples.json"), encoding="utf-8"))
LABELS = {
    "PromptoRecipe": ("recipes", L.recipe_label),
    "PromptoCharacter": ("cast", L.cast_label),
    "PromptoSnippet": ("snippets", L.snippet_label),
    "PromptoProfile": ("profiles", L.profile_label),
}


def test_samples_hold_every_kind():
    for kind in ("recipes", "cast", "snippets", "profiles"):
        assert SAMPLES[kind], kind
    assert all(r.get("renders") for r in SAMPLES["recipes"])


def test_example_workflows_only_name_sample_items():
    """The examples must run before anything is synced, so whatever their Prompto
    nodes pick has to be in samples.json."""
    folder = os.path.join(ROOT, "example_workflows")
    for name in os.listdir(folder):
        if not name.endswith(".json"):
            continue
        wf = json.load(open(os.path.join(folder, name), encoding="utf-8"))
        for node in wf["nodes"]:
            if node["type"] in LABELS:
                kind, fn = LABELS[node["type"]]
                picked = node["widgets_values"][0]
                assert L.find(SAMPLES[kind], picked, fn), f"{name}: {node['type']} picks “{picked}”, which isn't a sample"
