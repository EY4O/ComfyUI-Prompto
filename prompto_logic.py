"""Text logic behind the Prompto nodes, kept free of ComfyUI imports so it can
be tested on its own. It works on the library snapshot the Prompto Chrome
extension syncs (recipes, snippets and cast, prompts already rendered).
"""

import random
import re

NONE, RANDOM = "(none)", "(random)"
EMPTY = "(sync Prompto first)"

_CHOICE = re.compile(r"\{([^{}]*\|[^{}]*)\}")
_NAMED = re.compile(r"__([\w-]+)__")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").lower()).strip("_")


# ---------- labels for the dropdowns ----------
def recipe_label(r):
    return f"No. {int(r.get('no') or 0):03d} · {r.get('title') or 'Untitled'}"


def snippet_label(s):
    return f"{s.get('cat') or 'Snippets'} · {s.get('name') or 'Untitled'}"


def cast_label(c):
    return c.get("name") or "Unnamed"


def labels(items, fn):
    seen, out = set(), []
    for it in items or []:
        label = fn(it)
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out or [EMPTY]


def find(items, label, fn):
    return next((it for it in items or [] if fn(it) == label), None)


def outfit_names(cast):
    names = []
    for c in cast or []:
        for o in c.get("outfits") or []:
            if o.get("name") and o["name"] not in names:
                names.append(o["name"])
    return [NONE, RANDOM] + names


# ---------- wildcards ----------
def wildcard_entries(name, snippets):
    """__name__ is a snippet by name (one of its tags) or a category (one of its snippets)."""
    n = slug(name)
    for s in snippets or []:
        if slug(s.get("name")) == n:
            return list(s.get("tags") or []) or ([s["prose"]] if s.get("prose") else [])
    cat = [s for s in snippets or [] if slug(s.get("cat")) == n]
    return [", ".join(s["tags"]) if s.get("tags") else s.get("prose", "") for s in cat if s.get("tags") or s.get("prose")]


def expand(text, seed, snippets):
    """Rolls {a|b} choices and __name__ wildcards. The same seed gives the same text."""
    rng = random.Random(seed)
    out = str(text or "")
    for _ in range(40):
        changed = False

        def named(m):
            nonlocal changed
            entries = wildcard_entries(m.group(1), snippets)
            if not entries:
                return m.group(0)
            changed = True
            return rng.choice(entries)

        out = _NAMED.sub(named, out)
        m = _CHOICE.search(out)
        if m:
            out = out[: m.start()] + rng.choice(m.group(1).split("|")).strip() + out[m.end():]
            changed = True
        if not changed:
            break
    out = re.sub(r",\s*,", ",", out)
    return re.sub(r"^\s*,\s*|\s*,\s*$", "", out).replace("  ", " ")


# ---------- characters ----------
def pick_outfit(c, outfit, seed):
    outfits = c.get("outfits") or []
    if outfit == RANDOM:
        return random.Random(seed).choice(outfits) if outfits else None
    if outfit == NONE:
        return None
    return next((o for o in outfits if o.get("name") == outfit), None)


def character_text(c, outfit, fmt, seed):
    """fmt: 'tags', 'prose' or 'tags + prose'. Returns (text, outfit name used)."""
    o = pick_outfit(c, outfit, seed)
    tags = ", ".join([t for t in (c.get("tags") or []) + ((o or {}).get("tags") or []) if t])
    prose_parts = [c.get("prose") or c.get("proseDraft") or "", (o or {}).get("prose") or (o or {}).get("proseDraft") or ""]
    prose = ", ".join(p.strip().rstrip(".") for p in prose_parts if p and p.strip())
    if prose:
        prose = prose[0].upper() + prose[1:] + "."
    if fmt == "prose":
        text = prose or tags
    elif fmt == "tags + prose":
        text = "\n\n".join(x for x in (tags, prose) if x)
    else:
        text = tags
    return text, (o or {}).get("name", "")


def recipe_values(r, roll, snippets):
    """Everything a Recipe node outputs, with wildcards rolled."""
    s = r.get("settings") or {}
    pos = expand(r.get("positive") or "", roll, snippets)
    neg = r.get("negative")
    neg = expand(neg, roll + 1, snippets) if neg else ""

    def num(v, kind, default):
        try:
            return kind(v)
        except (TypeError, ValueError):
            return default

    return {
        "positive": pos,
        "negative": neg,
        "seed": num(s.get("seed"), int, 0),
        "steps": num(s.get("steps"), int, 28),
        "cfg": num(s.get("cfg"), float, 5.0),
        "width": num(s.get("width"), int, 1024),
        "height": num(s.get("height"), int, 1024),
        "sampler": s.get("sampler") or "euler",
        "scheduler": s.get("scheduler") or "normal",
    }
