# Automate your time logging in JIRA

Just a simple script to give you a head start at automating your time sheet submission in JIRA.

## Prerequisites

1. A JIRA API token is needed for the script to be able to authenticate on your behalf. You can create a JIRA API token from here: [Create and manage API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
1. Create a `.env` file with the following contents:
    ```shell
    AUTH_TOKEN=<insert JIRA token>
    ```

## Installation

```shell
pip3 install -r requirements.txt
```

## Configuration

*Before* running `log_work.py` for the first time, edit the script and define the JIRA tickets and the daily amount of hours (from Mon to Fri).

## Running the script

Run the script daily as follows (or just create a simple cronjob):

```shell
python3 log_work.py
```
