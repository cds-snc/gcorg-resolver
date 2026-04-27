"""Download a fresh copy of the GC Organizations Reference Standard.

Run manually when we want to refresh the pinned snapshot:

    python data/download_reference_standard.py

Source: https://open.canada.ca/data/en/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5
"""

from pathlib import Path
from urllib.request import urlopen

URL = (
    "https://open.canada.ca/data/dataset/"
    "57180b36-3428-4a7f-afe3-2161a6b44ec5/resource/"
    "3faaafb4-00e2-4303-947d-ac786b62559f/download/gc_concordance.csv"
)

OUT_PATH = Path(__file__).parent / "gc_concordance.csv"


if __name__ == "__main__":
    print(f"Fetching {URL}")
    with urlopen(URL) as response:
        body = response.read()
    OUT_PATH.write_bytes(body)
    print(f"Wrote {len(body):,} bytes to {OUT_PATH}")
