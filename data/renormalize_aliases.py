"""Re-normalize the ``name`` column in gc_org_aliases.csv.

Run this after changing the rules in ``gcorg_resolver.normalize`` so the
checked-in aliases file reflects the new normalization. Re-normalizing may
cause two previously distinct aliases to collapse to the same string:

- If they point to the same gc_orgID, the duplicate is dropped silently.
- If they point to different gc_orgIDs, the first occurrence wins and the
  conflict is printed so it can be resolved by hand (typically by adding an
  entry to KNOWN_CONFLICTS in update_aliases.py).

Rows whose name normalizes to an empty string are dropped.
"""

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from gcorg_resolver.normalize import normalize

ALIASES_PATH = HERE / "gc_org_aliases.csv"


if __name__ == "__main__":
    with ALIASES_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        original = [(row["name"], int(row["gc_orgID"])) for row in reader]

    renormalized: list[tuple[str, int]] = []
    seen: dict[str, int] = {}
    dropped_empty = 0
    conflicts = 0

    for name, gc_org_id in original:
        new_name = normalize(name)

        if not new_name:
            dropped_empty += 1
            continue

        if new_name in seen:
            if seen[new_name] != gc_org_id:
                print(
                    f"Conflict: '{name}' -> '{new_name}' would map to "
                    f"{gc_org_id}, but already assigned to {seen[new_name]}"
                )
                conflicts += 1
            continue

        seen[new_name] = gc_org_id
        renormalized.append((new_name, gc_org_id))

    renormalized.sort(key=lambda r: r[0])

    with ALIASES_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "gc_orgID"])
        writer.writerows(renormalized)

    print(
        f"{len(original)} rows in -> {len(renormalized)} rows out "
        f"({dropped_empty} dropped empty, {conflicts} conflicts) "
        f"written to {ALIASES_PATH}"
    )
