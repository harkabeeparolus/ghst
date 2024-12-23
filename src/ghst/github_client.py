"""Talk to the GitHub API."""

import datetime as dt
import logging

import github
from github.GitRelease import GitRelease
from github.Repository import Repository
from rich.progress import track

log = logging.getLogger("ghst.client")


def get_starred_repos(
    *, client: github.Github, limit: int | None = 0
) -> list[Repository]:
    """Get the user's starred repositories using the GitHub API."""
    result = []
    repos = client.get_user().get_starred()
    for repo in track(
        repos,
        description="Getting your starred repos",
        total=repos.totalCount,
        transient=True,
    ):
        result.append(repo)
        if limit and len(result) >= limit:
            break
    return result


def get_latest_releases(
    repos: list[Repository], cutoff_date: dt.datetime | None
) -> dict[str, GitRelease]:
    """Get the latest releases for a list of repositories.

    If a cutoff date is provided, only releases after that date are considered.

    The results are stored in a dictionary mapping repository full names to their latest release.

    Args:
        repos (list[Repository]): A list of GitHub repositories.

    Returns:
        dict[str, GitRelease]: A dictionary mapping repository full names to their latest release.

    Raises:
        github.GithubException: An error occurred while getting the release.
    """
    result = {}
    for repo in track(repos, description="Getting latest releases", transient=True):
        release = None
        try:
            release = repo.get_latest_release()
        except github.GithubException as exc:
            if exc.status == 404:
                log.debug(f"No releases found for {repo.full_name}")
                continue
            log.error(f"Error getting release for {repo.full_name}: {exc}")
        if release:
            if cutoff_date and release.published_at < cutoff_date:
                continue
            result[repo.full_name] = release
    return result


def create_github_client(token):
    """Create a GitHub client with the given token."""
    auth = github.Auth.Token(token)
    client = github.Github(auth=auth)
    return client
