import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import prompto_banner as B  # noqa: E402


def test_banner_has_the_art_and_the_version():
    text = B.banner("1.2.3", 4)
    assert text.startswith("\n")  # the art starts below ComfyUI's timestamp
    assert text.count("\n") == 15  # a blank line, 14 lines of art, then the version line
    assert text.endswith("[Prompto] ComfyUI-Prompto 1.2.3 loaded · 4 nodes")


def test_a_console_without_braille_gets_one_plain_line():
    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    B.show("1.2.3", 4, out)
    out.flush()
    assert raw.getvalue().decode("cp1252").strip() == "[Prompto] ComfyUI-Prompto 1.2.3 loaded - 4 nodes"


def test_a_utf8_console_gets_the_art():
    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="utf-8")
    B.show("1.2.3", 4, out)
    out.flush()
    assert "⣿" in raw.getvalue().decode("utf-8")
