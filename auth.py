# By  Jaziel Lopez (github.com/jazlopez)
# See license file

import os
import time
import logging
import click
from jira import JIRA
from shutdown import teardown

auth = {
    'url': None,
    'user': None,
    'password': None
}


def authenticate(logger:logging.Logger=None) -> JIRA:

    """
      Initiate an authorization login workflow via JIRA api
    """

    logger.info("*************** JIRA AUTHENTICATE AUTOMATION ****************")
    # time.sleep(1)

    logger.info("Checking for environment variables to login [JIRA_URL, JIRA_USER,JIRA_PASSWD")
    # time.sleep(1)
    env_jira_url = os.getenv('JIRA_URL', None)
    env_jira_user = os.getenv("JIRA_USER", None)
    env_jira_passwd = os.getenv("JIRA_PASSWD", None)

    logger.info("[LOGIN]")
    logger.info("Using credentials from environment variables")

    auth['url'] = env_jira_url
    auth['user'] = env_jira_user
    auth['password'] = env_jira_passwd
    try:

        client = JIRA(auth['url'], auth=(auth['user'], auth['password']), max_retries=0)

        logger.info("[INFO]")
        logger.info("You have successfully authenticated with provided credentials")

        return client
    except Exception as e:
        logger.error(e)
        teardown(exit_code=1)


if __name__ == '__main__':
    click.secho("[ERROR] You cannot execute this script directly", fg='red')
    exit(1)
