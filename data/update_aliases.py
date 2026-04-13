"""Update gc_org_aliases.csv with new aliases from gc_concordance.csv.

Reads the existing aliases file first, then scans the concordance for new
aliases to add. Existing aliases are never removed or modified — only new
normalized forms that aren't already in the file get appended.

For each row in the Names and Codes dataset, the following fields are treated
as alias sources: harmonized_name, nom_harmonisé, abbreviation, abreviation,
ati, open_gov_ouvert. Duplicate normalized forms are resolved according to the
KNOWN_CONFLICTS dictionary or, if they're not known, the first value is
accepted and we print a message for attention later.

"""

import csv
import sys
from pathlib import Path

# Allow running from the repo root or from data/ directly.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from gcorg_resolver.normalize import normalize  # noqa: E402

CONCORDANCE_PATH = _HERE / "gc_concordance.csv"
ALIASES_PATH = _HERE / "gc_org_aliases.csv"

# Fields that potentially contain aliases that help us resolve names
ALIAS_FIELDS = [
    "harmonized_name",
    "nom_harmonisé",
    "abbreviation",
    "abreviation",
    "ati",
    "open_gov_ouvert",
]

# Some short abbreivations correspond to to more than one organization.
# For these known conflicts, we intentionally choose what we feel is 
# the best match.

KNOWN_CONFLICTS = {
    # Registrar of the Supreme Court of Canada (2287)
    # Service correctionnel Canada (2255)
    "scc": 2255,  

    # Registraire de la Cour suprême du Canada (2287) 
    # Correctional Service Canada (2255)
    "csc": 2255,

    # Agence spatiale canadienne (2251) 
    # Accessibility Standards Canada (2319)
    "asc": 2251,
}

if __name__ == "__main__":
    # Load existing aliases so we never remove or overwrite them.
    existing_rows: list[tuple[str, int]] = []
    seen: dict[str, int] = {}

    if ALIASES_PATH.exists():
        with ALIASES_PATH.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["name"]
                gc_org_id = int(row["gc_orgID"])
                existing_rows.append((name, gc_org_id))
                seen[name] = gc_org_id

    # Scan the concordance for new aliases not already in the file.
    new_rows: list[tuple[str, int]] = []

    with CONCORDANCE_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for concordance_row in reader:
            gc_org_id = int(concordance_row["gc_orgID"])

            for field in ALIAS_FIELDS:
                raw = concordance_row.get(field, "").strip()
                if not raw:
                    continue

                normalized = normalize(raw)

                # If we get a blank string after normalization, skip
                if not normalized:
                    continue

                # If this is a known conflict, use the designated org and skip
                # any other occurrence without printing a warning.
                if normalized in KNOWN_CONFLICTS:
                    resolved_id = KNOWN_CONFLICTS[normalized]
                    if normalized not in seen:
                        seen[normalized] = resolved_id
                        new_rows.append((normalized, resolved_id))
                    continue

                # If the alias is already in the list (i.e., not a known conflict), skip
                if normalized in seen:
                    if seen[normalized] != gc_org_id:
                        print(
                            f"Skipping duplicate alias '{normalized}' "
                            f"(already assigned to {seen[normalized]}, "
                            f"conflict with {gc_org_id})"
                        )
                    continue

                seen[normalized] = gc_org_id
                new_rows.append((normalized, gc_org_id))

    # Combine existing and new, sort alphabetically, and write.
    all_rows = existing_rows + new_rows
    all_rows.sort(key=lambda r: r[0])

    with ALIASES_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "gc_orgID"])
        writer.writerows(all_rows)

    print(f"{len(existing_rows)} existing aliases, {len(new_rows)} new — {len(all_rows)} total written to {ALIASES_PATH}")
