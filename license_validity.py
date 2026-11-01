"""Read explicitly labelled validity starts; do not infer starts from issue dates."""
import re
from validation import dates_in_text

_LABEL = re.compile(
    r"valid\s+from|effective\s+(?:from|on)|starts?\s+on|"
    r"تاريخ\s+(?:بدء|بداية)\s+(?:السريان|الصلاحية)|"
    r"ساري(?:ة)?\s+من|يسري\s+من", re.I
)


def explicit_start(text):
    """Return (label_seen, unique_date); ambiguous/invalid labelled dates stay None."""
    starts = set()
    matches = list(_LABEL.finditer(text))
    for match in matches:
        fragment = text[match.end():].splitlines()[0]
        fragment = re.split(r"\buntil\b|\bto\b|حتى|إلى|الى|[.;]", fragment, maxsplit=1, flags=re.I)[0]
        dates = dates_in_text(fragment)
        if len(dates) != 1:
            return True, None
        starts.update(dates)
    return bool(matches), next(iter(starts)) if len(starts) == 1 else None
