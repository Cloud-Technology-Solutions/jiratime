# `jiratime` README

Just a simple script to give you a head start at automating your timesheet
submission in JIRA.

## Prerequisites

1.  A JIRA API token is needed for `jiratime` to be able to authenticate on
    your behalf. You can create a JIRA API token from here: [Create and manage
    API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2.  Set the API key as an environment variable:

    ```sh
    export API_TOKEN=<insert JIRA token>
    ```

## Installation

```sh
pipx install .
```

## Configuration

`jiratime` requires a configuration file to set your email address and define
the JIRA tickets and the daily amount of hours (from Monday to Friday). A
sample is provided in `test/sample_config.yaml`. You can either save this as
`~/.timesheets.yaml` or pass the config file in each time with `-c <filename`>.

## Usage

> [!NOTE]
> To avoid logging time twice, `jiratime` will automatically check if time has
> been logged for a particular day already.

Note that by default `jiratime` does not actually submit time values. To tell
it to actually submit time, pass in the `-y` flag.

### Daily

You can run `jiratime` daily as follows (or just create a simple cronjob):

```sh
jiratime
```

The above is identical to:

```sh
jiratime --today
```

### Logging time for this week

In case you want to log time on a weekly basis, usually on a Friday, here's how
you can do that:

```sh
jiratime --this-week
```

### Logging time for last week

In case you forgot to log time for last week, you can run:

```sh
jiratime --last-week
```

## TODO

-   Convert to use `click` rather than `argparse` for a more featureful CLI
-   Add an interactive mode
