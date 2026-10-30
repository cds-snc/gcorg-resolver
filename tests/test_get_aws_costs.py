import csv
import importlib.util
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "data" / "get_aws_costs.py"

spec = importlib.util.spec_from_file_location("get_aws_costs", SCRIPT)
gac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gac)


def item(service: str, amount: str, usage_type: str = "CAN1-Usage") -> object:
    return gac.LineItem(service, usage_type, Decimal(amount), "USD")


class FakeCostExplorer:
    """Returns each page in turn, recording the request kwargs."""

    def __init__(self, pages: list[dict]):
        self.pages = pages
        self.calls: list[dict] = []

    def get_cost_and_usage(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return self.pages[len(self.calls) - 1]


def page(groups: list[tuple[str, str, str]], token: str | None = None) -> dict:
    result = {
        "ResultsByTime": [
            {
                "Groups": [
                    {
                        "Keys": [service, usage_type],
                        "Metrics": {"UnblendedCost": {"Amount": amount, "Unit": "USD"}},
                    }
                    for service, usage_type, amount in groups
                ]
            }
        ]
    }
    if token:
        result["NextPageToken"] = token
    return result


# ---------------------------------------------------------------------------
# category
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "service",
    [
        "AWS WAF",
        "AWS Config",
        "AWS Security Hub",
        "Amazon GuardDuty",
        "AWS Key Management Service",
        "AWS CloudTrail",
        "AWS Secrets Manager",
    ],
)
def test_security_services_are_security(service):
    assert gac.category(service, "CAN1-Usage") == gac.SECURITY


def test_waf_fixed_fees_are_security():
    assert gac.category("AWS WAF", "Global-WebACLV2") == gac.SECURITY


@pytest.mark.parametrize(
    ("service", "usage_type"),
    [
        ("AWS Lambda", "CAN1-Lambda-GB-Second"),
        ("AWS Lambda", "CAN1-Request"),
        ("Amazon API Gateway", "CAN1-ApiGatewayHttpRequest"),
        ("Amazon API Gateway", "CAN1-DataTransfer-Out-Bytes"),
        ("Amazon CloudFront", "EU-Requests-Tier2-HTTPS"),
        ("Amazon CloudFront", "CA-DataTransfer-Out-Bytes"),
    ],
)
def test_request_path_services_are_serving(service, usage_type):
    assert gac.category(service, usage_type) == gac.SERVING


def test_waf_request_charges_are_serving_not_security():
    assert gac.category("AWS WAF", "Global-RequestV2-Tier1") == gac.SERVING


def test_route_53_dns_queries_are_serving():
    assert gac.category("Amazon Route 53", "DNS-Queries") == gac.SERVING


def test_route_53_hosted_zone_is_everything_else():
    assert gac.category("Amazon Route 53", "HostedZone") == gac.OTHER


def test_nat_gateway_usage_is_security_whatever_the_service():
    assert gac.category("EC2 - Other", "CAN1-NatGateway-Hours") == gac.SECURITY


def test_cloudwatch_is_monitoring():
    assert gac.category("AmazonCloudWatch", "CAN1-CW:Requests") == gac.MONITORING


def test_s3_is_storage():
    assert gac.category("Amazon Simple Storage Service", "CAN1-Requests-Tier1") == (
        gac.STORAGE
    )


def test_ebs_usage_under_ec2_other_is_storage():
    assert gac.category("EC2 - Other", "CAN1-EBS:VolumeUsage.gp3") == gac.STORAGE


def test_athena_is_queries():
    assert gac.category("Amazon Athena", "CAN1-DataScannedInTB") == gac.QUERIES


@pytest.mark.parametrize("service", ["AWS Cost Explorer", "Amazon Route 53", "Tax"])
def test_unmatched_services_are_everything_else(service):
    assert gac.category(service, "CAN1-Usage") == gac.OTHER


def test_usage_rule_wins_over_a_later_service_rule():
    # NatGateway usage matches Security before the CloudWatch service rule.
    assert gac.category("AmazonCloudWatch", "NatGateway-Bytes") == gac.SECURITY


# ---------------------------------------------------------------------------
# item_name
# ---------------------------------------------------------------------------


def test_data_transfer_usage_is_named_data_transfer():
    assert gac.item_name("Amazon CloudFront", "CA-DataTransfer-Out-Bytes") == (
        "Data transfer"
    )


def test_tax_is_named_sales_tax():
    assert gac.item_name("Tax", "Tax") == "Sales tax"


@pytest.mark.parametrize(
    ("service", "expected"),
    [
        ("Amazon API Gateway", "API Gateway"),
        ("AWS Cost Explorer", "Cost Explorer"),
        ("Amazon Route 53", "Route 53"),
    ],
)
def test_amazon_and_aws_prefixes_are_stripped(service, expected):
    assert gac.item_name(service, "CAN1-Usage") == expected


# ---------------------------------------------------------------------------
# last_30_days
# ---------------------------------------------------------------------------


def test_last_30_days_ends_before_today():
    period = gac.last_30_days(date(2026, 10, 30))
    assert period.end == date(2026, 10, 30)


def test_last_30_days_spans_30_days():
    period = gac.last_30_days(date(2026, 10, 30))
    assert period.end - period.start == timedelta(days=30)
    assert period.start == date(2026, 9, 30)


def test_last_30_days_can_cross_a_year_boundary():
    period = gac.last_30_days(date(2027, 1, 15))
    assert period.start == date(2026, 12, 16)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

PERIOD = gac.Period(date(2026, 10, 19), date(2026, 10, 26))
ANY_FILTER = gac.tag_filter(["GCOrgResolver"])


def test_fetch_builds_line_items_from_groups():
    client = FakeCostExplorer([page([("AWS WAF", "Global-WebACLV2", "2.65")])])
    items = gac.fetch(client, PERIOD, ANY_FILTER)
    assert items == [gac.LineItem("AWS WAF", "Global-WebACLV2", Decimal("2.65"), "USD")]


def test_fetch_sends_the_period_dates():
    client = FakeCostExplorer([page([])])
    gac.fetch(client, PERIOD, ANY_FILTER)
    assert client.calls[0]["TimePeriod"] == {"Start": "2026-10-19", "End": "2026-10-26"}


def test_fetch_sends_the_given_filter():
    client = FakeCostExplorer([page([])])
    gac.fetch(client, PERIOD, ANY_FILTER)
    assert client.calls[0]["Filter"] == {
        "Tags": {"Key": "CostCentre", "Values": ["GCOrgResolver"]}
    }


def test_fetch_follows_pagination():
    client = FakeCostExplorer(
        [
            page([("AWS WAF", "Global-WebACLV2", "1")], token="next"),
            page([("AWS Config", "CAN1-ConfigRuleEvaluations", "2")]),
        ]
    )
    items = gac.fetch(client, PERIOD, ANY_FILTER)
    assert [i.service for i in items] == ["AWS WAF", "AWS Config"]
    assert client.calls[1]["NextPageToken"] == "next"


def test_fetch_keeps_the_filter_on_later_pages():
    client = FakeCostExplorer([page([], token="next"), page([])])
    gac.fetch(client, PERIOD, ANY_FILTER)
    assert client.calls[1]["Filter"] == ANY_FILTER


def test_fetch_with_no_costs_returns_no_items():
    client = FakeCostExplorer([page([])])
    assert gac.fetch(client, PERIOD, ANY_FILTER) == []


# ---------------------------------------------------------------------------
# group_filters
# ---------------------------------------------------------------------------


def test_groups_are_the_three_projects_then_shared():
    names = [name for name, _ in gac.group_filters()]
    assert names == [
        gac.RESOLVER,
        gac.PROGRAM_CODE,
        gac.SERVICE_INVENTORY,
        gac.SHARED,
    ]


@pytest.mark.parametrize(
    ("group", "tag"),
    [
        ("GC Organization Name Resolution API", "GCOrgResolver"),
        ("Program code lookup", "program-code-lookup"),
        ("Service inventory lookup", "service-inventory-lookup"),
    ],
)
def test_project_groups_filter_on_their_cost_centre_tag(group, tag):
    filters = dict(gac.group_filters())
    assert filters[group] == {"Tags": {"Key": "CostCentre", "Values": [tag]}}


def test_shared_group_is_everything_without_a_project_tag():
    filters = dict(gac.group_filters())
    assert filters[gac.SHARED] == {
        "Not": {
            "Tags": {
                "Key": "CostCentre",
                "Values": [
                    "GCOrgResolver",
                    "program-code-lookup",
                    "service-inventory-lookup",
                ],
            }
        }
    }


# ---------------------------------------------------------------------------
# build_lines
# ---------------------------------------------------------------------------


def test_categories_are_summed_and_ordered_largest_first():
    lines = gac.build_lines(
        [
            item("AWS Config", "0.50"),
            item("AWS WAF", "2.00"),
            item("AmazonCloudWatch", "3.00"),
        ]
    )
    categories = [(line.name, line.amount) for line in lines if line.kind == "category"]
    assert categories == [
        (gac.MONITORING, Decimal("3.00")),
        (gac.SECURITY, Decimal("2.50")),
    ]


def test_categories_with_no_items_have_no_line():
    lines = gac.build_lines([item("AWS WAF", "2.00")])
    assert [line.name for line in lines if line.kind == "category"] == [gac.SECURITY]


def test_everything_else_line_always_follows_the_categories():
    lines = gac.build_lines([item("AWS WAF", "2.00")])
    assert [line.kind for line in lines] == ["category", "other", "rest"]
    assert lines[1].amount == Decimal(0)


def test_everything_else_items_at_or_above_the_minimum_are_listed():
    lines = gac.build_lines(
        [item("Tax", "1.00"), item("Amazon Route 53", "0.99")],
        detail_min=Decimal(1),
    )
    details = [line.name for line in lines if line.kind == "detail"]
    assert details == ["Sales tax"]


def test_smaller_items_is_the_rest_of_everything_else():
    lines = gac.build_lines(
        [
            item("Tax", "1.50"),
            item("Amazon Route 53", "0.25"),
            item("AWS Cost Explorer", "0.25"),
        ],
        detail_min=Decimal(1),
    )
    assert lines[-1] == gac.Line("rest", gac.SMALLER_ITEMS, Decimal("0.50"))


# ---------------------------------------------------------------------------
# visible_lines
# ---------------------------------------------------------------------------


def test_visible_lines_start_with_the_total_of_every_item():
    lines = gac.visible_lines([item("AWS WAF", "2.00"), item("Tax", "0.00001")])
    assert lines[0] == gac.Line("total", "Total", Decimal("2.00001"))


def test_everything_else_at_zero_is_hidden():
    lines = gac.visible_lines([item("AWS WAF", "2.00")])
    assert [line.name for line in lines] == ["Total", gac.SECURITY]


def test_categories_that_round_to_zero_are_hidden():
    lines = gac.visible_lines(
        [item("AWS WAF", "2.00"), item("AmazonCloudWatch", "0.00004")]
    )
    assert [line.name for line in lines] == ["Total", gac.SECURITY]


def test_fractions_of_a_cent_are_shown():
    lines = gac.visible_lines([item("AWS WAF", "2.00"), item("AWS Lambda", "0.0056")])
    assert [line.name for line in lines] == ["Total", gac.SECURITY, gac.SERVING]


def test_smaller_items_is_hidden_without_a_named_item_above_it():
    lines = gac.visible_lines([item("Tax", "0.50")])
    assert [line.kind for line in lines] == ["total", "other"]


def test_smaller_items_that_round_to_zero_are_hidden():
    lines = gac.visible_lines([item("Tax", "1.50"), item("Amazon Route 53", "0.00004")])
    assert [line.kind for line in lines] == ["total", "other", "detail"]


def test_smaller_items_is_shown_under_a_named_item():
    lines = gac.visible_lines([item("Tax", "1.50"), item("Amazon Route 53", "0.50")])
    assert [line.kind for line in lines] == ["total", "other", "detail", "rest"]


def test_no_costs_gives_only_a_zero_total():
    assert gac.visible_lines([]) == [gac.Line("total", "Total", Decimal(0))]


# ---------------------------------------------------------------------------
# grand_total and write_csv
# ---------------------------------------------------------------------------


def test_grand_total_sums_the_group_totals():
    groups = [
        (
            "a",
            [
                gac.Line("total", "Total", Decimal("1.50")),
                gac.Line("category", "x", Decimal("1.50")),
            ],
        ),
        ("b", [gac.Line("total", "Total", Decimal("0.25"))]),
    ]
    assert gac.grand_total(groups) == gac.Line("grand_total", "Total", Decimal("1.75"))


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_write_csv_writes_each_group_then_the_grand_total(tmp_path):
    path = tmp_path / "aws_costs.csv"
    groups = [
        (gac.RESOLVER, [gac.Line("total", "Total", Decimal("1.5"))]),
        (gac.SHARED, [gac.Line("total", "Total", Decimal("0.00456"))]),
    ]
    gac.write_csv(PERIOD, groups, "USD", path)
    rows = read_rows(path)
    assert [(r["group"], r["kind"], r["amount"]) for r in rows] == [
        (gac.RESOLVER, "total", "1.5000"),
        (gac.SHARED, "total", "0.0046"),
        ("", "grand_total", "1.5046"),
    ]


def test_write_csv_uses_the_inclusive_end_date(tmp_path):
    path = tmp_path / "aws_costs.csv"
    gac.write_csv(
        PERIOD, [(gac.RESOLVER, [gac.Line("total", "Total", Decimal(1))])], "USD", path
    )
    rows = read_rows(path)
    assert {(r["period_start"], r["period_end"], r["unit"]) for r in rows} == {
        ("2026-10-19", "2026-10-25", "USD")
    }
