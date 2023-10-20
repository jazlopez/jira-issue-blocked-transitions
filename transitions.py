# By Jaziel Lopez (github.com/jazlopez)
# See license file.

from exit_codes import *
from shutdown import teardown
from auth import authenticate
from texttable import Texttable
import jira
import click
import os
from os import sep as system_separator
import datetime
import csv
import signal
import logging
from pytz import timezone


# ----
EXPORT_DIRECTORY = os.getenv("EXPORT_DIRECTORY", None)
LOGS_DIRECTORY = os.getenv("LOGS_DIRECTORY", None)
JQL_QUERY_FILENAME = os.getenv("JQL_QUERY_FILENAME", "jql.jql")

if not EXPORT_DIRECTORY:
    click.secho("Environment variable: EXPORT_DIRECTORY is not set. Unable to continue. Will exit now")
    teardown(EXIT_ENVIRONMENT_EXPORT_DIRECTORY_ERROR_CODE)

if not os.path.exists(EXPORT_DIRECTORY) :
    click.secho(f"EXPORT_DIRECTORY: {EXPORT_DIRECTORY} is declared but it is not created. Unable to continue. "
                f"Will exit now")
    teardown(EXIT_EXPORT_DIRECTORY_ERROR_CODE)

if not LOGS_DIRECTORY:
    click.secho("Environment variable: LOGS_DIRECTORY is not set. Unable to continue. Will exit now")
    teardown(EXIT_ENVIRONMENT_LOGS_DIRECTORY_ERROR_CODE)

if not os.path.exists(LOGS_DIRECTORY) :
    click.secho(f"LOGS_DIRECTORY: {LOGS_DIRECTORY} is declared but it is not created. Unable to continue. "
                f"Will exit now")
    teardown(EXIT_LOGS_DIRECTORY_ERROR_CODE)


if not LOGS_DIRECTORY:
    click.secho("Environment variable: LOGS_DIRECTORY is not set. Unable to continue. Will exit now")
    teardown(EXIT_DIRECTORIES_MISSING_CODE)

# -------
NOW = datetime.datetime.now().strftime("_%Y_%m_%d-%H_%M")
LOG_FILE = os.path.join(LOGS_DIRECTORY, ".worklogs_" + NOW + ".log")
FORMAT = logging.Formatter("%(asctime)s jlopez.mx [%(module)s - %(funcName)s:%(lineno)s] %(levelname)s: %(message)s")
HANDLER = logging.FileHandler(filename=LOG_FILE)
HANDLER.setFormatter(FORMAT)
LOG = logging.getLogger(__name__)
LOG.addHandler(HANDLER)
LOG.setLevel(logging.INFO)
# -------
display = Texttable()

def get_pst(input, fmt="%Y-%m-%dT%H:%M:%S.%f%z"):
    return datetime.datetime.strptime(input, fmt).astimezone(tz=timezone('US/Pacific'))

def signal_handler(sign, handler):

    click.clear()

    if sign == signal.SIGINT:
        click.secho("[INFO] You opted to stop the program: it will exit now...")
        LOG.info("Received an expected program interruption event: program will close gracefully")
        teardown(EXIT_NO_ERROR_CODE)

    LOG.info(f"[INFO] captured abnormal interruption event {sign}")
    LOG.info(f"[INFO] handler {handler}")
    teardown(sign)

def get_export_file_path(filename="report"):

    location = os.path.join(system_separator, EXPORT_DIRECTORY,
                            f"{filename}-{str(datetime.datetime.now()).replace(' ', '_').replace(':', '.')}.csv")

    return location

def time_format(seconds=None):

    if seconds:

        seconds = int(seconds)
        d = seconds // (3600 * 8)
        h = seconds // 3600 % 8
        m = seconds % 3600 // 60
        s = seconds % 3600 % 60
        if d > 0:
            return '{days}d {hours}h {minutes}m {secs}s'.format(days=d, hours=h, minutes=m, secs=s)
        elif h > 0:
            return '{hours}h {minutes}m {secs}s'.format(hours=h, minutes=m, secs=s)
        elif m > 0:
            return '{minutes}m {secs}s'.format(minutes=m, secs=s)
        elif s > 0:
            return '{secs}s'.format(secs=s)

    return ''

# -------
def close_jira_session(client=None):

    click.secho(f"[INFO] Closing JIRA session before leaving program...", fg="green")
    client.kill_session()


def get_transitions_by_query(client=None, query=None, location=None):
    next_page_starts_at = 0
    count_worklogs = 0
    available_results = True

    with open(file=location, mode='w') as exported_results:

        # display = Texttable()
        csv_writer = csv.writer(exported_results, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # prob. not the best way to handle headers here
        headers = ["ID", "Blocked At", "Unblocked At", "Total Blocked Time"]
        csv_writer.writerow(headers)

        # get totals for progress bar
        click.secho(f"[INFO] Calculating report rows...", fg="green")

        entries = []
        while available_results:
            _issues = client.search_issues(jql_str=query, startAt=next_page_starts_at-1,  maxResults=20, expand="Names")
            available_results = len(_issues) > 0
            # available_results = 0

            for issue in _issues:
                changelog = client.issue(id=issue.id, expand='changelog')
                #
                for history in changelog.changelog.histories:
                    for item in history.items:
                        if item.field == "status":
                            if item.toString == "Blocked":
                                entry = {}
                                unblocked_at = None

                                entry[issue.key] = {}

                                entry[issue.key]["blocked_at"] = get_pst(history.created)

                            if item.fromString == "Blocked":

                                entry[issue.key]["unblocked_at"] = get_pst(history.created)
                              
                                entries.append(entry)

                if not unblocked_at:
                    
                  try:
                        entry[issue.key]["unblocked_at"] = ""
                        entries.append(entry)
                    except:
                        continue

                next_page_starts_at = next_page_starts_at + 1

        for i in entries:

            for k in i.keys():
                issue_id = k
                break

            for data in i.values():

                data["total_blocked_time"] = "Still Blocked"

                if data["unblocked_at"] != "":
                    delta = (data["unblocked_at"] - data["blocked_at"]).total_seconds()
                    data["total_blocked_time"] = time_format(delta)

                csv_writer.writerow([issue_id, data["blocked_at"], data["unblocked_at"], data["total_blocked_time"]])

    click.secho(f"[INFO] Exported results to file {os.path.join(EXPORT_DIRECTORY, os.path.basename(location))}", fg="green")

def time_format(seconds=None):

    if seconds:

        seconds = int(seconds)

        d = seconds // (24 * 3600)
        seconds = seconds % (24 * 3600)
        h =  seconds // 3600
        seconds %= 3600
        m = seconds // 60
        seconds %= 60
        s = seconds

        if d > 0:
            return '{days}d {hours}h {minutes}m {secs}s'.format(days=d, hours=h, minutes=m, secs=s)
        elif h > 0:
            return '{hours}h {minutes}m {secs}s'.format(hours=h, minutes=m, secs=s)
        elif m > 0:
            return '{minutes}m {secs}s'.format(minutes=m, secs=s)
        elif s > 0:
            return '{secs}s'.format(secs=s)

    return ''

def query_jira_by_file(client=None, jql=None):
    try:
        with open(jql, 'r') as jql_queries:
            lines = [line.rstrip() for line in jql_queries]

            for line in lines:
                get_transitions_by_query(client=client, query=line, location=get_export_file_path())

        close_jira_session(client=client)
        teardown(exit_code=0)
    except jira.exceptions.JIRAError as e:
        raise Exception(e.text)
    except Exception as e:
        LOG.error(e)
        teardown(exit_code=EXIT_ERROR_CODE)

@click.command()
def panel():
    client = authenticate(logger=LOG)
    current_user = client.user(client.current_user())
    click.clear()

    dot = "\t"

    for i in range(90):
        dot = dot + "-"

    click.secho(dot)
    click.secho(f"{client.server_url} | {current_user.displayName}"
                f" | {current_user.emailAddress} | {current_user.timeZone}")

    if client.session() and os.path.exists(JQL_QUERY_FILENAME):
        query_jira_by_file(client=client, jql=JQL_QUERY_FILENAME)


# -------
signal.signal(signal.SIGINT, signal_handler)

# -------
if __name__ == '__main__':
    panel()
