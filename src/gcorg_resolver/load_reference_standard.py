"""Load the pinned GC Organizations Reference Standard concordance snapshot.

The reference standard concordance is the canonical source of ``gc_orgID`` and
the English/French harmonized names and abbreviations we train on.
"""

import csv
from dataclasses import dataclass
from functools import cache
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent

# The data directory lives two levels up from this file in local dev
# (src/gcorg_resolver/ → src/ → repo root), but only one level up in Lambda
CONCORDANCE_FILENAME = "gc_concordance.csv"
REPO_ROOT_DATA = PKG_DIR.parent.parent / "data" / CONCORDANCE_FILENAME
LAMBDA_ROOT_DATA = PKG_DIR.parent / "data" / CONCORDANCE_FILENAME

if REPO_ROOT_DATA.exists():
    DEFAULT_PATH = REPO_ROOT_DATA
elif LAMBDA_ROOT_DATA.exists():
    DEFAULT_PATH = LAMBDA_ROOT_DATA
else:
    raise FileNotFoundError(
        f"Could not find gc_concordance.csv at {REPO_ROOT_DATA} or {LAMBDA_ROOT_DATA}"
    )


@dataclass(frozen=True)
class Org:
    gc_orgID: int
    harmonized_name: str
    nom_harmonise: str
    abbreviation: str
    abreviation: str
    infobaseID: str
    rg: str
    ati: str
    open_gov_ouvert: str
    pop: str
    phoenix: str
    website: str
    site_web: str

    def name_variants(self) -> list[str]:
        """Non-empty name/abbreviation forms from the concordance row."""
        return [
            v
            for v in (
                self.harmonized_name,
                self.nom_harmonise,
                self.abbreviation,
                self.abreviation,
            )
            if v
        ]


def load_reference_standard(path: Path | None = None) -> list[Org]:
    """Read the concordance CSV from disk and return one ``Org`` per row."""
    target = path if path is not None else DEFAULT_PATH
    with target.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            Org(
                gc_orgID=int(row["gc_orgID"]),
                harmonized_name=row["harmonized_name"],
                nom_harmonise=row["nom_harmonisé"],
                abbreviation=row["abbreviation"],
                abreviation=row["abreviation"],
                infobaseID=row["infobaseID"],
                rg=row["rg"],
                ati=row["ati"],
                open_gov_ouvert=row["open_gov_ouvert"],
                pop=row["pop"],
                phoenix=row["phoenix"],
                website=row["website"],
                site_web=row["site_web"],
            )
            for row in reader
        ]


@cache
def _default_index() -> dict[int, Org]:
    return {o.gc_orgID: o for o in load_reference_standard()}


def lookup(gc_org_id: int) -> Org:
    """Return the ``Org`` for ``gc_org_id`` from the pinned snapshot."""
    return _default_index()[gc_org_id]
