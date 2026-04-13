"""Normalize Government of Canada organization names for robust matching.

Originally ported from the ``normalize_name`` function in the CDS R package
(https://www.github.com/cds-snc/data-r-functions-for-cds), then extended.

Pipeline steps (in order):

1. Lowercase
2. Strip diacritics (Latin-ASCII via unidecode)
3. If the input is an email address, extract the registrable domain
4. Strip trailing abbreviation dots (e.g. "St." -> "St")
5. Remove "of Canada" / "du Canada" / "au Canada" and trailing "Canada"
6. Strip "Office of the" / "Bureau du/de la/d'" prefixes
7. Remove any trailing "Canada" revealed by step 6
8. Strip trailing "Inc" / "Inc."
9. Drop prepositions and articles (the, of, and, du, de, des, etc.)
10. Replace non-critical punctuation with a space
11. Collapse whitespace
12. Fix common agency/department typos
"""

import re
from unidecode import unidecode

CANADA_ANY = re.compile(r"(of canada)|(au canada)|(du canada)|( canada )|( canada$)")
OFFICE_PREFIX = re.compile(r"(office of the)|(bureau du)|(bureau de la)|(bureau d')")
CANADA_TRAILING = re.compile(r"( of canada$)|( au canada$)|( du canada$)|( canada$)")
INC_TRAILING = re.compile(r"\s+inc\.?$")


# Match a preposition/article that sits on its own as a word — i.e. with a
# space or string boundary on each side. The leading boundary is captured so
# the substitution can put it back (\1), which keeps adjacent words from
# colliding. d' and l' are handled separately since their right-hand
# boundary is the apostrophe itself, not a space.
PREPOSITIONS = re.compile(
    r"(^| )(?:(?:the|of|and|du|de|des|le|la|les|et|aux|au|a)(?= |$)|[dl]')"
)

# Strip periods that trail an abbreviation — i.e. a period followed by
# whitespace or end of string (e.g. "St." → "St", "Intl." → "Intl").
# Domain periods like "agr.gc.ca" are always followed by more characters
# so they are left untouched.
ABBREV_DOTS = re.compile(r"\.(?=\s|$)")

# Strip any punctuation or whitespace wider than a single space
PUNCTUATION = re.compile(r"[/()&',\":]")
WHITESPACE = re.compile(r"\s+")

# Fix some common typos
TYPO_AGENCY = re.compile(r"agnecy|agancy|agincy|agensey|ageny")
TYPO_DEPARTMENT = re.compile(r"deprtment|departmant|deparment|depatment")

# If the input is an email address, strip the local part (before @) and any
# subdomains, keeping only the registrable domain. GC orgs live under .gc.ca
# or .canada.ca (3-part domains); everything else uses 2 parts (.ca, .com).
EMAIL = re.compile(r"^[^@\s]+@(.+)$")
GC_SUFFIXES = (".gc.ca", ".canada.ca")

def extract_domain(s: str) -> str:
    m = EMAIL.match(s)
    if not m:
        return s
    domain = m.group(1)
    parts = domain.split(".")
    for suffix in GC_SUFFIXES:
        if domain.endswith(suffix):
            return ".".join(parts[-3:]) if len(parts) > 3 else domain
    return ".".join(parts[-2:]) if len(parts) > 2 else domain


def normalize(s: str) -> str:
    """Return a normalized form of an organization name suitable for matching."""
    o = s.lower()
    o = unidecode(o)
    o = extract_domain(o)
    o = ABBREV_DOTS.sub("", o)
    o = CANADA_ANY.sub(" ", o)
    o = OFFICE_PREFIX.sub("", o)
    o = CANADA_TRAILING.sub("", o)
    o = INC_TRAILING.sub("", o)
    o = PREPOSITIONS.sub(r"\1", o)
    o = PUNCTUATION.sub(" ", o)
    o = WHITESPACE.sub(" ", o).strip()
    o = TYPO_AGENCY.sub("agency", o)
    o = TYPO_DEPARTMENT.sub("department", o)
    return o
