import argparse
import json
import logging
import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level="INFO")
log = logging.getLogger("log_work")

ATLASSIAN_URL = "https://appsbroker.atlassian.net"
USER_EMAIL = ""
API_TOKEN = os.getenv("API_TOKEN")

# A list of JIRA tickets which are assigned to you for tracking/logging time. e.g. IACC-38, IP-54, SSS-312 etc.
# Define a total amount of time per day (from Mon to Fri) you're spending on each ticket:
#   hours (e.g. "6h")
#   minutes (e.g. "30m")
#   a combination of both (e.g. "3h 30m")
JIRA_TICKETS = [
    # MAIN PROJECT WORK
    {"id": "TICKET-1", "daily_time_spent": ["7h 30m", "7h 30m", "7h 30m", "0", "6h"]},
    # Holiday / Sick / Compassionate etc.
    {"id": "NBL-2", "daily_time_spent": ["0", "0", "0", "7h 30m", "0"]},
    # Training / certifications work incl.
    {"id": "IACT-5", "daily_time_spent": ["0", "0", "0", "0", "1h"]},
    # Tech Talks
    {"id": "NW-55", "daily_time_spent": ["0", "0", "0", "0", "30m"]},
]

# Helpers
REQUEST_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
REQUEST_TIMEOUT = 10


def handle_errors(response, message) -> dict:
    if response.status_code in set([200, 201]):
        log.debug(json.dumps(response.json(), indent=4))
        return response.json()

    try:
        obj = response.json()
        error_codes = obj["errors"]
        error_messages = obj["errorMessages"]
    except ValueError:
        error_codes = f"HTTP {response.status_code}"
        error_messages = response.text
    raise Exception(f"{message}: {error_codes}\n" f"{error_messages}")


def get_user_account_id() -> str:
    url = f"{ATLASSIAN_URL}/rest/api/3/groupuserpicker"

    resp = requests.get(
        url,
        headers=REQUEST_HEADERS,
        params={"query": USER_EMAIL},
        auth=(USER_EMAIL, API_TOKEN),
        timeout=REQUEST_TIMEOUT,
    )
    result = handle_errors(resp, f"Failed to get account ID for your user")

    user_account_id = result["users"]["users"][0]["accountId"]
    return user_account_id


def get_worklog(ticket_id: str, iso_date: date) -> dict:
    worklog_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}/worklog"

    resp = requests.get(
        worklog_url,
        headers=REQUEST_HEADERS,
        auth=(USER_EMAIL, API_TOKEN),
        timeout=REQUEST_TIMEOUT,
    )
    result = handle_errors(resp, f"Failed to get worklogs from {ticket_id}")

    # Filtering all results just because the API doesn't work properly
    # in case you'd want filtered results startAfter and startBefore query params
    def date_filter(worklog: dict) -> list:
        return (
            worklog["started"].startswith(iso_date.isoformat())
            and worklog["author"]["accountId"] == get_user_account_id()
        )

    worklog = list(filter(date_filter, result["worklogs"]))
    log.debug(json.dumps(worklog, indent=4))
    return worklog


def is_work_already_logged(ticket_id: str, iso_date: date) -> bool:
    worklogs = get_worklog(ticket_id, iso_date)

    return len(worklogs) > 0


def log_work(ticket: dict, iso_date: date):
    weekday = iso_date.weekday()
    ticket_id = ticket["id"]
    time_spent = ticket["daily_time_spent"][weekday]
    worklog_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}/worklog"

    if time_spent in set([0, "0", "0h"]):
        return

    if is_work_already_logged(ticket_id, iso_date):
        log.info(f"Work is already logged in {ticket_id}")
        return

    payload = {
        "comment": {
            "content": [
                {
                    "content": [
                        {"text": "Logging some time for today", "type": "text"}
                    ],
                    "type": "paragraph",
                }
            ],
            "type": "doc",
            "version": 1,
        },
        "started": f"{iso_date}T09:00:00.000+0000",
        "timeSpent": time_spent,
    }

    resp = requests.post(
        worklog_url,
        headers=REQUEST_HEADERS,
        data=json.dumps(payload),
        auth=(USER_EMAIL, API_TOKEN),
        timeout=REQUEST_TIMEOUT,
    )
    handle_errors(resp, f"Failed to log work in {ticket_id} for {iso_date}")
    log.info(f"Logged {time_spent} in {ticket_id}")


def main():
    doc = """
Log your work in JIRA

By default the script will log time in all of your tickets ONLY FOR TODAY.
Use the following arguments to change the behavior and specify if you need
to execute a full weekly schedule for this / last week.
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=doc
    )
    parser.add_argument("--debug", action="store_true", default=False, help="Enable debug mode")
    period = parser.add_mutually_exclusive_group(required=False)
    period.add_argument(
        "--today", action="store_true", help="Log work in your tickets only for today"
    )
    period.add_argument(
        "--this-week",
        action="store_true",
        help="Execute the full weekly schedule for THIS week. This would log \
            time for every day of that week for all of your tickets.",
    )
    period.add_argument(
        "--last-week",
        action="store_true",
        help="Execute the full weekly schedule for LAST week. This would log \
            time for every day of that week for all of your tickets.",
    )
    args = parser.parse_args()

    log.setLevel("DEBUG" if args.debug else "INFO")

    base_date = date.today()
    date_list = [base_date]
    if args.this_week:
        base_date = date.today() - timedelta(days=date.today().weekday())
        date_list = [base_date + timedelta(days=x) for x in range(5)]
    if args.last_week:
        base_date = date.today() - timedelta(days=date.today().weekday() + 7)
        date_list = [base_date + timedelta(days=x) for x in range(5)]

    for day in date_list:
        iso_date = day.isoformat()
        log.info(f"Logging work for: {iso_date}")
        for ticket in JIRA_TICKETS:
            log_work(ticket, day)
