"""Fetch the last 30 days of this account's AWS costs from Cost Explorer, split by project and grouped into plain-language categories.

The 30 days are whole UTC days ending yesterday. The account serves three
projects, each tagged with its own CostCentre: gcorg-resolver, and the program
code and service inventory lookups. Everything without one of those tags is
the shared account baseline (policy-required security services, tax), which
serves all three, so it gets its own group rather than being split.

Steps:
1. Work out the dates of the last 30 days.
2. For each group, fetch its line items from Cost Explorer, grouped by service
   and usage type. Cost Explorer allows only two GroupBy keys, so each group is
   a separate filtered request.
3. Sort each group's line items into categories (Serving requests, Security,
   Queries, Monitoring, Storage, Everything else), dropping any that round to
   zero. Items in Everything else at or above OTHER_DETAIL_MIN are listed by
   name; the rest are summed as Smaller items.
4. Write each group's total and lines, then a grand total, to
   data/aws_costs.csv for the usage dashboard.

Usage:
    python data/get_aws_costs.py [YYYY-MM-DD]

"""

import argparse
import csv
import datetime
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import groupby
from pathlib import Path

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

# Length of the reporting period, in days.
PERIOD_DAYS = 30

COST_CENTRE_TAG = "CostCentre"

RESOLVER = "GC Organization Name Resolution API"
PROGRAM_CODE = "Program code lookup"
SERVICE_INVENTORY = "Service inventory lookup"
SHARED = "Shared account costs"

# CostCentre tag values. gcorg-resolver's matches billing_tag_value in
# infra/env/*/terraform.tfvars; the lookups' live in the service-inventory-lookup
# repo.
PROJECT_TAGS = {
    RESOLVER: "GCOrgResolver",
    PROGRAM_CODE: "program-code-lookup",
    SERVICE_INVENTORY: "service-inventory-lookup",
}

# Items in Everything else at or above this many dollars are listed by name.
OTHER_DETAIL_MIN = Decimal(1)

SERVING = "Serving requests"
SECURITY = "Security"
QUERIES = "Queries"
MONITORING = "Monitoring"
STORAGE = "Storage"
OTHER = "Everything else"
SMALLER_ITEMS = "Smaller items"

# What each API response costs: the request path through CloudFront, WAF,
# API Gateway and Lambda, plus the DNS lookup. WAF's fixed web ACL and rule
# fees stay in Security.
SERVING_USAGE = re.compile(r"RequestV2|DNS-Queries")
SERVING_SERVICE = re.compile(r"Lambda|API Gateway|CloudFront")
SECURITY_USAGE = re.compile(r"NatGateway|PublicIPv4|ElasticIP")
SECURITY_SERVICE = re.compile(
    r"Virtual Private Cloud|GuardDuty|Security Hub|Config|CloudTrail"
    r"|Key Management|Secrets Manager|Inspector|Macie|WAF|Shield|Detective"
)
QUERIES_SERVICE = re.compile(r"Athena|Glue")
MONITORING_SERVICE = re.compile(r"CloudWatch")
# EBS disks also hide under "EC2 - Other".
STORAGE_USAGE = re.compile(r"EBS:")
STORAGE_SERVICE = re.compile(r"Simple Storage Service|Backup|Elastic File System")

DATA_TRANSFER_USAGE = re.compile(r"DataTransfer")
SERVICE_PREFIX = re.compile(r"^(Amazon|AWS) ?")

# Checked in order; the first match wins, so Serving comes before Security to
# claim WAF's per-request charges. Anything unmatched, sales tax included, is
# Everything else.
CATEGORY_RULES: list[tuple[str, re.Pattern[str] | None, re.Pattern[str] | None]] = [
    (SERVING, SERVING_SERVICE, SERVING_USAGE),
    (SECURITY, SECURITY_SERVICE, SECURITY_USAGE),
    (QUERIES, QUERIES_SERVICE, None),
    (MONITORING, MONITORING_SERVICE, None),
    (STORAGE, STORAGE_SERVICE, STORAGE_USAGE),
]

# Friendlier names for services that land in Everything else.
ITEM_NAMES = {
    "Tax": "Sales tax",
}

# Finer than cents so per-request costs of a fraction of a cent still show.
PRECISION = Decimal("0.0001")

# Output path for the CSV.
CSV_PATH = Path(__file__).parent / "aws_costs.csv"

# Cost Explorer only has a us-east-1 endpoint.
AWS_REGION = "us-east-1"


@dataclass(frozen=True)
class Period:
    start: date
    end: date  # exclusive, as Cost Explorer expects


@dataclass(frozen=True)
class LineItem:
    service: str
    usage_type: str
    amount: Decimal
    unit: str

    @property
    def category(self) -> str:
        return category(self.service, self.usage_type)

    @property
    def item(self) -> str:
        return item_name(self.service, self.usage_type)


@dataclass(frozen=True)
class Line:
    kind: str  # total, category, other, detail or rest
    name: str
    amount: Decimal


def category(service: str, usage_type: str) -> str:
    for name, service_pattern, usage_pattern in CATEGORY_RULES:
        if usage_pattern and usage_pattern.search(usage_type):
            return name
        if service_pattern and service_pattern.search(service):
            return name
    return OTHER


def item_name(service: str, usage_type: str) -> str:
    if DATA_TRANSFER_USAGE.search(usage_type):
        return "Data transfer"
    return ITEM_NAMES.get(service, SERVICE_PREFIX.sub("", service))


def last_30_days(today: date) -> Period:
    """The 30 whole days before today."""
    return Period(today - timedelta(days=PERIOD_DAYS), today)


def tag_filter(values: list[str]) -> dict:
    return {"Tags": {"Key": COST_CENTRE_TAG, "Values": values}}


def group_filters() -> list[tuple[str, dict]]:
    """Each table group and its Cost Explorer filter, in display order.

    The shared group is "none of the project tags", so untagged resources and
    stray tag values both land there and the groups always add up to the bill.
    """
    groups = [(name, tag_filter([tag])) for name, tag in PROJECT_TAGS.items()]
    groups.append((SHARED, {"Not": tag_filter(list(PROJECT_TAGS.values()))}))
    return groups


# ---------------------------------------------------------------------------
# Cost Explorer
# ---------------------------------------------------------------------------


def fetch(client, period: Period, cost_filter: dict) -> list[LineItem]:
    """Every line item for the period, following pagination.

    A period that crosses a month boundary comes back as two results; the
    summing below adds them together.
    """
    items: list[LineItem] = []
    token = None
    while True:
        kwargs = {
            "TimePeriod": {
                "Start": period.start.isoformat(),
                "End": period.end.isoformat(),
            },
            "Granularity": "MONTHLY",
            "Metrics": ["UnblendedCost"],
            "Filter": cost_filter,
            "GroupBy": [
                {"Type": "DIMENSION", "Key": "SERVICE"},
                {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
            ],
        }
        if token:
            kwargs["NextPageToken"] = token
        page = client.get_cost_and_usage(**kwargs)
        for result in page["ResultsByTime"]:
            for group in result["Groups"]:
                cost = group["Metrics"]["UnblendedCost"]
                service, usage_type = group["Keys"]
                items.append(
                    LineItem(service, usage_type, Decimal(cost["Amount"]), cost["Unit"])
                )
        token = page.get("NextPageToken")
        if not token:
            return items


# ---------------------------------------------------------------------------
# Table lines
# ---------------------------------------------------------------------------


def total(items: list[LineItem], keep=lambda item: True) -> Decimal:
    return sum((item.amount for item in items if keep(item)), Decimal(0))


def sum_by(items: list[LineItem], key) -> list[tuple[str, Decimal]]:
    """Amounts summed per key, largest first, ties in name order."""
    ordered = sorted(items, key=key)
    sums = [(name, total(list(group))) for name, group in groupby(ordered, key=key)]
    return sorted(sums, key=lambda pair: -pair[1])


def build_lines(
    items: list[LineItem], detail_min: Decimal = OTHER_DETAIL_MIN
) -> list[Line]:
    """Every candidate line of the table, in order."""

    def is_other(item: LineItem) -> bool:
        return item.category == OTHER

    main = [item for item in items if not is_other(item)]
    lines = [
        Line("category", name, amount)
        for name, amount in sum_by(main, lambda i: i.category)
    ]

    other = total(items, is_other)
    lines.append(Line("other", OTHER, other))

    details = [
        (name, amount)
        for name, amount in sum_by([i for i in items if is_other(i)], lambda i: i.item)
        if amount >= detail_min
    ]
    lines.extend(Line("detail", name, amount) for name, amount in details)
    lines.append(
        Line("rest", SMALLER_ITEMS, other - sum((a for _, a in details), Decimal(0)))
    )

    return lines


def shown(amount: Decimal) -> bool:
    """Anything that rounds to zero only adds noise."""
    return amount.quantize(PRECISION, ROUND_HALF_UP) != 0


def visible_lines(items: list[LineItem]) -> list[Line]:
    """The lines worth showing, in order, starting with the total."""
    visible = [Line("total", "Total", total(items))]
    other_shown = False
    details_shown = False

    for line in build_lines(items):
        if line.kind in ("category", "other") and shown(line.amount):
            other_shown = other_shown or line.kind == "other"
            visible.append(line)
        elif line.kind == "detail" and other_shown:
            details_shown = True
            visible.append(line)
        # Without a named item above it, "Smaller items" would just repeat Everything else.
        elif line.kind == "rest" and details_shown and shown(line.amount):
            visible.append(line)

    return visible


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

CSV_COLUMNS = ["period_start", "period_end", "group", "kind", "name", "amount", "unit"]


def grand_total(groups: list[tuple[str, list[Line]]]) -> Line:
    """Sum of the group totals (each group's first line)."""
    return Line(
        "grand_total",
        "Total",
        sum((lines[0].amount for _, lines in groups), Decimal(0)),
    )


def write_csv(
    period: Period, groups: list[tuple[str, list[Line]]], unit: str, path: Path
) -> None:
    # period_end is the last day of the period, inclusive, for display.
    last_day = period.end - timedelta(days=1)
    rows = [(name, line) for name, lines in groups for line in lines]
    rows.append(("", grand_total(groups)))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for group, line in rows:
            writer.writerow(
                {
                    "period_start": period.start.isoformat(),
                    "period_end": last_day.isoformat(),
                    "group": group,
                    "kind": line.kind,
                    "name": line.name,
                    "amount": str(line.amount.quantize(PRECISION, ROUND_HALF_UP)),
                    "unit": unit,
                }
            )
    print(f"Wrote CSV to {path} ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> date:
    """Parse CLI arguments and return the date to report as if it were today."""
    parser = argparse.ArgumentParser(
        description="Fetch the last 30 days of AWS costs, by project, into a CSV for the usage dashboard."
    )
    parser.add_argument(
        "date",
        nargs="?",
        type=date.fromisoformat,
        help="report as if today were this date (YYYY-MM-DD); defaults to today (UTC)",
    )
    args = parser.parse_args(argv)
    return args.date or datetime.datetime.now(tz=datetime.UTC).date()


def main(argv: list[str] | None = None) -> None:
    try:
        import boto3
    except ImportError:
        sys.exit(
            "boto3 is not installed. "
            "Install the metrics extras: uv pip install -e '.[metrics]'"
        )

    period = last_30_days(parse_args(argv))
    print(f"Fetching costs for {period.start} to {period.end} (end exclusive)")

    client = boto3.client("ce", region_name=AWS_REGION)
    fetched = [(name, fetch(client, period, f)) for name, f in group_filters()]

    units = [items[0].unit for _, items in fetched if items]
    unit = units[0] if units else "USD"
    groups = [(name, visible_lines(items)) for name, items in fetched]
    write_csv(period, groups, unit, CSV_PATH)


if __name__ == "__main__":
    main()
