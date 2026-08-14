import subprocess
from pathlib import Path

import pytest

from generate_repo_overview.collector.git_checkout import (
    fetch_repository_ref,
    get_checkout_head_date,
    get_checkout_head_sha,
    list_repository_paths,
    read_repository_text,
    read_repository_text_at_ref,
    remote_repository_has_refs,
    sync_repository_checkout,
)
from generate_repo_overview.constants import default_repository_checkout_cache


def test_default_checkout_cache_uses_xdg_location(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    assert default_repository_checkout_cache() == tmp_path / "repo-cache"


def test_checkout_syncs_branch_and_reads_release_ref(tmp_path: Path) -> None:
    source = tmp_path / "source"
    checkout = tmp_path / "checkout"
    _git(source.parent, "init", "--initial-branch=main", str(source))
    _git(source, "config", "user.name", "Test User")
    _git(source, "config", "user.email", "test@example.com")
    (source / "MODULE.bazel").write_text(
        'module(name = "score_example")\n',
        encoding="utf-8",
    )
    _git(source, "add", "MODULE.bazel")
    _git(source, "commit", "-m", "initial")
    _git(source, "tag", "v1.0.0")

    synced = sync_repository_checkout(
        clone_url=str(source),
        default_branch="main",
        github_token=None,
        checkout_path=checkout,
    )

    assert synced == checkout
    assert "MODULE.bazel" in list_repository_paths(checkout)
    assert read_repository_text(checkout, "MODULE.bazel") == (
        'module(name = "score_example")\n'
    )
    initial_sha = get_checkout_head_sha(checkout)
    assert initial_sha
    assert get_checkout_head_date(checkout)

    (source / ".bazelversion").write_text("8.4.2\n", encoding="utf-8")
    _git(source, "add", ".bazelversion")
    _git(source, "commit", "-m", "update")
    assert (
        sync_repository_checkout(
            clone_url=str(source),
            default_branch="main",
            github_token=None,
            checkout_path=checkout,
        )
        == checkout
    )
    assert get_checkout_head_sha(checkout) != initial_sha

    release_ref = fetch_repository_ref(
        checkout,
        "v1.0.0",
        github_token=None,
    )
    assert release_ref
    assert (
        read_repository_text_at_ref(
            checkout,
            release_ref,
            "MODULE.bazel",
        )
        == 'module(name = "score_example")'
    )


def test_empty_repository_has_no_remote_refs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    checkout = tmp_path / "checkout"
    _git(source.parent, "init", "--initial-branch=main", str(source))

    assert remote_repository_has_refs(str(source), github_token=None) is False
    assert (
        sync_repository_checkout(
            clone_url=str(source),
            default_branch="main",
            github_token=None,
            checkout_path=checkout,
        )
        is None
    )


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
