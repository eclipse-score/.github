"""The lockfile check runs a real fake `bazel` executable found on PATH."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import generate_repo_overview.collector.signal_detection as signal_detection
from generate_repo_overview.collector.signal_detection import (
    detect_bazel_lockfile_ok,
)
from generate_repo_overview.models import LockfileStatus

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
    monkeypatch.setattr(signal_detection, "BAZEL_LOCKFILE_TIMEOUT_SECONDS", 0.2)
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
