import csv
from collections import Counter
from pathlib import Path

import pytest

ALIASES_CSV = Path(__file__).resolve().parents[1] / "data" / "gc_org_aliases.csv"

# Look for UTF-8 characters that have been rendered in Latin-1
MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "â€",
    "\ufffd",
)


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str]]:
    with ALIASES_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_aliases_csv_decodes_as_strict_utf8() -> None:
    ALIASES_CSV.read_bytes().decode("utf-8", errors="strict")


def test_name_column_has_no_duplicates(rows: list[dict[str, str]]) -> None:
    counts = Counter(r["name"] for r in rows)
    dupes = {name: n for name, n in counts.items() if n > 1}
    assert dupes == {}, f"duplicate names: {dupes}"


def test_known_unicode_aliases_are_present(
    rows: list[dict[str, str]],
) -> None:
    """Verify that orgs with accented names produce the expected normalized aliases."""
    aliases = {r["name"] for r in rows}
    assert "montreal port authority" in aliases
    assert "quebec port authority" in aliases
    assert "sept-iles port authority" in aliases
    assert "trois-rivieres port authority" in aliases


def test_no_mojibake(rows: list[dict[str, str]]) -> None:
    offenders: list[tuple[int, str, str]] = []
    for i, row in enumerate(rows, start=2):
        for col, value in row.items():
            # Check each bad-sequence marker, e.g. "Ã" in "MontrÃ©al".
            for marker in MOJIBAKE_MARKERS:
                if marker in value:
                    offenders.append((i, col, value))
    # Truncate the failure message so we don't dump hundreds of rows
    assert offenders == [], f"mojibake detected: {offenders[:5]}"
