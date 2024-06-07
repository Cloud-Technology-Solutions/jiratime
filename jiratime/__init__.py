import argparse
import json
import logging
import yaml
import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv
from rich.progress import Console, Progress

load_dotenv()

logging.basicConfig(level="INFO")
log = logging.getLogger("log_work")

ATLASSIAN_URL = "https://appsbroker.atlassian.net"
API_TOKEN = os.getenv("API_TOKEN")

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


def get_user_account_id(email: str) -> str:
    url = f"{ATLASSIAN_URL}/rest/api/3/groupuserpicker"

    resp = requests.get(
        url,
        headers=REQUEST_HEADERS,
        params={"query": email},
        auth=(email, API_TOKEN),
        timeout=REQUEST_TIMEOUT,
    )
    result = handle_errors(resp, f"Failed to get account ID for your user")

    user_account_id = result["users"]["users"][0]["accountId"]

    return user_account_id


def search_for_ticket(ticket_summary: str, email: str):
    log.debug("Searching for ticket with summary:", ticket_summary)
    url = f"{ATLASSIAN_URL}/rest/api/3/issue/picker"
    params = {"currentJQL": f"summary ~ '{ticket_summary}'"}

    resp = requests.get(
        url,
        headers=REQUEST_HEADERS,
        params=params,
        auth=(email, API_TOKEN),
        timeout=REQUEST_TIMEOUT,
    )
    result = handle_errors(
        resp, f"Failed to search for a ticket with summary: {ticket_summary}"
    )

    first_match = result["sections"][0]["issues"][0]
    log.debug("Found match:", first_match)

    return first_match["key"]


def is_work_already_logged(ticket_id: str, iso_date: date, email: str) -> bool:
    worklog_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}/worklog"

    log.debug(worklog_url)
    log.debug(REQUEST_HEADERS)
    log.debug(email)

    resp = requests.get(
        worklog_url,
        headers=REQUEST_HEADERS,
        auth=(email, API_TOKEN),
        timeout=REQUEST_TIMEOUT,
    )
    result = handle_errors(resp, f"Failed to get worklogs from {ticket_id}")

    # Filtering all results just because the API doesn't work properly
    # in case you'd want filtered results startAfter and startBefore query params
    def date_filter(worklog: dict) -> list:
        return worklog["started"].startswith(iso_date.isoformat()) and worklog[
            "author"
        ]["accountId"] == get_user_account_id(email)

    worklog = list(filter(date_filter, result["worklogs"]))
    already_logged = len(worklog) > 0
    log.debug("Work already logged:", str(already_logged))

    return already_logged


def log_work(
    ticket: dict,
    iso_date: date,
    email: str,
    yes: bool,
    progress: Progress,
    task_id: str,
):
    weekday = iso_date.weekday()
    ticket_id = ticket["id"]
    if " " in ticket_id:
        ticket_id = search_for_ticket(ticket_id, email)
    progress.update(task_id, advance=0.3)
    time_spent = ticket["daily_time_spent"][weekday]
    worklog_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}/worklog"

    if time_spent in set([0, "0", "0h"]):
        progress.update(task_id, advance=0.7)
        return

    if is_work_already_logged(ticket_id, iso_date, email):
        progress.log(f"[{iso_date}] Work is already logged in {ticket_id}")
        progress.update(task_id, advance=0.7)
        return
    progress.update(task_id, advance=0.2)

    if "comment" in ticket:
        comment = ticket["comment"]
    else:
        comment = "Logging some time for today"

    payload = {
        "comment": {
            "content": [
                {
                    "content": [{"text": comment, "type": "text"}],
                    "type": "paragraph",
                }
            ],
            "type": "doc",
            "version": 1,
        },
        "started": f"{iso_date}T09:00:00.000+0000",
        "timeSpent": time_spent,
    }

    if yes:
        resp = requests.post(
            worklog_url,
            headers=REQUEST_HEADERS,
            data=json.dumps(payload),
            auth=(email, API_TOKEN),
            timeout=REQUEST_TIMEOUT,
        )
        handle_errors(resp, f"Failed to log work in {ticket_id} for {iso_date}")
    progress.update(task_id, advance=0.5)

    progress.log(f"[{iso_date}] Logged {time_spent} in {ticket_id}")


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
    parser.add_argument(
        "--config",
        "-c",
        default=f"{os.path.expanduser('~')}/.timesheet.yaml",
        help="Config file",
    )
    parser.add_argument(
        "--debug", action="store_true", default=False, help="Enable debug mode"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="Actually submit timesheet",
    )
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

    with open(args.config, "r") as stream:
        timesheet_config = yaml.safe_load(stream)

    email = timesheet_config["email"]

    base_date = date.today()
    date_list = [base_date]
    if args.this_week:
        base_date = date.today() - timedelta(days=date.today().weekday())
        date_list = [base_date + timedelta(days=x) for x in range(5)]
    if args.last_week:
        base_date = date.today() - timedelta(days=date.today().weekday() + 7)
        date_list = [base_date + timedelta(days=x) for x in range(5)]

    with Progress() as progress:
        timesheet_progress = progress.add_task(
            "[green]Submitting timesheet...", total=len(date_list)
        )
        if not args.yes:
            progress.print(
                "\n[red]NOTE: jiratime was run without -y, so no timesheets have "
                "actually been submitted. Re-run with the -y flag to submit time.\n"
            )
        for day in date_list:
            progress.print("-" * os.get_terminal_size().columns)
            iso_date = day.isoformat()
            day_progress = progress.add_task(
                f"[green]Logging work for {iso_date}",
                total=len(timesheet_config["hours"]),
            )
            for ticket in timesheet_config["hours"]:
                log_work(ticket, day, email, args.yes, progress, day_progress)
            progress.advance(day_progress)
            progress.update(timesheet_progress, advance=1)


if __name__ == "__main__":
    main()
