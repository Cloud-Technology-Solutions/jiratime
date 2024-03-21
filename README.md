# Automate your time logging in JIRA

Just a simple script to give you a head start at automating your timesheet
submission in JIRA.

## Prerequisites

1.  A JIRA API token is needed for the script to be able to authenticate on
    your behalf. You can create a JIRA API token from here: [Create and manage
    API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2.  Create a `.env` file with the following contents:

    ```shell
    AUTH_TOKEN=<insert JIRA token>
    ```

## Installation

```shell
pip3 install -r requirements.txt
```

## Configuration

*Before* running `log_work.py` for the first time, edit the script and define
the JIRA tickets and the daily amount of hours (from Mon to Fri).

## Running the script

> [!NOTE]
> To avoid logging time twice, the script will automatically check if time has
> been logged for a particular day already.

### Daily

You can run the script daily as follows (or just create a simple cronjob):

```shell
python3 log_work.py
```

The above is identical to:

```shell
python3 log_work.py --today
```

### Logging time for this week

In case you want to log time on a weekly basis, usually on a Friday, here's how
you can do that:

```shell
python3 log_work.py --this-week
```

### Logging time for last week

In case you forgot to log time for last week, you can run:

```shell
python3 log_work.py --last-week
```

## Considerations

A few things to consider before fully relying on the script:

-   There's only support for logging time on a daily basis
-   Running the script more than once per day results in multiple time logs for
    that day
