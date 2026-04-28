#!/usr/bin/env python3
"""Post previous full week's total AWS account cost to a Slack webhook."""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from urllib import error, request


def safely_get_env_vars(names: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in names:
        value = os.environ.get(name, "").strip()
        if not value:
            raise RuntimeError(f"Missing required environment variable: {name}")
        values[name] = value
    return values


def calculate_last_week() -> tuple[str, str]:
    today_utc = datetime.now(timezone.utc).date()
    current_week_monday = today_utc - timedelta(days=today_utc.weekday())
    previous_week_monday = current_week_monday - timedelta(days=7)
    return previous_week_monday.isoformat(), current_week_monday.isoformat()


def get_weekly_cost(start_date: str, end_date: str) -> tuple[str, str]:
    command = [
        "aws",
        "ce",
        "get-cost-and-usage",
        "--time-period",
        f"Start={start_date},End={end_date}",
        "--granularity",
        "DAILY",
        "--metrics",
        "UnblendedCost",
        "--output",
        "json",
    ]

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)

    results = payload.get("ResultsByTime", [])
    unit = "USD"
    amount = 0.0

    for result_by_time in results:
        total = result_by_time.get("Total", {}).get("UnblendedCost", {})
        amount += float(total.get("Amount", "0"))
        unit = total.get("Unit", unit)

    return str(amount), unit


def post_slack_message(webhook_url: str, message: str) -> None:
    data = json.dumps({"text": message}).encode("utf-8")

    for attempt in range(1, 4):
        req = request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=20) as response:
                if 200 <= response.status < 300:
                    return
                raise RuntimeError(f"Slack webhook returned HTTP {response.status}")
        except error.URLError as exc:
            if attempt == 3:
                raise RuntimeError(f"Failed to post to Slack: {exc}") from exc
            time.sleep(2)


if __name__ == "__main__":
    env = safely_get_env_vars(["SRE_BOT_WEBHOOK_INFO"])

    webhook_url = env["SRE_BOT_WEBHOOK_INFO"]

    start_date, end_date = calculate_last_week()
    raw_amount, unit = get_weekly_cost(start_date, end_date)
    display_end_date = (
        datetime.fromisoformat(end_date).date() - timedelta(days=1)
    ).isoformat()

    try:
        formatted_amount = f"{float(raw_amount):.2f}"
    except ValueError:
        formatted_amount = raw_amount

    message = (
        f":money_with_wings: SD&R Weekly AWS Spend \n"
        f":calendar: {start_date} to {display_end_date} (inclusive)\n"
        f":moneybag: ${formatted_amount} {unit}"
    )

    # print(message)
    post_slack_message(webhook_url, message)
    print("Posted weekly cost report to Slack")
