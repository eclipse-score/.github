import subprocess
from pathlib import Path

import pytest

import generate_repo_overview.collector.dependency_resolution as dependency_resolution
from generate_repo_overview.models import (
    DeepContentSignals,
    DependencyDeclaration,
    DependencyOverride,
    DependencyResolution,
    RepoEntry,
    VolatileMetricsSnapshot,
)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(work: Path, message: str) -> str:
    git(work, "commit", "--allow-empty", "-m", message)
    return git(work, "rev-parse", "HEAD")


@pytest.fixture
def baselibs(tmp_path: Path) -> dict[str, str]:
    """A dependency with two releases, newer main commits, and a side branch."""
    work = tmp_path / "baselibs"
    git(tmp_path, "init", "--initial-branch=main", str(work))
    git(work, "config", "user.email", "test@example.com")
    git(work, "config", "user.name", "Test")
    commits = {"v1.0.0": commit(work, "release 1.0.0")}
    git(work, "tag", "-a", "v1.0.0", "-m", "1.0.0")
    commit(work, "fix")
    commits["v1.1.0"] = commit(work, "release 1.1.0")
    git(work, "tag", "v1.1.0")
    commits["main"] = commit(work, "feature")
    git(work, "checkout", "-q", "-b", "experiment", commits["v1.0.0"])
    commits["experiment"] = commit(work, "experiment")
    git(work, "checkout", "-q", "main")
    return commits


def test_resolve_dependencies_compares_pins_with_release_and_default_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, baselibs: dict[str, str]
) -> None:
    cloned: list[str] = []

    def clone_history(*, repository: str, destination: Path) -> None:
        cloned.append(repository)
        git(
            tmp_path,
            "clone",
            "-q",
            "--bare",
            str(tmp_path / "baselibs"),
            str(destination),
        )

    monkeypatch.setattr(dependency_resolution, "sync_history", clone_history)
    dependency = RepoEntry(
        "baselibs",
        "",
        "Platform",
        "General",
        owner="eclipse-score",
        default_branch="main",
        content=DeepContentSignals(bazel_module_name="score_baselibs"),
        volatile=VolatileMetricsSnapshot(latest_release_version="v1.1.0"),
    )
    logging_remote = "https://github.com/eclipse-score/baselibs.git"
    consumer = RepoEntry(
        "consumer",
        "",
        "Platform",
        "General",
        owner="eclipse-score",
        content=DeepContentSignals(
            bazel_deps=(
                DependencyDeclaration("score_baselibs", "1.1.0"),
                DependencyDeclaration("rules_python", "1.0.0"),
            )
        ),
        volatile=VolatileMetricsSnapshot(
            release_bazel_deps=(DependencyDeclaration("score_baselibs", "1.0.0"),)
        ),
    )
    git_pinned = RepoEntry(
        "integration",
        "",
        "Platform",
        "General",
        owner="eclipse-score",
        content=DeepContentSignals(
            bazel_deps=(
                DependencyDeclaration(
                    "score_baselibs_fork",
                    "0.0.0",
                    DependencyOverride.GIT,
                    remote=logging_remote,
                    revision=baselibs["experiment"],
                ),
                DependencyDeclaration("score_baselibs", "9.9.9"),
            )
        ),
    )

    resolutions = dependency_resolution.resolve_dependencies(
        (dependency, consumer, git_pinned),
        {"score_baselibs": "eclipse-score/baselibs"},
        cache_directory=tmp_path / "cache",
    )

    assert cloned == ["eclipse-score/baselibs"]
    assert {r.revision: r for r in resolutions} == {
        # The latest release, but the default branch moved on.
        "1.1.0": DependencyResolution(
            "eclipse-score/baselibs",
            "1.1.0",
            resolved_sha=baselibs["v1.1.0"],
            latest_release="v1.1.0",
            behind_latest_release_by=0,
            ahead_of_default_branch_by=0,
            behind_default_branch_by=1,
        ),
        # The annotated tag resolves to its commit.
        "1.0.0": DependencyResolution(
            "eclipse-score/baselibs",
            "1.0.0",
            resolved_sha=baselibs["v1.0.0"],
            latest_release="v1.1.0",
            behind_latest_release_by=2,
            ahead_of_default_branch_by=0,
            behind_default_branch_by=3,
        ),
        # Diverged history must not look up to date.
        baselibs["experiment"]: DependencyResolution(
            "eclipse-score/baselibs",
            baselibs["experiment"],
            resolved_sha=baselibs["experiment"],
            latest_release="v1.1.0",
            behind_latest_release_by=2,
            ahead_of_default_branch_by=1,
            behind_default_branch_by=3,
        ),
        "9.9.9": DependencyResolution(
            "eclipse-score/baselibs", "9.9.9", latest_release="v1.1.0"
        ),
    }


def test_resolve_dependencies_skips_repositories_outside_the_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(**_kwargs: object) -> None:
        raise AssertionError("must not clone uncollected repositories")

    monkeypatch.setattr(dependency_resolution, "sync_history", fail)
    consumer = RepoEntry(
        "consumer",
        "",
        "Platform",
        "General",
        owner="eclipse-score",
        content=DeepContentSignals(
            bazel_deps=(DependencyDeclaration("score_external", "1.0.0"),)
        ),
    )

    assert (
        dependency_resolution.resolve_dependencies(
            (consumer,), {"score_external": "other-org/external"}
        )
        == ()
    )
