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
TODAYS_ISO_DATE = date.today().isoformat()
WEEKDAY = date.today().weekday()


def main():
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    for ticket in JIRA_TICKETS:
        worklog_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket['id']}/worklog"

        if ticket["daily_time_spent"][WEEKDAY] in set([0, "0"]):
            continue

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
            "started": f"{TODAYS_ISO_DATE}T09:00:00.000+0000",
            "timeSpent": ticket["daily_time_spent"][WEEKDAY],
        }

        resp = requests.post(
            worklog_url,
            headers=headers,
            data=json.dumps(payload),
            auth=(USER_EMAIL, API_TOKEN),
        )

        if resp.status_code == 201:
            print(json.dumps(resp.json(), indent=4))
        else:
            try:
                obj = resp.json()
                error_codes = obj["errors"]
                error_messages = obj["errorMessages"]
            except ValueError:
                error_codes = f"HTTP {response.status_code}"
                error_messages = response.text
            raise Exception(
                f"Failed to log work in {ticket['id']}: {error_codes}\n"
                f"{error_messages}"
            )


if __name__ == "__main__":
    main()
