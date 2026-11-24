"""The lockfile check runs a real fake `bazel` executable found on PATH."""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import generate_repo_overview.collector.repo_entry as repo_entry
import generate_repo_overview.collector.signal_detection as signal_detection
from generate_repo_overview.collector.signal_detection import (
    detect_bazel_lockfile_ok,
)
from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    LockfileStatus,
    RepoEntry,
    RepoSnapshot,
)
from generate_repo_overview.org_config import load_org_config

FAKE_BAZEL = """#!/bin/sh
# Log one line per event: <checkout name> <startup option> <event>
name="$(basename "$PWD")"
case "$2" in
  mod)
    echo "$name $1 check-start" >> "$BAZEL_LOG"
    sleep "$(cat "$PWD/duration")"
    echo "$name $1 check-end" >> "$BAZEL_LOG"
    if [ -f "$PWD/outdated" ]; then
      echo "lockfile is out of date" >&2
      exit 1
    fi
    ;;
  shutdown)
    echo "$name $1 shutdown" >> "$BAZEL_LOG"
    ;;
esac
"""


@pytest.fixture
def bazel_log(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    bazel = bin_dir / "bazel"
    bazel.write_text(FAKE_BAZEL, encoding="utf-8")
    bazel.chmod(0o755)
    log = tmp_path / "bazel.log"
    log.touch()
    monkeypatch.setenv("PATH", str(bin_dir), prepend=":")
    monkeypatch.setenv("BAZEL_LOG", str(log))
    return log


def _checkout(tmp_path: Path, name: str, *, duration: str = "0") -> Path:
    checkout = tmp_path / name
    checkout.mkdir()
    (checkout / "MODULE.bazel").touch()
    (checkout / "MODULE.bazel.lock").touch()
    (checkout / "duration").write_text(duration, encoding="utf-8")
    return checkout


def _events(log: Path) -> list[list[str]]:
    return [line.split() for line in log.read_text(encoding="utf-8").splitlines()]


def test_parallel_collection_runs_one_lockfile_check_at_a_time(
    bazel_log: Path, tmp_path: Path
) -> None:
    checkouts = [
        _checkout(tmp_path, f"repo{index}", duration="0.2") for index in range(4)
    ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(detect_bazel_lockfile_ok, checkouts))

    assert results == [(LockfileStatus.OK, None)] * 4
    events = _events(bazel_log)
    # Each repository finishes its check and stops its server before the next
    # check starts.
    assert [event for _, _, event in events] == [
        "check-start",
        "check-end",
        "shutdown",
    ] * 4
    for index in range(0, len(events), 3):
        assert len({name for name, _, _ in events[index : index + 3]}) == 1
    # Different startup options would make the shutdown restart the server.
    assert len({option for _, option, _ in events}) == 1


def test_outdated_lockfile_reports_error_and_stops_the_server(
    bazel_log: Path, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")
    (checkout / "outdated").touch()

    assert detect_bazel_lockfile_ok(checkout) == (
        LockfileStatus.ERROR,
        "lockfile is out of date",
    )
    assert _events(bazel_log)[-1][2] == "shutdown"


def test_timed_out_check_stops_the_server(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REPO_OVERVIEW_BAZEL_LOCKFILE_TIMEOUT_SECONDS", "0.2")
    checkout = _checkout(tmp_path, "repo", duration="5")

    assert detect_bazel_lockfile_ok(checkout) == (LockfileStatus.TIMEOUT, None)
    assert [event for _, _, event in _events(bazel_log)] == [
        "check-start",
        "shutdown",
    ]


def test_repository_without_lockfile_does_not_start_bazel(
    bazel_log: Path, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")
    (checkout / "MODULE.bazel.lock").unlink()

    assert detect_bazel_lockfile_ok(checkout) == (LockfileStatus.MISSING, None)
    assert _events(bazel_log) == []


def _collect_entry(
    monkeypatch: pytest.MonkeyPatch,
    checkout: Path,
    *,
    run_repository_tools: bool,
    cached_entry: RepoEntry | None = None,
) -> RepoEntry:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=checkout, check=True)
    subprocess.run(["git", "add", "."], cwd=checkout, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "Initial commit",
        ],
        cwd=checkout,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    monkeypatch.setattr(
        repo_entry, "_sync_content_checkout", lambda **_kwargs: (checkout, head)
    )
    return repo_entry.collect_repository_entry(
        repository_name="repo",
        repository=SimpleNamespace(default_branch="main", description="Repo"),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=cached_entry,
        run_repository_tools=run_repository_tools,
    )


def test_organization_without_repository_tools_never_starts_bazel(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")

    entry = _collect_entry(monkeypatch, checkout, run_repository_tools=False)

    assert entry.content.bazel_lockfile_status == LockfileStatus.SKIPPED
    assert _events(bazel_log) == []

    index = render_all_pages(
        RepoSnapshot(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            org_name="example",
            generated_at="2026-01-01T00:00:00+00:00",
            repos=(entry,),
        )
    )["index.html"]
    assert "Repository tools are disabled for this organization" in index


def test_skipped_lockfile_is_checked_once_repository_tools_are_enabled(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")
    skipped = _collect_entry(monkeypatch, checkout, run_repository_tools=False)

    # The repository is unchanged, but its cached status no longer applies.
    entry = repo_entry.collect_repository_entry(
        repository_name="repo",
        repository=SimpleNamespace(default_branch="main", description="Repo"),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=skipped,
        run_repository_tools=True,
    )

    assert entry.content.bazel_lockfile_status == LockfileStatus.OK
    assert [event for _, _, event in _events(bazel_log)] == [
        "check-start",
        "check-end",
        "shutdown",
    ]


def test_only_the_primary_organization_runs_repository_tools_by_default(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "org.toml"
    config_path.write_text(
        """
org_name = "primary"

[organizations.untrusted]

[organizations.trusted]
run_repository_tools = true
""",
        encoding="utf-8",
    )

    configs = load_org_config(config_path).collection_configs()

    assert {config.org_name: config.run_repository_tools for config in configs} == {
        "primary": True,
        "untrusted": False,
        "trusted": True,
    }


def test_repository_tools_setting_must_be_a_boolean(tmp_path: Path) -> None:
    config_path = tmp_path / "org.toml"
    config_path.write_text(
        'org_name = "primary"\nrun_repository_tools = "no"\n', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="run_repository_tools must be true or false"):
        load_org_config(config_path)


def test_checked_lockfile_becomes_skipped_once_repository_tools_are_disabled(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")
    checked = _collect_entry(monkeypatch, checkout, run_repository_tools=True)
    assert checked.content.bazel_lockfile_status == LockfileStatus.OK
    bazel_log.write_text("", encoding="utf-8")

    entry = repo_entry.collect_repository_entry(
        repository_name="repo",
        repository=SimpleNamespace(default_branch="main", description="Repo"),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=checked,
        run_repository_tools=False,
    )

    assert entry.content.bazel_lockfile_status == LockfileStatus.SKIPPED
    assert _events(bazel_log) == []


def test_missing_lockfile_is_reported_without_repository_tools(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")
    (checkout / "MODULE.bazel.lock").unlink()

    entry = _collect_entry(monkeypatch, checkout, run_repository_tools=False)

    assert entry.content.bazel_lockfile_status == LockfileStatus.MISSING
    assert _events(bazel_log) == []

    # The status needs no Bazel, so the unchanged repository is reused as is.
    monkeypatch.setattr(
        repo_entry,
        "inspect_repository_checkout",
        lambda *_args, **_kwargs: pytest.fail("repository was inspected again"),
    )
    reused = repo_entry.collect_repository_entry(
        repository_name="repo",
        repository=SimpleNamespace(default_branch="main", description="Repo"),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=entry,
        run_repository_tools=False,
    )
    assert reused.content.bazel_lockfile_status == LockfileStatus.MISSING


@pytest.mark.parametrize(
    "value", ["", "soon", "0", "-5", "nan", "inf", "1e300", "86401"]
)
def test_invalid_lockfile_timeout_uses_the_default(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("REPO_OVERVIEW_BAZEL_LOCKFILE_TIMEOUT_SECONDS", value)

    assert signal_detection.resolve_bazel_lockfile_timeout_seconds() == 120


def _collect_unchanged(cached_entry: RepoEntry) -> RepoEntry:
    return repo_entry.collect_repository_entry(
        repository_name="repo",
        repository=SimpleNamespace(default_branch="main", description="Repo"),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=cached_entry,
    )


def test_timed_out_lockfile_check_is_repeated_for_an_unchanged_repository(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo", duration="5")
    # The duration file is untracked, so changing it keeps the commit.
    (checkout / ".gitignore").write_text("duration\n", encoding="utf-8")
    monkeypatch.setenv("REPO_OVERVIEW_BAZEL_LOCKFILE_TIMEOUT_SECONDS", "0.2")
    timed_out = _collect_entry(monkeypatch, checkout, run_repository_tools=True)
    assert timed_out.content.bazel_lockfile_status == LockfileStatus.TIMEOUT

    (checkout / "duration").write_text("0", encoding="utf-8")
    monkeypatch.setattr(
        repo_entry,
        "inspect_repository_checkout",
        lambda *_args, **_kwargs: pytest.fail("repository was inspected again"),
    )
    entry = _collect_unchanged(timed_out)

    assert entry.content.bazel_lockfile_status == LockfileStatus.OK


def test_lockfile_error_is_kept_for_an_unchanged_repository(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")
    (checkout / "outdated").touch()
    failed = _collect_entry(monkeypatch, checkout, run_repository_tools=True)
    assert failed.content.bazel_lockfile_status == LockfileStatus.ERROR
    bazel_log.write_text("", encoding="utf-8")

    entry = _collect_unchanged(failed)

    assert entry.content.bazel_lockfile_status == LockfileStatus.ERROR
    assert _events(bazel_log) == []


def test_repository_cached_as_skipped_reports_its_missing_lockfile(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")
    (checkout / "MODULE.bazel.lock").unlink()
    entry = _collect_entry(monkeypatch, checkout, run_repository_tools=False)
    # Earlier versions recorded every repository without repository tools as skipped.
    cached = replace(
        entry,
        content=replace(entry.content, bazel_lockfile_status=LockfileStatus.SKIPPED),
    )

    upgraded = repo_entry.collect_repository_entry(
        repository_name="repo",
        repository=SimpleNamespace(default_branch="main", description="Repo"),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=cached,
        run_repository_tools=False,
    )

    assert upgraded.content.bazel_lockfile_status == LockfileStatus.MISSING
    assert _events(bazel_log) == []


def test_check_without_bazel_is_repeated_once_bazel_is_available(
    bazel_log: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout = _checkout(tmp_path, "repo")
    available = signal_detection._BAZEL_COMMAND
    monkeypatch.setattr(
        signal_detection, "_BAZEL_COMMAND", (str(tmp_path / "no-bazel"),)
    )
    without_bazel = _collect_entry(monkeypatch, checkout, run_repository_tools=True)
    assert without_bazel.content.bazel_lockfile_status == LockfileStatus.UNKNOWN

    monkeypatch.setattr(signal_detection, "_BAZEL_COMMAND", available)
    monkeypatch.setattr(
        repo_entry,
        "inspect_repository_checkout",
        lambda *_args, **_kwargs: pytest.fail("repository was inspected again"),
    )
    entry = _collect_unchanged(without_bazel)

    assert entry.content.bazel_lockfile_status == LockfileStatus.OK
