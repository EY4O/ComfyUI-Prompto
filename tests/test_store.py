import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompto_store import MAX_CAPTURES, Store  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path))


def test_library_round_trip(store):
    assert store.get_library() is None
    synced = store.set_library({"syncedAt": 123, "recipes": [{"id": "r1"}], "snippets": [], "cast": [], "extra": "dropped"})
    assert synced == 123
    lib = store.get_library()
    assert lib == {"syncedAt": 123, "recipes": [{"id": "r1"}], "snippets": [], "cast": []}


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
