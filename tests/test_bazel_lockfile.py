"""Collection only records whether a Bazel module commits its lockfile."""

import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import generate_repo_overview.collector.repo_entry as repo_entry
from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    RepoEntry,
    RepoSnapshot,
)


@pytest.fixture
def bazel_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Put a `bazel` on PATH that records every call."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "bazel.log"
    log.touch()
    bazel = bin_dir / "bazel"
    bazel.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n', encoding="utf-8")
    bazel.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir), prepend=":")
    return log


def _collect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, *files: str
) -> RepoEntry:
    checkout = tmp_path / name
    checkout.mkdir()
    for file in files:
        (checkout / file).touch()
    git = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com"]
    subprocess.run([*git, "init", "-q", "-b", "main"], cwd=checkout, check=True)
    subprocess.run([*git, "add", "."], cwd=checkout, check=True)
    subprocess.run([*git, "commit", "-q", "-m", "Initial"], cwd=checkout, check=True)
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
        repository_name=name,
        repository=SimpleNamespace(default_branch="main", description=name),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=None,
    )


def _automation_row(index: str, name: str) -> str:
    rows = re.findall(rf'<tr[^>]*data-repo-filter="{name}".*?</tr>', index, re.S)
    # The automation table is the one with the commit message rules column.
    row = next((row for row in rows if "commit message formatting" in row), None)
    assert row, f"no automation row for {name}"
    return row


def test_collection_records_the_lockfile_without_running_bazel(
    bazel_calls: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    locked = _collect(
        monkeypatch, tmp_path, "locked", "MODULE.bazel", "MODULE.bazel.lock"
    )
    unlocked = _collect(monkeypatch, tmp_path, "unlocked", "MODULE.bazel")
    plain = _collect(monkeypatch, tmp_path, "plain", "README.md")

    assert locked.content.has_bazel_lockfile
    assert not unlocked.content.has_bazel_lockfile
    assert bazel_calls.read_text(encoding="utf-8") == ""

    index = render_all_pages(
        RepoSnapshot(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            org_name="example",
            generated_at="2026-01-01T00:00:00+00:00",
            repos=(locked, unlocked, plain),
        )
    )["index.html"]
    assert "MODULE.bazel.lock is committed." in _automation_row(index, "locked")
    assert '<span class="badge yellow">missing</span>' in _automation_row(
        index, "unlocked"
    )
    assert "Not a Bazel module repository." in _automation_row(index, "plain")


@pytest.mark.parametrize(
    ("status", "has_lockfile"),
    [
        ("ok", True),
        ("error", True),
        ("timeout", True),
        ("skipped", True),
        ("missing", False),
        ("unknown", False),
    ],
)
def test_older_snapshot_lockfile_status_becomes_presence(
    status: str, *, has_lockfile: bool
) -> None:
    content = DeepContentSignals.from_dict(
        {"has_bazel_module": True, "bazel_lockfile_status": status}
    )

    assert content.has_bazel_lockfile is has_lockfile
