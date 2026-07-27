from github import GithubException

from connect_agent.github_publisher import (
    GitHubConfig,
    GitHubPublishError,
    build_repository_path,
    publish_files,
)
import pytest


class _Named:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeRef:
    def __init__(self, sha):
        self.object = _Named(sha=sha)
        self.edited_sha = None

    def edit(self, sha):
        self.edited_sha = sha


class FakeRepo:
    """Minimal stand-in for github.Repository used by the commit path."""

    def __init__(self, *, full_name="my-org/connect-infra", default_branch="main",
                 existing_branches=("main",)):
        self.full_name = full_name
        self.default_branch = default_branch
        self._existing = set(existing_branches)
        self.ref = FakeRef("base-sha")
        self.created_refs = []
        self.blobs = []
        self.tree_elements = None
        self.base_tree = None
        self.commit_message = None
        self.commit_parents = None

    def get_git_ref(self, ref_name):
        branch = ref_name.split("heads/", 1)[-1]
        if branch not in self._existing:
            raise GithubException(404, {"message": "Not Found"}, None)
        return self.ref

    def get_branch(self, name):
        return _Named(commit=_Named(sha="default-sha"))

    def create_git_ref(self, ref, sha):
        self.created_refs.append((ref, sha))
        self.ref = FakeRef(sha)
        return self.ref

    def get_git_commit(self, sha):
        return _Named(sha=sha, tree=_Named(sha="base-tree"))

    def create_git_blob(self, content, encoding):
        blob = _Named(sha=f"blob-{len(self.blobs)}", content=content, encoding=encoding)
        self.blobs.append(blob)
        return blob

    def create_git_tree(self, tree, base_tree):
        self.tree_elements = tree
        self.base_tree = base_tree
        return _Named(sha="new-tree")

    def create_git_commit(self, message, tree, parents):
        self.commit_message = message
        self.commit_parents = parents
        return _Named(sha="commit-sha")


class FakeClient:
    def __init__(self, repo):
        self.repo = repo
        self.requested = None
        self.closed = False

    def get_repo(self, full_name):
        self.requested = full_name
        return self.repo

    def close(self):
        self.closed = True


FILES = {"main.tf": "resource {}", "variables.tf": "variable {}"}


def _config(**overrides):
    base = dict(
        token="tok",
        repo_full_name="my-org/connect-infra",
        branch="main",
        target_directory="terraform",
    )
    base.update(overrides)
    return GitHubConfig(**base)


def test_build_repository_path_normalizes_separators_and_dots():
    assert build_repository_path("terraform", "main.tf") == "terraform/main.tf"
    assert build_repository_path("./infra\\connect/", "main.tf") == "infra/connect/main.tf"
    assert build_repository_path("", "main.tf") == "main.tf"


def test_publish_commits_all_files_as_single_commit():
    repo = FakeRepo()
    client = FakeClient(repo)
    result = publish_files(_config(), FILES, "Add Terraform", client=client)

    assert client.requested == "my-org/connect-infra"
    assert client.closed is False  # injected clients are not closed by the publisher
    assert len(repo.blobs) == 2
    assert repo.commit_message == "Add Terraform"
    assert repo.ref.edited_sha == "commit-sha"
    assert result.branch_created is False
    assert result.commit_sha == "commit-sha"
    assert result.commit_url == "https://github.com/my-org/connect-infra/commit/commit-sha"
    assert result.file_paths == ["terraform/main.tf", "terraform/variables.tf"]


def test_publish_creates_missing_branch_from_default():
    repo = FakeRepo(existing_branches=("main",))
    client = FakeClient(repo)
    result = publish_files(_config(branch="feature/connect"), FILES, "msg", client=client)

    assert repo.created_refs == [("refs/heads/feature/connect", "default-sha")]
    assert result.branch_created is True
    assert result.branch == "feature/connect"


def test_publish_targets_repository_root_when_directory_blank():
    repo = FakeRepo()
    client = FakeClient(repo)
    result = publish_files(_config(target_directory=""), FILES, "msg", client=client)
    assert result.file_paths == ["main.tf", "variables.tf"]


def test_publish_requires_repository():
    with pytest.raises(GitHubPublishError, match="owner/name"):
        publish_files(_config(repo_full_name="not-a-repo"), FILES, "msg", client=FakeClient(FakeRepo()))


def test_publish_requires_files():
    with pytest.raises(GitHubPublishError, match="no generated files"):
        publish_files(_config(), {}, "msg", client=FakeClient(FakeRepo()))


def test_publish_requires_token_without_injected_client():
    with pytest.raises(GitHubPublishError, match="token is required"):
        publish_files(_config(token=""), FILES, "msg")


def test_publish_wraps_github_errors():
    class FailingClient:
        def get_repo(self, full_name):
            raise GithubException(403, {"message": "Resource not accessible"}, None)

    with pytest.raises(GitHubPublishError, match="403"):
        publish_files(_config(), FILES, "msg", client=FailingClient())
