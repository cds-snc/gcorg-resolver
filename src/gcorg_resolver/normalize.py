"""Normalize Government of Canada organization names for robust matching.

Originally ported from the ``normalize_name`` function in the CDS R package
(https://www.github.com/cds-snc/data-r-functions-for-cds), then extended.

Pipeline steps (in order):

1. Lowercase
2. Strip diacritics (Latin-ASCII via unidecode)
3. If the input is an email address, extract the registrable domain
4. Strip trailing abbreviation dots (e.g. "St." -> "St")
5. Remove "Canada" as a standalone token (anywhere in the string),
   including "of Canada" / "du Canada" / "au Canada"
6. Remove English/French adjective forms: "Canadian", "canadien(ne)(s)"
7. Strip "Office of the" / "Bureau du/de la/d'" prefixes
8. Strip trailing "Inc" / "Inc."
9. Fix common agency/department/ministry typos
10. Strip leading or trailing "Department"/"Ministère" affixes
11. Drop prepositions and articles (the, of, and, du, de, des, etc.)
12. Replace non-critical punctuation with a space
13. Collapse whitespace
"""

import re

from unidecode import unidecode

# Match "canada" as a standalone token anywhere in the string, optionally
# preceded by "of " / "au " / "du ". Token boundaries are space or
# string-boundary — crucially NOT the regex \b, because that would also
# match "canada" inside domains like ``fintrac-canafe.canada.ca``.
CANADA_ANY = re.compile(r"(?:^|\s)(?:of |au |du )?canada(?=\s|$)")

# Match English and French adjective forms on a token boundary:
# canadian, canadien, canadiens, canadienne, canadiennes. We don't have
# to worry about accents because we've already stripped them
CANADIAN_ADJ = re.compile(r"(?:^|\s)canad(?:ian|ien|iens|ienne|iennes)(?=\s|$)")

# Strip "Office of the" / "Bureau du" / "Bureau de la" / "Bureau d'" when
# they appear as a prefix on org names (e.g. "Office of the Auditor General"
# -> "Auditor General").
OFFICE_PREFIX = re.compile(r"^(?:office of the|bureau du|bureau de la|bureau d')\s+")

# Strip a trailing "Inc" or "Inc." preceded by whitespace (e.g. "Acme Inc."
# -> "Acme"). The leading \s+ ensures we don't chew into a word ending in
# "inc"; the optional dot handles both punctuated and unpunctuated forms.
INC_TRAILING = re.compile(r"\s+inc\.?$")


# Strip leading/trailing English/French department/ministry nouns.
# Prepositions/articles such as "of", "de la", "du", "d'", etc. are removed
# later by PREPOSITIONS, so we intentionally do not match them here.
DEPARTMENT_AFFIX = re.compile(
    r"^\s*(?:department|ministere)\s+|\s+(?:department|ministere)\s*$"
)


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
# We intentially don't correct "Ministre" so as to leave "Premier Ministre" intact
TYPO_AGENCY = re.compile(r"agnecy|agancy|agincy|agensey|ageny")
TYPO_DEPARTMENT = re.compile(r"deprtment|departmant|deparment|depatment")
TYPO_MINISTERE = re.compile(r"minstere|mnistere|ministaire")

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
    o = CANADIAN_ADJ.sub(" ", o)
    o = OFFICE_PREFIX.sub("", o)
    o = INC_TRAILING.sub("", o)
    o = TYPO_AGENCY.sub("agency", o)
    o = TYPO_DEPARTMENT.sub("department", o)
    o = TYPO_MINISTERE.sub("ministere", o)
    o = DEPARTMENT_AFFIX.sub("", o)
    o = PREPOSITIONS.sub(r"\1", o)
    o = PUNCTUATION.sub(" ", o)
    o = WHITESPACE.sub(" ", o).strip()
    return o
