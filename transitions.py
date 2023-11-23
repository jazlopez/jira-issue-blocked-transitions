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
import re


from pytz import timezone

def get_pst(input, fmt="%Y-%m-%dT%H:%M:%S.%f%z"):
    return datetime.datetime.strptime(input, fmt).astimezone(tz=timezone('US/Pacific'))

# ----
EXPORT_DIRECTORY = os.getenv("EXPORT_DIRECTORY", None)
LOGS_DIRECTORY = os.getenv("LOGS_DIRECTORY", None)
JQL_QUERY_FILENAME = os.getenv("JQL_QUERY_FILENAME", "jql.jql")

if not EXPORT_DIRECTORY:
    click.secho("Environment variable: EXPORT_DIRECTORY is not set. Unable to continue. Will exit now")
    teardown(EXIT_ENVIRONMENT_EXPORT_DIRECTORY_ERROR_CODE)

if not os.path.exists(EXPORT_DIRECTORY) :
    click.secho(f"EXPORT_DIRECTORY: {EXPORT_DIRECTORY} is declared but it is not created. Attempting to create {EXPORT_DIRECTORY}.")

    try:
        os.mkdir(EXPORT_DIRECTORY)
    except:
        click.secho(f"Unable to create {EXPORT_DIRECTORY}. Will exit now")
        teardown(EXIT_EXPORT_DIRECTORY_ERROR_CODE)

if not LOGS_DIRECTORY:
    click.secho("Environment variable: LOGS_DIRECTORY is not set. Unable to continue. Will exit now")
    teardown(EXIT_ENVIRONMENT_LOGS_DIRECTORY_ERROR_CODE)

if not os.path.exists(LOGS_DIRECTORY) :
    click.secho(f"LOGS_DIRECTORY: {LOGS_DIRECTORY} is declared but it is not created. Attempting to create {LOGS_DIRECTORY}. ")

    try:
        os.mkdir(LOGS_DIRECTORY)
    except:
        click.secho(f"Unable to create {LOGS_DIRECTORY}. Will exit now")
        teardown(EXIT_LOGS_DIRECTORY_ERROR_CODE)

# -------
NOW = datetime.datetime.now().strftime("_%Y_%m_%d-%H_%M")
LOG_FILE = os.path.join(LOGS_DIRECTORY, ".worklogs_" + NOW + ".log")
FORMAT = logging.Formatter("%(asctime)s jlopez.mx [%(module)s - %(funcName)s:%(lineno)s] %(levelname)s: %(message)s")
HANDLER = logging.FileHandler(filename=LOG_FILE)
HANDLER.setFormatter(FORMAT)
# -------
NO_LABELS_EXISTS = "No Labels"
NO_BUSINESS_VALUE_EXISTS = "No Business Value"
NO_STORY_POINT_EXISTS = "No Story Points"
EPIC_LINK_NAME_ERROR = "Epic Link Error"
EPIC_LINK_NAME_NOT_AVAILABLE = "No Epic Link Name"

# -------
LOG = logging.getLogger(__name__)
LOG.addHandler(HANDLER)
LOG.setLevel(logging.INFO)
# -------
display = Texttable()


def signal_handler(sign, handler):

    click.clear()

    if sign == signal.SIGINT:
        click.secho("[INFO] You opted to stop the program: it will exit now...")
        LOG.info("Received an expected program interruption event: program will close gracefully")
        teardown(EXIT_NO_ERROR_CODE)

    LOG.info(f"[INFO] captured abnormal interruption event {sign}")
    LOG.info(f"[INFO] handler {handler}")
    teardown(sign)

def get_export_file_path(filename="changelogs"):

    location = os.path.join(system_separator, EXPORT_DIRECTORY,
                            f"{filename}-{str(datetime.datetime.now()).replace(' ', '_').replace(':', '.')}.csv")

    return location

def extract_sprint_info(issue=None):

    sprint = ""

    try:
        raw = [str(sprint) for sprint in issue.fields.customfield_10760]
        sprint = re.findall(r"name=[^,]*", raw[-1])[0].split("=")[1]

    except BaseException as e:
        e_msg = f"Unable to extract sprint info for issue: {issue.key}"
        LOG.error(e_msg)

    return sprint


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


def close_jira_session(client=None):

    click.secho(f"[INFO] Closing JIRA session before leaving program...", fg="green")
    client.kill_session()

# -------


def write_results_to_file(csv_writer=None, entries=None):

    """
    :param csv_writer:
    :param entries:
    """
    for i in entries:
        issue_id = list(i.keys())[0]
        for data in i.values():
            data["total_blocked_time"] = "Still Blocked"
            if data["unblocked_at"] != "":
                delta = (data["unblocked_at"] - data["blocked_at"]).total_seconds()
                data["total_blocked_time"] = time_format(delta)

            csv_writer.writerow(
                [issue_id, data["blocked_at"], data["unblocked_at"], data["total_blocked_time"], data["block_type"],
                 data['sprint'], data["issue_type"]])


def get_transitions_by_query(client=None, query=None, location=None):
    next_page_starts_at = 0
    available_results = True

    with open(file=location, mode='w') as exported_results:

        csv_writer = csv.writer(exported_results, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        headers = ["ID", "Blocked At", "Unblocked At", "Total Blocked Time", "Blocked Type", "Sprint", "Issue Type"]
        csv_writer.writerow(headers)

        click.secho(f"[INFO] Calculating report rows...", fg="green")

        unblocked_at = None
        entries = []
        while available_results:
            _issues = client.search_issues(jql_str=query, startAt=next_page_starts_at-1,  maxResults=20, expand="Names")
            available_results = len(_issues) > 0

            for issue in _issues:
                changelog = client.issue(id=issue.id, expand='changelog,transitions')
                # for each issue get the changelog histories
                for history in changelog.changelog.histories:
                    # each history has more than one action
                    # like the user has changed the status, the assignee, etc
                    for item in history.items:

                        if item.field == "status":      # the user has changed the status

                            # if the status has changed to "Blocked"
                            # then we get the date of the change
                            if item.toString == "Blocked":

                                unblocked_at = None

                                entry = {issue.key: {}}
                                blocked_at = history.created

                                entry[issue.key]["blocked_at"] = get_pst(blocked_at)
                                entry[issue.key]['sprint'] = extract_sprint_info(issue=issue)

                            elif item.fromString == "Blocked":
                                unblocked_at = history.created
                                entry[issue.key]["unblocked_at"] = get_pst(unblocked_at)
                                entry[issue.key]["block_type"] = blocked_type
                                entry[issue.key]["issue_type"] = issue.fields.issuetype.name
                                entries.append(entry)
                        # end if item.field == "status"
                        elif item.field == "Block Type":
                            blocked_type = item.toString
                        else:
                            continue
                    # end for item in history.items
                # end for history in changelog.changelog.histories
                if not unblocked_at:
                    try:
                        entry[issue.key]["unblocked_at"] = ""
                        entry[issue.key]["block_type"] = blocked_type
                        entry[issue.key]["issue_type"] = issue.fields.issuetype.name
                        entries.append(entry)
                    except:
                        LOG.error(f"Unable to write entry for issue: {issue.key}")
                # end if not unblocked_at
                next_page_starts_at = next_page_starts_at + 1
            # end for issue in _issues
        # end while available_results
        # write results to file
        write_results_to_file(csv_writer=csv_writer, entries=entries)

    click.secho(f"[INFO] Exported results to file {os.path.join(EXPORT_DIRECTORY, os.path.basename(location))}", fg="green")


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
