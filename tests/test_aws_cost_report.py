import importlib.util
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "scripts"
    / "aws_cost_report.py"
)

spec = importlib.util.spec_from_file_location("aws_cost_report", SCRIPT)
acr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acr)

URL = "https://cds-snc.github.io/gcorg-resolver/"


def test_successful_dashboard_update_links_the_dashboard():
    assert acr.dashboard_line(URL, "success") == f":bar_chart: Usage dashboard: {URL}"


def test_manual_run_with_no_result_links_the_dashboard():
    assert acr.dashboard_line(URL, "") == f":bar_chart: Usage dashboard: {URL}"


@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped"])
def test_unsuccessful_dashboard_update_warns_and_links_last_good_version(result):
    line = acr.dashboard_line(URL, result)
    assert line.startswith(":warning: Usage dashboard update failed")
    assert line.endswith(URL)
