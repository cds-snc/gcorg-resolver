"""Fetch CloudWatch metrics for the gcorg-resolver Lambda incrementally, store one row per day in a CSV.

Steps:
1. Determine the fetch range:
   - First run (no CSV): backfill from DEFAULT_BACKFILL_START through yesterday.
   - Subsequent runs: re-fetch from the last date already in the CSV (in case that
     day was still in progress) through yesterday, then merge into existing rows.
2. Pull five metrics from CloudWatch at daily granularity:
   Invocations, Errors, Throttles, Duration (average), ConcurrentExecutions (max).
3. Write one row per complete day to data/lambda_usage_{env}.csv.

Usage:
    python data/lambda_usage.py --env prod

"""

import argparse
import csv
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

# Each entry: (CloudWatch MetricName, Statistic, column name in CSV)
METRICS = [
    ("Invocations", "Sum", "invocations"),
    ("Errors", "Sum", "errors"),
    ("Throttles", "Sum", "throttles"),
    ("Duration", "Average", "duration_avg_ms"),
    ("ConcurrentExecutions", "Maximum", "concurrent_max"),
]

ONE_DAY_SECONDS = 86400

# Default start date used when no existing CSV is found.
DEFAULT_BACKFILL_START = date(2026, 4, 1)  # 2026-Apr-01

# Output directory for CSV files.
OUTPUT_DIR = Path(__file__).parent

# AWS region for CloudWatch metrics.
AWS_REGION = "ca-central-1"


# ---------------------------------------------------------------------------
# CloudWatch helpers
# ---------------------------------------------------------------------------


def fetch_daily_metric(
    cw_client,
    function_name: str,
    metric_name: str,
    stat: str,
    start: date,
    end: date,
) -> dict[date, float]:
    """Return a mapping of date -> value for a single CloudWatch metric."""
    start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    # CloudWatch end time is exclusive; advance one day past the last requested day.
    end_dt = datetime(end.year, end.month, end.day, tzinfo=timezone.utc) + timedelta(
        days=1
    )

    response = cw_client.get_metric_statistics(
        Namespace="AWS/Lambda",
        MetricName=metric_name,
        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
        StartTime=start_dt,
        EndTime=end_dt,
        Period=ONE_DAY_SECONDS,
        Statistics=[stat],
    )

    return {dp["Timestamp"].date(): dp[stat] for dp in response["Datapoints"]}


def fetch_all_metrics(
    cw_client,
    function_name: str,
    start: date,
    end: date,
) -> list[dict]:
    """Return a list of dicts, one per day in [start, end], with all metric columns."""
    # Fetch each metric independently; CloudWatch returns only days with data.
    raw: dict[str, dict[date, float]] = {}
    for metric_name, stat, col in METRICS:
        raw[col] = fetch_daily_metric(
            cw_client, function_name, metric_name, stat, start, end
        )

    rows = []
    day = start
    while day <= end:
        row = {"date": day.isoformat()}
        for _, _, col in METRICS:
            # Days with zero activity are absent from CloudWatch; treat as 0.
            row[col] = raw[col].get(day, 0.0)
        rows.append(row)
        day += timedelta(days=1)

    return rows


# ---------------------------------------------------------------------------
# Incremental CSV helpers
# ---------------------------------------------------------------------------


def read_existing_csv(path: Path) -> list[dict]:
    """Return all rows from an existing CSV, or an empty list if the file doesn't exist."""
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def determine_fetch_range(existing_rows: list[dict]) -> tuple[date, date]:
    """Return (start, end) for the CloudWatch fetch.

    End is always yesterday -- today's data is still accumulating.
    Start is DEFAULT_BACKFILL_START on the first run, or the last recorded date
    so that a potentially-incomplete day gets re-fetched and overwritten.
    """
    end = date.today() - timedelta(days=1)
    if not existing_rows:
        return DEFAULT_BACKFILL_START, end
    last_date = date.fromisoformat(existing_rows[-1]["date"])
    return last_date, end


def merge_rows(existing_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    """Merge new daily rows into existing rows, overwriting any overlapping dates."""
    new_by_date = {r["date"]: r for r in new_rows}
    kept = [r for r in existing_rows if r["date"] not in new_by_date]
    merged = kept + new_rows
    merged.sort(key=lambda r: r["date"])
    return merged


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

CSV_COLUMNS = ["date"] + [col for _, _, col in METRICS]


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote CSV to {path} ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> str:
    """Parse CLI arguments and return the environment (dev or prod)."""
    parser = argparse.ArgumentParser(
        description=(
            "Incrementally fetch Lambda CloudWatch metrics to a daily CSV. "
            "On the first run, backfills from DEFAULT_BACKFILL_START. "
            "On subsequent runs, re-fetches from the last recorded date and appends new data."
        )
    )
    parser.add_argument(
        "--env",
        required=False,
        default="prod",
        choices=["dev", "prod"],
        help="Environment (dev or prod).",
    )
    args = parser.parse_args(argv)
    return args.env


def main(argv: list[str] | None = None) -> None:
    env = parse_args(argv)

    try:
        import boto3
    except ImportError:
        sys.exit(
            "boto3 is not installed. "
            "Install the metrics extras: uv pip install -e '.[metrics]'"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"lambda_usage_{env}"
    csv_path = OUTPUT_DIR / f"{stem}.csv"

    existing_rows = read_existing_csv(csv_path)
    start, end = determine_fetch_range(existing_rows)

    if start > end:
        print(f"CSV is already up to date through {end}. Nothing to fetch.")
        return

    function_name = f"gcorg-resolver-{env}"
    print(f"Fetching metrics for {function_name} ({start} to {end})")

    cw = boto3.client("cloudwatch", region_name=AWS_REGION)
    new_rows = fetch_all_metrics(cw, function_name, start, end)

    # Cast metric values fetched from CloudWatch to float so they round-trip
    # through the CSV consistently with rows loaded from disk (which are strings).
    for row in new_rows:
        for _, _, col in METRICS:
            row[col] = float(row[col])

    all_rows = merge_rows(existing_rows, new_rows)
    write_csv(all_rows, csv_path)


if __name__ == "__main__":
    main()
