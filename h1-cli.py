
from collections import namedtuple
from pathlib import Path
import pickle
from pprint import pprint
import sys
from tempfile import TemporaryDirectory

import bugzilla
import click
import rich
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress
from rich.prompt import Prompt
from rich.table import Table

import h1lib




@click.group("h1-cli")
@click.option("-h1u", "--h1-key-username", help="HackerOne API key name", type=click.STRING, required=True,
              default="scott_f_bmo_exporter")
@click.option("--cache", help="Cache reports when possible", is_flag=True, default=False, show_default=False)
@click.option("--cache-path", help="Where the cache should be saved", default="/tmp/h1_cache",
              show_default=True, type=click.Path(dir_okay=False, writable=True, resolve_path=True))
@click.pass_context
def h1_cli(ctx, h1_key_username, cache, cache_path):
    # Rich console output for pretty printing
    # Switch 'quiet' to True to suppress all output. Defaults to False.
    # Add Rich Console to the context obj
    ctx.obj = {"console": Console(quiet=False)}
    console = ctx.obj["console"]

    h1_api_key = Prompt.ask(prompt=f"What is the HackerOne API key for {h1_key_username}", console=console)
    # Local cache path for dev work
    local_cache_path = Path(cache_path)

    # Update the context object provided by Click with global variables
    ctx.obj.update({"h1_api_key": h1_api_key, "local_cache_path": local_cache_path})

@h1_cli.command("show")
@click.argument("h1-report-id", type=click.INT)
@click.option("-m", "--markdown", help="Print the report information with Markdown", default=False,
              is_flag=True, show_default=True)
@click.pass_context
def h1_exporter(ctx, h1_report_id, markdown):
    """
    Print H1 report to screen with the correct formatting
    """
    console: Console = ctx.obj["console"]
    h1_api_key = ctx.obj["h1_api_key"]
    local_cache_path = ctx.obj["local_cache_path"]
    cache = ctx.parent.params["cache"]
    h1_key_username = ctx.parent.params["h1_key_username"]

    session = h1lib.HackerOneSession(username=h1_key_username, token=h1_api_key, console=console, cache=cache,
                                     local_cache_path=local_cache_path)
    report = session.get_report(h1_report_id)
    if markdown:
        console.print(Markdown(report.formatted_report_title))
        console.print(Markdown(report.formatted_report_body))
    else:
        console.print(report.formatted_report_title)
        console.print(report.formatted_report_body, markup=False)


@h1_cli.command("upload-bmo")
@click.option("--bugzilla-url", default="https://bugzilla-dev.allizom.org/xmlrpc.cgi", show_default=True,
              help="Bugzilla instance URL")
@click.argument("h1-report-id", type=click.INT)
@click.pass_context
def upload_bmo(ctx, h1_report_id, bugzilla_url):
    """Upload a HackerOne report to Bugzilla"""
    console: Console = ctx.obj["console"]
    h1_api_key = ctx.obj["h1_api_key"]
    local_cache_path = ctx.obj["local_cache_path"]
    h1_key_username = ctx.parent.params["h1_key_username"]
    cache = ctx.parent.params["cache"]

    bmo_api_key = Prompt.ask(prompt=f"What is the Bugzilla API key", console=console)
    bzapi = bugzilla.Bugzilla(bugzilla_url, api_key=bmo_api_key)
    session = h1lib.HackerOneSession(username=h1_key_username, token=h1_api_key, console=console,
                                     cache=cache)
    report = session.get_report(h1_report_id)
    # console.print(report.raw_report_dict)
    attachments_list = session.get_attachments(report)

    # Create bugzilla report object
    create_info = report.h1_bug_converter(bzapi)

    # Create the bug report
    new_bug = bzapi.createbug(create_info)
    pprint(f"{h1lib.success_msg} Created a bug with ID: {new_bug.id}\nURL: {new_bug.weburl}")

    # Download each attachment and save it to a temp file
    with TemporaryDirectory(dir="/tmp/") as tmpdirname:
        tmpdirname_path = Path(tmpdirname)
        tmpdirname_path.mkdir(exist_ok=True)

        # Each attachment gets downloaded
        for attachment_obj in attachments_list:
            # Download each attachment and save it to disk
            attachment_save_path = attachment_obj.download_attachment(save_dir_path=tmpdirname_path)

            # Open file and attach it to the bug
            with open(attachment_save_path, 'rb') as f:
                resp = bzapi.attachfile(idlist=[new_bug.id], attachfile=f, description=attachment_obj.file_name)
    pprint(f"{h1lib.success_msg} Uploaded attachments to bug: {new_bug.weburl}")


if __name__ == '__main__':
    h1_cli()
