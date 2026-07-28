"""Download fresh copies of the GC Organizations Reference Standard.

Run manually when we want to refresh the pinned snapshots:

    python data/download_reference_standard.py

Source: https://open.canada.ca/data/en/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5
"""

import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

_BASE = (
    "https://open.canada.ca/data/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5/resource/"
)

RESOURCES = [
    (
        _BASE + "3faaafb4-00e2-4303-947d-ac786b62559f/download/gc_concordance.csv",
        Path(__file__).parent / "gc_concordance.csv",
    ),
    (
        _BASE + "cb5b5566-f599-4d12-abae-8279a0230928/download/gc_org_info.csv",
        Path(__file__).parent / "gc_org_info.csv",
    ),
]

TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5


def fetch_with_retry(url: str) -> bytes:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urlopen(url, timeout=TIMEOUT_SECONDS) as response:
                return response.read()
        except URLError as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(f"Attempt {attempt} failed ({exc}); retrying in {delay}s...")
            time.sleep(delay)


if __name__ == "__main__":
    for url, out_path in RESOURCES:
        print(f"Fetching {url}")
        body = fetch_with_retry(url)
        out_path.write_bytes(body)
        print(f"Wrote {len(body):,} bytes to {out_path}")
