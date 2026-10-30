"""Integration tests for the prod API.

Runs after every prod deploy and on a daily schedule. Expected values for the
alias sweep come from the CSVs in data/, so the checked-out ref should match
what is deployed. Every check runs even if an earlier one fails;
the script exits non-zero if any failed.

Usage:
    BASE_URL=https://gcorgs.cdssandbox.xyz uv run python tests/integration_api.py
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Collection
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ALIASES_CSV = DATA_DIR / "gc_org_aliases.csv"
CONCORDANCE_CSV = DATA_DIR / "gc_concordance.csv"

USER_AGENT = "gcorg-resolver-integration-test"
REQUEST_TIMEOUT_SECONDS = 15
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

# Measured on the first request, so this includes any Lambda cold start
HEALTH_MAX_SECONDS = 5

# Matches MAX_NAMES in app.py
RESOLVE_BATCH_SIZE = 1000

MAX_REPORTED_MISMATCHES = 10


class CheckFailed(Exception):
    pass


@dataclass(frozen=True)
class Response:
    status: int
    content_type: str
    body: bytes
    elapsed: float

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self):
        return json.loads(self.body)


class Api:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, params: dict[str, str] | None = None) -> Response:
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return self._send(urllib.request.Request(url, method="GET"))

    def post_json(self, path: str, payload) -> Response:
        return self.post_raw(path, json.dumps(payload).encode("utf-8"))

    def post_raw(self, path: str, body: bytes) -> Response:
        req = urllib.request.Request(
            self.base_url + path,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        return self._send(req)

    def _send(self, req: urllib.request.Request) -> Response:
        req.add_header("User-Agent", USER_AGENT)
        # Only network-level failures are retried. An HTTP error status is a
        # real answer from the API and is returned for the check to judge.
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            start = time.monotonic()
            try:
                with urllib.request.urlopen(
                    req, timeout=REQUEST_TIMEOUT_SECONDS
                ) as resp:
                    body = resp.read()
                    return Response(
                        resp.status,
                        resp.headers.get("Content-Type", ""),
                        body,
                        time.monotonic() - start,
                    )
            except urllib.error.HTTPError as e:
                body = e.read()
                return Response(
                    e.code,
                    e.headers.get("Content-Type", ""),
                    body,
                    time.monotonic() - start,
                )
            except urllib.error.URLError, TimeoutError:
                if attempt == RETRY_ATTEMPTS:
                    raise
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        raise AssertionError("unreachable")


CHECKS: list[tuple[str, Callable[[Api], None]]] = []


def check(name: str):
    def register(fn: Callable[[Api], None]) -> Callable[[Api], None]:
        CHECKS.append((name, fn))
        return fn

    return register


def expect(actual, expected, what: str) -> None:
    if actual != expected:
        raise CheckFailed(f"{what}: expected {expected!r}, got {actual!r}")


def report_mismatches(mismatches: list[str], total: int) -> None:
    if not mismatches:
        return
    shown = "\n    ".join(mismatches[:MAX_REPORTED_MISMATCHES])
    more = len(mismatches) - MAX_REPORTED_MISMATCHES
    suffix = f"\n    ... and {more} more" if more > 0 else ""
    raise CheckFailed(f"{len(mismatches)} of {total} wrong:\n    {shown}{suffix}")


def load_names_by_id() -> dict[int, tuple[str, str]]:
    """Map each gc_orgID in the concordance to its (English, French) name."""
    with CONCORDANCE_CSV.open(encoding="utf-8-sig", newline="") as f:
        return {
            int(row["gc_orgID"]): (row["harmonized_name"], row["nom_harmonisé"])
            for row in csv.DictReader(f)
        }


def load_expected_aliases(known_ids: Collection[int]) -> list[tuple[str, int | None]]:
    # Aliases for orgs absent from the concordance, and ambiguous aliases
    # (gc_orgID 0), must come back unmatched
    with ALIASES_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        (row["name"], gc_org_id if gc_org_id in known_ids else None)
        for row in rows
        for gc_org_id in [int(row["gc_orgID"])]
    ]


# Health and response time. Registered first so it absorbs any cold start.


@check("GET /health returns ok within the time limit")
def health(api: Api) -> None:
    r = api.get("/health")
    expect(r.status, 200, "status")
    expect(r.json(), {"status": "ok"}, "body")
    if r.elapsed > HEALTH_MAX_SECONDS:
        raise CheckFailed(f"took {r.elapsed:.1f}s (limit {HEALTH_MAX_SECONDS}s)")


@check("GET /.well-known/security.txt is plain text")
def security_txt(api: Api) -> None:
    r = api.get("/.well-known/security.txt")
    expect(r.status, 200, "status")
    if not r.content_type.startswith("text/plain"):
        raise CheckFailed(f"content type is {r.content_type!r}")


# POST /resolve


@check("POST /resolve: exact name, acronym and no-match in one batch")
def resolve_post_mixed_batch(api: Api) -> None:
    names = ["Bibliothèque et Archives Canada", "CRA", "Department of Unicorns"]
    r = api.post_json("/resolve", {"names": names})
    expect(r.status, 200, "status")
    results = r.json()["results"]
    expect([row["gc_orgID"] for row in results], [2262, 2303, None], "gc_orgIDs")
    expect([row["matched"] for row in results], [True, True, False], "matched")


@check("POST /resolve: non-string names are unmatched rather than a 500")
def resolve_post_non_strings(api: Api) -> None:
    r = api.post_json("/resolve", {"names": [123, None, {"a": 1}, ["CRA"], "CRA"]})
    expect(r.status, 200, "status")
    results = r.json()["results"]
    expect(
        [row["matched"] for row in results],
        [False, False, False, False, True],
        "matched",
    )


BAD_RESOLVE_BODIES: list[tuple[str, bytes]] = [
    ("malformed JSON", b"{not json"),
    ("a JSON array instead of an object", b'["CRA"]'),
    ("a missing names key", b'{"name": "CRA"}'),
    ("names that is a string", b'{"names": "CRA"}'),
    ("an empty names list", b'{"names": []}'),
    (
        f"more than {RESOLVE_BATCH_SIZE} names",
        json.dumps({"names": ["CRA"] * (RESOLVE_BATCH_SIZE + 1)}).encode(),
    ),
]

for label, body in BAD_RESOLVE_BODIES:

    @check(f"POST /resolve rejects {label} with 400")
    def resolve_post_bad_body(api: Api, body: bytes = body) -> None:
        expect(api.post_raw("/resolve", body).status, 400, "status")


# Every org in the concordance has at least one alias, so this also checks
# every org's English and French names
@check("POST /resolve: every alias resolves to its expected org and names")
def resolve_post_every_alias(api: Api) -> None:
    names_by_id = load_names_by_id()
    expected = load_expected_aliases(names_by_id.keys())
    mismatches = []
    for start in range(0, len(expected), RESOLVE_BATCH_SIZE):
        batch = expected[start : start + RESOLVE_BATCH_SIZE]
        r = api.post_json("/resolve", {"names": [name for name, _ in batch]})
        expect(r.status, 200, f"status for batch starting at row {start}")
        results = r.json()["results"]
        expect(len(results), len(batch), f"result count for batch at row {start}")
        for (name, want), got in zip(batch, results, strict=True):
            if got["gc_orgID"] != want or got["matched"] != (want is not None):
                mismatches.append(f"{name!r}: expected {want}, got {got['gc_orgID']}")
                continue
            if want is None:
                continue
            want_names = names_by_id[want]
            got_names = (got["harmonized_name"], got["nom_harmonise"])
            if got_names != want_names:
                mismatches.append(
                    f"{name!r} ({want}): expected names {want_names}, got {got_names}"
                )
    report_mismatches(mismatches, len(expected))


# GET endpoints with plain-text responses: (label, path, params, status, body).
# A body of None means only the status is checked.
GET_TEXT_CASES: list[tuple[str, str, dict[str, str], int, str | None]] = [
    # GET /resolve
    ("exact name", "/resolve", {"name": "Agriculture"}, 200, "2222"),
    (
        "misspelt name via fuzzy matching",
        "/resolve",
        {"name": "Canada Ecomomic Development for Quebec Regions"},
        200,
        "2257",
    ),
    ("ambiguous acronym is unmatched", "/resolve", {"name": "MPO"}, 200, ""),
    (
        "unknown name is unmatched",
        "/resolve",
        {"name": "Department of Unicorns"},
        200,
        "",
    ),
    ("missing name is rejected", "/resolve", {}, 400, None),
    # GET /name: fields
    (
        "English name",
        "/name",
        {"gc_orgID": "2222", "lang": "en"},
        200,
        "Agriculture and Agri-Food Canada",
    ),
    (
        "French name",
        "/name",
        {"gc_orgID": "2222", "lang": "fr"},
        200,
        "Agriculture et Agroalimentaire Canada",
    ),
    (
        "English abbreviation",
        "/name",
        {"gc_orgID": "2222", "lang": "en", "field": "abbreviation"},
        200,
        "AAFC",
    ),
    (
        "French abbreviation",
        "/name",
        {"gc_orgID": "2222", "lang": "fr", "field": "abbreviation"},
        200,
        "AAC",
    ),
    (
        "English legal title",
        "/name",
        {"gc_orgID": "2222", "lang": "en", "field": "legal_title"},
        200,
        "Department of Agriculture and Agri-Food",
    ),
    (
        "French legal title",
        "/name",
        {"gc_orgID": "2222", "lang": "fr", "field": "legal_title"},
        200,
        "Ministère de l’Agriculture et de l’Agroalimentaire",
    ),
    (
        "org with no abbreviation returns an empty body",
        "/name",
        {"gc_orgID": "2270", "lang": "en", "field": "abbreviation"},
        200,
        "",
    ),
    # GET /name: accepted parameter variants
    (
        "lang=english",
        "/name",
        {"gc_orgID": "2222", "lang": "english"},
        200,
        "Agriculture and Agri-Food Canada",
    ),
    (
        "lang=français",
        "/name",
        {"gc_orgID": "2222", "lang": "français"},
        200,
        "Agriculture et Agroalimentaire Canada",
    ),
    (
        "lang=FR is case-insensitive",
        "/name",
        {"gc_orgID": "2222", "lang": "FR"},
        200,
        "Agriculture et Agroalimentaire Canada",
    ),
    (
        "GC_ORGID parameter name is case-insensitive",
        "/name",
        {"GC_ORGID": "2222", "lang": "en"},
        200,
        "Agriculture and Agri-Food Canada",
    ),
    (
        "field=nom synonym",
        "/name",
        {"gc_orgID": "2222", "lang": "fr", "field": "nom"},
        200,
        "Agriculture et Agroalimentaire Canada",
    ),
    (
        "field=abreviation synonym",
        "/name",
        {"gc_orgID": "2222", "lang": "fr", "field": "abreviation"},
        200,
        "AAC",
    ),
    (
        "field=appellation_légale synonym",
        "/name",
        {"gc_orgID": "2222", "lang": "fr", "field": "appellation_légale"},
        200,
        "Ministère de l’Agriculture et de l’Agroalimentaire",
    ),
    # GET /name: errors
    (
        "misspelt field is rejected",
        "/name",
        {"gc_orgID": "2222", "lang": "en", "field": "abbrevation"},
        400,
        None,
    ),
    ("missing gc_orgID is rejected", "/name", {"lang": "en"}, 400, None),
    (
        "non-integer gc_orgID is rejected",
        "/name",
        {"gc_orgID": "abc", "lang": "en"},
        400,
        None,
    ),
    ("missing lang is rejected", "/name", {"gc_orgID": "2222"}, 400, None),
    (
        "unknown lang is rejected",
        "/name",
        {"gc_orgID": "2222", "lang": "de"},
        400,
        None,
    ),
    (
        "unknown gc_orgID is not found",
        "/name",
        {"gc_orgID": "999999", "lang": "en"},
        404,
        None,
    ),
]

for label, path, params, status, want in GET_TEXT_CASES:

    @check(f"GET {path}: {label}")
    def get_text_case(
        api: Api,
        path: str = path,
        params: dict[str, str] = params,
        status: int = status,
        want: str | None = want,
    ) -> None:
        r = api.get(path, params)
        expect(r.status, status, "status")
        if want is not None:
            expect(r.text, want, "body")


def main() -> int:
    base_url = os.environ.get("BASE_URL", "")
    if not base_url:
        print("BASE_URL is required")
        return 1

    print(f"Testing {base_url}")
    api = Api(base_url)
    failed = []
    for name, fn in CHECKS:
        try:
            fn(api)
        except (urllib.error.URLError, TimeoutError) as e:
            # Unreachable even after retries: every remaining check would just
            # wait out its own timeouts, so stop here
            failed.append(name)
            print(f"FAIL  {name}\n    API unreachable: {e}")
            print("Skipping remaining checks")
            return 1
        # One broken check shouldn't stop the rest from running
        except Exception as e:  # noqa: BLE001
            failed.append(name)
            print(f"FAIL  {name}\n    {e}")
        else:
            print(f"PASS  {name}")

    print(f"\n{len(CHECKS) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
