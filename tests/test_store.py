import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompto_store import MAX_CAPTURES, Store, read_version  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path))


def test_library_round_trip(store):
    assert store.get_library() is None
    synced = store.set_library({"syncedAt": 123, "recipes": [{"id": "r1"}], "snippets": [], "cast": [], "extra": "dropped"})
    assert synced == 123
    lib = store.get_library()
    # aliases holds labels items had before a rename; none yet
    assert lib == {"syncedAt": 123, "recipes": [{"id": "r1"}], "snippets": [], "cast": [],
                   "aliases": {"recipes": {}, "snippets": {}, "cast": {}}}


def test_library_rejects_bad_shapes(store):
    with pytest.raises(ValueError):
        store.set_library([])
    with pytest.raises(ValueError):
        store.set_library({"recipes": "nope"})


def test_captures_queue_and_ack(store):
    a = store.add_capture({"kind": "text", "text": "silver hair, rain"})
    b = store.add_capture({"kind": "generation", "graph": {"1": {}}, "thumb": "data:image/jpeg;base64,xx"})
    assert [c["id"] for c in store.list_captures()] == [a, b]
    assert store.ack_captures([a]) == 1
    assert [c["id"] for c in store.list_captures()] == [b]
    assert store.status()["captures"] == 1


def test_captures_validate(store):
    for bad in ({"kind": "video"}, {"kind": "text", "text": "  "}, {"kind": "generation"}, "text"):
        with pytest.raises(ValueError):
            store.add_capture(bad)


def test_capture_queue_is_bounded(store):
    for i in range(MAX_CAPTURES + 5):
        store.add_capture({"kind": "text", "text": f"tag {i}"})
    items = store.list_captures()
    assert len(items) == MAX_CAPTURES
    assert items[0]["text"] == "tag 5"


def test_version_comes_from_pyproject(tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert read_version(os.path.join(root, "pyproject.toml"))[0].isdigit()
    p = tmp_path / "pyproject.toml"
    p.write_text('[project]\nname = "x"\nversion = "1.2.3"\n', encoding="utf-8")
    assert read_version(str(p)) == "1.2.3"
    assert read_version(str(tmp_path / "missing.toml")) == "unknown"


def test_library_sync_remembers_old_labels(store):
    store.set_library({"syncedAt": 1, "snippets": [{"id": "s1", "cat": "Lighting", "name": "Golden hour"}], "recipes": [], "cast": []})
    store.set_library({"syncedAt": 2, "snippets": [{"id": "s1", "cat": "Lighting", "name": "Magic hour"}], "recipes": [], "cast": []})
    lib = store.get_library()
    assert lib["aliases"]["snippets"] == {"Lighting · Golden hour": "s1"}
