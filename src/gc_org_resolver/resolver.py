"""Resolve free-text organization names to a ``gc_orgID``.

Exact match first: normalize the input with the same pipeline used to build
``data/gc_org_aliases.csv`` and look the result up in an in-memory index.
On a miss, fall back to a string-distance search against the aliases — but
only when the normalized query is long enough that fuzzy matching is safe.
Short tokens like abbreviations are too easy to confuse and stay exact-only.
"""

import csv
from difflib import get_close_matches
from functools import cache
from pathlib import Path

from gc_org_resolver.normalize import normalize

ALIASES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "gc_org_aliases.csv"
)

# Only fuzzy-match when the normalized query is at least this long. Below
# this, one typo can shift an abbreviation to a neighbour (``csc`` → ``csa``)
# and quietly return the wrong org.
FUZZY_MATCH_MIN_LENGTH = 10

# Minimum ``difflib`` similarity ratio for a fuzzy hit to count. A single
# typo in a 20-char string lands around 0.95; two typos around 0.90
FUZZY_MATCH_MIN_RATIO = 0.85


@cache
def _alias_index() -> dict[str, int]:
    with ALIASES_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {row["name"]: int(row["gc_orgID"]) for row in reader}


def resolve(name: str) -> int | None:
    """Return the ``gc_orgID`` that ``name`` resolves to, or ``None``."""
    query = normalize(name)
    index = _alias_index()
    if query in index:
        return index[query]
    if len(query) >= FUZZY_MATCH_MIN_LENGTH:
        matches = get_close_matches(
            query, index.keys(), n=1, cutoff=FUZZY_MATCH_MIN_RATIO
        )
        if matches:
            return index[matches[0]]
    return None
