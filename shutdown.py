# By Jaziel Lopez (github.com/jazlopez)
# See license file

import click

# -------
def teardown(exit_code=1):

    if exit_code > 0:
        click.secho("[ERROR] An error has occurred and will exit the program now. See logs for error details", fg="red")
        exit(code=exit_code)

    click.secho("[INFO] Program exits now... Good bye", fg="green")
    exit(code=0)
