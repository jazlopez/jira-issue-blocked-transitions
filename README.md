Reports dates of when an JIRA issue blocks/unblocks: help you analize how long an issue  remains in blocked status

## Setup

In order to start working with this project you should configure the following environment variables:

```shell
export EXPORT_DIRECTORY=/tmp/exports
export LOGS_DIRECTORY=/tmp/logs
export JIRA_USER=YOUR_LOGIN_NAME
export JIRA_PASSWD=YOUR_LOGIN_PASSWORD
export JIRA_URL=https://jira.com
```
And install all required packages

```shell
pip3 install -r requirements.txt
```

## Configure

You need to have an initial JQL query to fetch the issues you want to analyze how long these issues remained in blocked status.

Edit the `jql.jql` and add your JQL.

```jql
project = YOUR_PROJECT
```

## Run

After you have configured the required information you should be able to pull out the report with the blocked-start-date, blocked-end-date for the issues that matched the JQL query.

```shell
python3 transitions.py

# 	------------------------------------------------------------------------------------------
# https://jira.com | YOUR_USER | YOUR_EMAIL_ADDRESS | YOUR_TIMEZONE
# [INFO] Calculating report rows...
# [INFO] Exported results to file /tmp/exports/report-2023-10-19_18.15.01.571517.csv
# [INFO] Closing JIRA session before leaving program...
# [INFO] Program exits now... Good bye
# Process finished with exit code 0
```

It should generate a csv report as below:

<img width="512" alt="image" src="https://github.com/jazlopez/jira-issue-blocked-transitions/assets/2969347/2443d2ee-df7f-4000-8851-9c9d0d987e96">

## Contact

You can contact me by leaving a github issue with your comment. I will follow up as time permits. 

You can also visit my github profile to see other published projects at [github.com/jazlopez](https://github.com/jazlopez) or my personal website at [jlopez.mx](https://jlopez.mx)

## Version

1.0.0 Initial
