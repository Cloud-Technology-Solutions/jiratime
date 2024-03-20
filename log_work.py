import json
import os
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

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

# Date helpers
TODAYS_DATE = date.today()
WEEKDAY = date.today().weekday()

headers = {"Accept": "application/json", "Content-Type": "application/json"}


def handle_errors(response, message) -> dict:
    if response.status_code in set([200, 201]):
        # print(json.dumps(response.json(), indent=4))
        return response.json()

    try:
        obj = response.json()
        error_codes = obj["errors"]
        error_messages = obj["errorMessages"]
    except ValueError:
        error_codes = f"HTTP {response.status_code}"
        error_messages = response.text
    raise Exception(f"{message}: {error_codes}\n" f"{error_messages}")


def get_worklog(ticket_id: str, iso_date: date) -> dict:
    worklog_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}/worklog"

    resp = requests.get(
        worklog_url,
        headers=headers,
        auth=(USER_EMAIL, API_TOKEN),
    )
    result = handle_errors(resp, f"Failed to get worklogs from {ticket_id}")

    # Filtering all results just because the API doesn't work properly
    # in case you'd want filtered results startAfter and startBefore query params
    def date_filter(worklog: dict) -> list:
        return worklog["started"].startswith(iso_date.isoformat())

    worklog = list(filter(date_filter, result["worklogs"]))
    # print(json.dumps(worklog, indent=4))

    return worklog


def is_already_logged(ticket_id: str, iso_date: date) -> bool:
    worklogs = get_worklog(ticket_id, iso_date)

    return len(worklogs) > 0


def log_work(ticket_id: str, iso_date: date, time_spent: str):
    worklog_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}/worklog"

    if time_spent in set([0, "0", "0h"]):
        return

    if is_already_logged(ticket_id, iso_date):
        print(f"Work is already logged in {ticket_id}")
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
        headers=headers,
        data=json.dumps(payload),
        auth=(USER_EMAIL, API_TOKEN),
    )
    handle_errors(resp, f"Failed to log work in {ticket_id} for {iso_date}")
    print(f"Logged {time_spent} in {ticket_id}")


def main():
    print(f"Logging work for: {TODAYS_DATE}")
    for ticket in JIRA_TICKETS:
        log_work(
            ticket["id"],
            TODAYS_DATE,
            ticket["daily_time_spent"][WEEKDAY],
        )


if __name__ == "__main__":
    main()
