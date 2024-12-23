"""Get GitHub starred repositories and latest release."""

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich import print as pprint
from rich.columns import Columns
from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from tzlocal import get_localzone

from ghst.github_client import (
    create_github_client,
    get_latest_releases,
    get_starred_repos,
)

log = logging.getLogger("ghst")
app = typer.Typer(add_completion=False)


@app.command()
def cli(
    days: Annotated[int, typer.Option(help="Number of days to look back.")] = 7,
    limit: Annotated[
        int | None, typer.Option(help="Limit the number of repos (for debugging).")
    ] = None,
    verbose: Annotated[
        bool, typer.Option("-v", "--verbose", help="More verbose output.")
    ] = False,
    debug: Annotated[bool, typer.Option(help="Show debug output.")] = False,
):
    """Command line interface."""
    logging.getLogger().setLevel(logging.DEBUG if debug else logging.INFO)

    # See if we have a GitHub token
    token = retrieve_or_prompt_token()
    client = create_github_client(token)

    # Use the token to get the user's starred repositories
    starred = get_starred_repos(client=client, limit=limit or None)
    display_starred_repositories(starred)

    # Get the latest releases for the starred repositories
    lookback_date = dt.datetime.now(tz=get_localzone()) - dt.timedelta(days=days)
    pprint(Rule(title=f"Releases since {lookback_date:%Y-%m-%d %H:%M}"))
    releases = get_latest_releases(starred, cutoff_date=lookback_date)
    if not releases:
        pprint("[i]No recent releases found.[/i]")
        return

    # Print the latest releases
    display_recent_releases(starred=starred, releases=releases, include_body=verbose)


def display_recent_releases(*, starred, releases, include_body=False):
    """Display the recent releases in a pretty format."""
    repos_by_full_name = {repo.full_name: repo for repo in starred}
    tz = get_localzone()

    table = Table(
        "repo", "title", "published at", "released by", title="Recent releases"
    )

    for full_name, release in sorted(releases.items(), key=lambda x: x[1].published_at):
        repo = repos_by_full_name[full_name]
        published_at = release.published_at.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        by = release.author

        if include_body:
            release_info_panel = Panel.fit(
                Group(
                    Panel.fit(f"{repo.name} ({repo.stargazers_count:_} :star:)"),
                    Markdown(release.body or "_No description_"),
                ),
                title=f"Release notes for {full_name}",
                subtitle=f"Published at {published_at}",
            )
            pprint(release_info_panel)

        table.add_row(
            f"[link={repo.html_url}][b]{repo.name}[/b][/link] ({repo.stargazers_count:_} :star:)",
            f"[link={release.html_url}]{release.title}[/link]",
            published_at,
            f"{by.name} [link={by.html_url}]([blue]{by.login}[/blue])[/link]",
        )

    pprint(table)


def display_starred_repositories(starred):
    """Display the user's starred repositories in a column layout."""
    pprint(Rule(title="Your starred repositories"))
    names = sorted((repo.name for repo in starred), key=lambda x: x.lower())
    columns = Columns(names, column_first=True)
    pprint(columns)


def retrieve_or_prompt_token() -> str:
    """Retrieve the GitHub token from a file or prompt the user for it."""
    app_dir = Path(typer.get_app_dir("ghst"))
    token_file = app_dir / "token.json"
    log.debug(f"Token file: {token_file}")
    if not (token := load_token(token_file)):
        token = prompt_and_save_token(token_file)
    return token


def prompt_and_save_token(token_file: Path) -> str:
    """Prompt the user for a GitHub token and save it to a JSON file."""
    token = typer.prompt("Enter your GitHub token")
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(json.dumps({"token": token}))
    return token


def load_token(json_file: Path) -> str | None:
    """Load the GitHub token from a JSON file."""
    try:
        return json.loads(json_file.read_text())["token"]
    except FileNotFoundError:
        log.error(f"Token file not found: {json_file}")
    except json.JSONDecodeError:
        log.error(f"Invalid JSON in token file: {json_file}")
    return None


if __name__ == "__main__":
    app()
