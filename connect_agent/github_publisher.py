"""Publish generated Terraform files to a GitHub repository using PyGithub.

The application renders Terraform as a ``dict[str, str]`` of filename to content.
This module commits that same mapping into a Git repository as a single atomic
commit through the GitHub Git Data API, so the downloadable ZIP and the committed
tree always contain identical files. Terraform is never applied here; the tool only
writes source files that a human reviews before running ``terraform plan``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class GitHubPublishError(RuntimeError):
    """Raised when publishing generated Terraform to GitHub fails."""


@dataclass(frozen=True)
class GitHubConfig:
    """Everything needed to commit files to one repository and branch."""

    token: str
    repo_full_name: str
    branch: str = "main"
    target_directory: str = "terraform"
    base_url: str | None = None


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a successful commit."""

    repo_full_name: str
    branch: str
    branch_created: bool
    commit_sha: str
    commit_url: str
    file_paths: list[str] = field(default_factory=list)


def github_defaults_from_env() -> dict[str, str | None]:
    """Read optional GitHub defaults from the environment to prefill the form.

    A token supplied here is a convenience for local use only; the UI still
    lets the operator override or clear it per request.
    """
    return {
        "token": os.getenv("GITHUB_TOKEN", ""),
        "repo_full_name": os.getenv("GITHUB_REPOSITORY", ""),
        "branch": os.getenv("GITHUB_BRANCH", "") or "main",
        "target_directory": os.getenv("GITHUB_TARGET_DIRECTORY", "") or "terraform",
        # GITHUB_API_URL lets the tool target GitHub Enterprise Server.
        "base_url": os.getenv("GITHUB_API_URL") or None,
    }


def build_repository_path(target_directory: str, filename: str) -> str:
    """Join a target directory and file name into a POSIX repository path.

    GitHub paths always use forward slashes and are relative to the repository
    root, so backslashes, leading slashes, and ``.`` segments are stripped.
    """
    normalized = target_directory.replace("\\", "/")
    parts = [segment for segment in normalized.split("/") if segment and segment != "."]
    parts.append(filename)
    return "/".join(parts)


def _build_client(token: str, base_url: str | None):
    from github import Auth, Github

    auth = Auth.Token(token)
    if base_url:
        return Github(base_url=base_url, auth=auth)
    return Github(auth=auth)


def _describe_error(exc: Exception) -> str:
    from github import GithubException

    if isinstance(exc, GithubException):
        message = ""
        data = getattr(exc, "data", None)
        if isinstance(data, dict):
            message = str(data.get("message", "")).strip()
        status = getattr(exc, "status", None)
        if message and status:
            return f"GitHub returned {status}: {message}"
        if message:
            return message
        if status:
            return f"GitHub returned HTTP {status}."
    return str(exc) or exc.__class__.__name__


def _resolve_branch_ref(repo, branch: str) -> tuple[object, bool]:
    """Return the branch ref, creating it from the default branch if missing."""
    from github import GithubException

    ref_name = f"heads/{branch}"
    try:
        return repo.get_git_ref(ref_name), False
    except GithubException as exc:
        if getattr(exc, "status", None) != 404:
            raise
    source = repo.get_branch(repo.default_branch)
    ref = repo.create_git_ref(f"refs/{ref_name}", source.commit.sha)
    return ref, True


def _commit_files(
    repo, config: GitHubConfig, files: dict[str, str], commit_message: str
) -> PublishResult:
    from github import InputGitTreeElement

    ref, branch_created = _resolve_branch_ref(repo, config.branch)
    latest_commit = repo.get_git_commit(ref.object.sha)
    base_tree = latest_commit.tree

    elements: list[InputGitTreeElement] = []
    file_paths: list[str] = []
    for filename, content in files.items():
        path = build_repository_path(config.target_directory, filename)
        blob = repo.create_git_blob(content, "utf-8")
        elements.append(
            InputGitTreeElement(path=path, mode="100644", type="blob", sha=blob.sha)
        )
        file_paths.append(path)

    new_tree = repo.create_git_tree(elements, base_tree)
    new_commit = repo.create_git_commit(commit_message, new_tree, [latest_commit])
    ref.edit(new_commit.sha)

    commit_url = f"https://github.com/{repo.full_name}/commit/{new_commit.sha}"
    return PublishResult(
        repo_full_name=repo.full_name,
        branch=config.branch,
        branch_created=branch_created,
        commit_sha=new_commit.sha,
        commit_url=commit_url,
        file_paths=file_paths,
    )


def publish_files(
    config: GitHubConfig,
    files: dict[str, str],
    commit_message: str,
    *,
    client=None,
) -> PublishResult:
    """Commit ``files`` to ``config.repo_full_name`` as one commit.

    ``client`` is injectable for testing; in normal use it is built from the
    configured token and optional base URL. Any GitHub API failure is wrapped in
    :class:`GitHubPublishError` with a human-readable message.
    """
    if not config.repo_full_name.strip():
        raise GitHubPublishError("A repository in owner/name form is required.")
    if "/" not in config.repo_full_name.strip("/"):
        raise GitHubPublishError("Repository must be in owner/name form, e.g. my-org/connect-infra.")
    if not files:
        raise GitHubPublishError("There are no generated files to publish.")
    if client is None and not config.token.strip():
        raise GitHubPublishError("A GitHub token is required to publish.")

    owns_client = client is None
    if client is None:
        client = _build_client(config.token, config.base_url)

    try:
        repo = client.get_repo(config.repo_full_name.strip())
        return _commit_files(repo, config, files, commit_message)
    except GitHubPublishError:
        raise
    except Exception as exc:  # noqa: BLE001 - surfaced verbatim to the operator
        raise GitHubPublishError(_describe_error(exc)) from exc
    finally:
        if owns_client:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001 - closing must never mask the result
                    pass
