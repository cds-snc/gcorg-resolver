"""Download fresh copies of the GC Organizations Reference Standard.

Run nightly by update-reference-data.yml, or by hand:

    python data/download_reference_standard.py

Steps:
1. Fetch every resource, retrying transient network failures.
2. Validate each payload's columns and row count.
3. Write the files, only once every resource has passed.

Source: https://open.canada.ca/data/en/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5
"""

import csv
import io
import sys
import time
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

BASE = (
    "https://open.canada.ca/data/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5/resource/"
)

HERE = Path(__file__).parent

# (url, output path, columns the app reads)
RESOURCES = [
    (
        BASE + "3faaafb4-00e2-4303-947d-ac786b62559f/download/gc_concordance.csv",
        HERE / "gc_concordance.csv",
        {
            "gc_orgID",
            "harmonized_name",
            "nom_harmonisé",
            "abbreviation",
            "abreviation",
            "infobaseID",
            "rg",
            "ati",
            "open_gov_ouvert",
            "pop",
            "phoenix",
            "website",
            "site_web",
        },
    ),
    (
        BASE + "cb5b5566-f599-4d12-abae-8279a0230928/download/gc_org_info.csv",
        HERE / "gc_org_info.csv",
        {"gc_orgID", "legal_title", "appellation_légale"},
    ),
]

# The download endpoint can take over 50s to send its first byte
TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5

# Real upstream releases have shrunk by up to 9%; a bigger drop than this
# means a truncated or broken download.
MIN_ROW_FRACTION = 0.8


class DownloadError(Exception):
    pass


def fetch_with_retry(url: str) -> bytes:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urlopen(url, timeout=TIMEOUT_SECONDS) as response:
                return response.read()
        except HTTPError as exc:
            # A 4xx won't fix itself on retry
            if exc.code < 500 or attempt == MAX_ATTEMPTS:
                raise DownloadError(f"HTTP {exc.code} from {url}") from exc
            reason = f"HTTP {exc.code}"
        # Read timeouts raise a bare TimeoutError, not URLError, so catch OSError.
        # HTTPException covers truncated responses (IncompleteRead).
        except (OSError, HTTPException) as exc:
            if attempt == MAX_ATTEMPTS:
                raise DownloadError(
                    f"{url} unreachable after {MAX_ATTEMPTS} attempts ({exc!r})"
                ) from exc
            reason = repr(exc)
        delay = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
        print(f"Attempt {attempt} failed ({reason}); retrying in {delay}s...")
        time.sleep(delay)
    raise AssertionError("unreachable")


def count_rows(body: bytes) -> tuple[list[str], int]:
    """Return the header and the number of data rows in a CSV payload."""
    reader = csv.reader(io.StringIO(body.decode("utf-8-sig")))
    header = next(reader, [])
    return header, sum(1 for _ in reader)


def validate(body: bytes, out_path: Path, required_columns: set[str]) -> None:
    try:
        header, n_rows = count_rows(body)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise DownloadError(f"{out_path.name} is not a readable CSV ({exc})") from exc
    missing = required_columns - set(header)
    if missing:
        raise DownloadError(f"{out_path.name} is missing columns {sorted(missing)}")
    if out_path.exists():
        _, current_rows = count_rows(out_path.read_bytes())
        if n_rows < current_rows * MIN_ROW_FRACTION:
            raise DownloadError(
                f"{out_path.name} shrank from {current_rows} to {n_rows} rows"
            )


def main() -> int:
    bodies = []
    try:
        for url, out_path, required_columns in RESOURCES:
            print(f"Fetching {url}")
            body = fetch_with_retry(url)
            validate(body, out_path, required_columns)
            bodies.append((out_path, body))
    except DownloadError as exc:
        print(f"::error::{exc}. Keeping the existing snapshots.", file=sys.stderr)
        return 1

    # Write only after every resource passed, so the snapshots never disagree
    for out_path, body in bodies:
        out_path.write_bytes(body)
        print(f"Wrote {len(body):,} bytes to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
