"""Arabic text normalization and direction repair utilities for PDF extraction."""

import unicodedata
import re


def _has_arabic(text: str) -> bool:
    return any("ARABIC" in unicodedata.name(char, "") for char in text)


def _unshape_arabic(text: str) -> str:
    return "".join(
        unicodedata.normalize("NFKC", char)
        if "ARABIC" in unicodedata.name(char, "")
        and ("\uFB50" <= char <= "\uFDFF" or "\uFE70" <= char <= "\uFEFC")
        else char
        for char in text
    )


def normalize_arabic_text(text: str) -> tuple[str, bool]:
    """Normalize presentation forms without guessing ordinary Arabic order."""
    return _unshape_arabic(text), _has_arabic(text)


def _arabic_order_errors(value: str) -> int:
    count = 0
    forms = {
        "INITIAL": (False, True),
        "MEDIAL": (True, True),
        "FINAL": (True, False),
        "ISOLATED": (False, False),
    }
    for word in value.split():
        edges = []
        for char in word:
            if not unicodedata.category(char).startswith("L"):
                continue
            name = unicodedata.name(char, "")
            edges.append(
                next(
                    (
                        pair
                        for form, pair in forms.items()
                        if "ARABIC" in name and f"{form} FORM" in name
                    ),
                    None,
                )
            )
        if len(edges) < 2:
            continue
        count += bool(edges[0] and edges[0][0])
        count += bool(edges[-1] and edges[-1][1])
        count += sum(
            left[1] != right[0]
            for left, right in zip(edges, edges[1:])
            if left is not None and right is not None
        )
    return count


def recover_arabic_run(text: str) -> str:
    """Repair a pypdf visitor run only with consistent contextual-form evidence."""
    result = []
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        ending = line[len(content) :]

        has_ltr = any(unicodedata.bidirectional(c) in {"L", "EN"} for c in content)
        errors = _arabic_order_errors(content)
        bounded_word = (
            bool(content)
            and not content[0].isalpha()
            and not content[-1].isalpha()
            and len(
                [
                    word
                    for word in content.split()
                    if any(char.isalpha() for char in word)
                ]
            )
            == 1
        )
        if (
            not has_ltr
            and (errors >= 2 or errors == 1 and bounded_word)
            and _arabic_order_errors(content[::-1]) == 0
        ):
            content = content[::-1]
        result.append(_unshape_arabic(content) + ending)
    return "".join(result)