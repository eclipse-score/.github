import subprocess
from pathlib import Path

import pytest
from repo_cache import RepoCacheError

import generate_repo_overview.collector.git_checkout as git_checkout
from generate_repo_overview.collector.git_checkout import (
    fetch_repository_ref,
    get_checkout_head_date,
    get_checkout_head_sha,
    list_repository_paths,
    read_repository_text,
    read_repository_text_at_ref,
    remote_repository_has_refs,
)


def test_github_checkout_uses_shared_repo_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_sync(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(git_checkout, "sync_default_branch", fake_sync)
    checkout = tmp_path / "checkout"

    assert (
        git_checkout.sync_repository_checkout(
            repository="eclipse-score/tools",
            default_branch="main",
            checkout_path=checkout,
        )
        == checkout
    )
    assert calls == [
        {
            "repository": "eclipse-score/tools",
            "branch": "main",
            "destination": checkout,
        }
    ]


def test_github_checkout_failure_keeps_best_effort_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_sync(**_: object) -> None:
        raise RepoCacheError("checkout failed")

    monkeypatch.setattr(git_checkout, "sync_default_branch", fail_sync)

    assert (
        git_checkout.sync_repository_checkout(
            repository="eclipse-score/tools",
            default_branch="main",
            checkout_path=tmp_path / "checkout",
        )
        is None
    )


def test_checkout_helpers_read_release_ref(tmp_path: Path) -> None:
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

    subprocess.run(
        ["git", "clone", str(source), str(checkout)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "MODULE.bazel" in list_repository_paths(checkout)
    assert read_repository_text(checkout, "MODULE.bazel") == (
        'module(name = "score_example")\n'
    )
    initial_sha = get_checkout_head_sha(checkout)
    assert initial_sha
    assert get_checkout_head_date(checkout)

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
    _git(source.parent, "init", "--initial-branch=main", str(source))

    assert remote_repository_has_refs(str(source), github_token=None) is False


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
