import json
import subprocess
from pathlib import Path

import pytest

import generate_repo_overview.collector.dependency_resolution as dependency_resolution
from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    DependencyDeclaration,
    DependencyOverride,
    DependencyPinKind,
    DependencyResolution,
    RepoEntry,
    RepoSnapshot,
    VolatileMetricsSnapshot,
)
from generate_repo_overview.org_config import OrgConfig


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
    git(work, "tag", "experiment", commits["v1.1.0"])
    git(work, "branch", "9.9.9")
    return commits


def test_resolve_dependencies_compares_pins_with_release_and_default_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, baselibs: dict[str, str]
) -> None:
    cloned: list[str] = []

    def clone_history(
        *, repository: str, branch: str, destination: Path, history: bool
    ) -> None:
        assert history
        assert branch == "main"
        cloned.append(repository)
        destination.parent.mkdir(parents=True)
        git(
            tmp_path,
            "clone",
            "-q",
            "--branch",
            branch,
            str(tmp_path / "baselibs"),
            str(destination),
        )

    monkeypatch.setattr(dependency_resolution, "sync_default_branch", clone_history)
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
    dependency_remote = "https://github.com/eclipse-score/baselibs.git"
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
                    remote=dependency_remote,
                    revision=baselibs["experiment"],
                    pin_kind=DependencyPinKind.COMMIT,
                ),
                DependencyDeclaration(
                    "experiment_branch",
                    override=DependencyOverride.GIT,
                    remote=dependency_remote,
                    revision="experiment",
                    pin_kind=DependencyPinKind.BRANCH,
                ),
                DependencyDeclaration(
                    "experiment_tag",
                    override=DependencyOverride.GIT,
                    remote=dependency_remote,
                    revision="experiment",
                    pin_kind=DependencyPinKind.TAG,
                ),
                DependencyDeclaration("score_baselibs", "9.9.9"),
            )
        ),
    )

    _, resolutions = dependency_resolution.collect_dependencies(
        (dependency, consumer, git_pinned),
        (OrgConfig(org_name="eclipse-score"),),
        cache_directory=tmp_path / "cache",
    )

    assert cloned == ["eclipse-score/baselibs"]
    by_pin = {(r.pin_kind, r.revision): r for r in resolutions}
    assert (
        by_pin.pop((DependencyPinKind.BRANCH, "experiment")).resolved_sha
        == baselibs["experiment"]
    )
    assert (
        by_pin.pop((DependencyPinKind.TAG, "experiment")).resolved_sha
        == baselibs["v1.1.0"]
    )
    assert {r.revision: r for r in by_pin.values()} == {
        # The latest release, but the default branch moved on.
        "1.1.0": DependencyResolution(
            "eclipse-score/baselibs",
            "1.1.0",
            resolved_sha=baselibs["v1.1.0"],
            latest_release="v1.1.0",
            behind_latest_release_by=0,
            ahead_of_default_branch_by=0,
            behind_default_branch_by=1,
            consumer_org="eclipse-score",
            module="score_baselibs",
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
            consumer_org="eclipse-score",
            module="score_baselibs",
        ),
        # Diverged history must not look up to date.
        baselibs["experiment"]: DependencyResolution(
            "eclipse-score/baselibs",
            baselibs["experiment"],
            resolved_sha=baselibs["experiment"],
            ahead_of_default_branch_by=1,
            behind_default_branch_by=3,
            pin_kind=DependencyPinKind.COMMIT,
            consumer_org="eclipse-score",
            module="score_baselibs_fork",
        ),
        # A branch of the same name does not resolve a Bazel module version.
        "9.9.9": DependencyResolution(
            "eclipse-score/baselibs",
            "9.9.9",
            latest_release="v1.1.0",
            consumer_org="eclipse-score",
            module="score_baselibs",
        ),
    }


def test_resolve_dependencies_skips_repositories_outside_the_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(**_kwargs: object) -> None:
        raise AssertionError("must not clone uncollected repositories")

    monkeypatch.setattr(dependency_resolution, "sync_default_branch", fail)
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

    assert dependency_resolution.collect_dependencies(
        (consumer,), (OrgConfig(org_name="eclipse-score"),)
    ) == ({"eclipse-score": {}}, ())


def _write_registry_module(
    root: Path, repository: str, versions: dict[str, dict[str, str]]
) -> None:
    module = root / "modules/score_python_basics"
    module.mkdir(parents=True)
    (module / "metadata.json").write_text(
        json.dumps(
            {
                "repository": [f"github:{repository}"],
                "versions": list(versions),
                "yanked_versions": {"9.9.9": "broken"},
            }
        )
    )
    for version, source in versions.items():
        version_directory = module / version
        version_directory.mkdir()
        (version_directory / "source.json").write_text(json.dumps(source))


def test_registry_versions_and_consumers_use_their_organizations_registry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, baselibs: dict[str, str]
) -> None:
    # Both registries publish the same module/version name from different repos.
    # The root module and the repository-wide release belong to a different module.
    cache = tmp_path / "cache"
    first_source = "first-org/tooling"
    second_source = "second-org/tooling"
    _write_registry_module(
        cache / "first-org/registry",
        first_source,
        {
            "0.3.3": {"url": "https://example.com/opaque-release-0.3.3.tar.gz"},
            "0.3.4": {
                "url": f"https://github.com/{first_source}/archive/refs/tags/v1.0.0.tar.gz"
            },
            "9.9.9": {
                "url": f"https://github.com/{first_source}/archive/refs/tags/v1.1.0.tar.gz"
            },
            "0.3.5": {
                "type": "git_repository",
                "remote": f"https://github.com/{first_source}",
                "tag": "v1.1.0",
            },
        },
    )
    _write_registry_module(
        cache / "second-org/registry",
        second_source,
        {
            "0.3.4": {
                "url": f"https://github.com/{second_source}/archive/{baselibs['v1.1.0']}.zip"
            },
        },
    )
    git(tmp_path / "baselibs", "tag", "v0.3.4", baselibs["main"])
    git(tmp_path / "baselibs", "tag", "v0.3.3", baselibs["main"])
    git(tmp_path / "baselibs", "tag", "unrelated-release", baselibs["main"])

    def clone_history(
        *, repository: str, branch: str, destination: Path, history: bool
    ) -> None:
        assert history
        assert repository in {first_source, second_source}
        destination.parent.mkdir(parents=True, exist_ok=True)
        git(
            tmp_path,
            "clone",
            "-q",
            "--branch",
            branch,
            str(tmp_path / "baselibs"),
            str(destination),
        )

    monkeypatch.setattr(dependency_resolution, "sync_default_branch", clone_history)
    dependency = DependencyDeclaration("score_python_basics", "0.3.4")
    opaque_archive = DependencyDeclaration("score_python_basics", "0.3.3")
    consumer_orgs = ("first-org", "second-org", "disabled-org")
    consumers = tuple(
        RepoEntry(
            f"{owner}-consumer",
            "",
            "Platform",
            "General",
            owner=owner,
            content=DeepContentSignals(bazel_deps=(dependency,)),
            volatile=VolatileMetricsSnapshot(release_bazel_deps=(opaque_archive,))
            if owner == "first-org"
            else VolatileMetricsSnapshot(),
        )
        for owner in consumer_orgs
    )
    sources = tuple(
        RepoEntry(
            "tooling",
            "",
            "Platform",
            "General",
            owner=owner,
            default_branch="main",
            content=DeepContentSignals(bazel_module_name="tooling"),
            volatile=VolatileMetricsSnapshot(
                latest_release_version="unrelated-release"
            ),
        )
        for owner in consumer_orgs[:2]
    )
    configs = tuple(
        OrgConfig(
            org_name=owner,
            registry_repo=f"{owner}/registry" if owner != "disabled-org" else "",
        )
        for owner in consumer_orgs
    )
    repos = (*sources, *consumers)
    mapping, resolutions = dependency_resolution.collect_dependencies(
        repos, configs, cache_directory=cache
    )
    snapshot = RepoSnapshot.from_dict(
        RepoSnapshot(
            SNAPSHOT_SCHEMA_VERSION,
            "first-org",
            "2026-11-20T00:00:00+00:00",
            repos,
            additional_org_names=consumer_orgs[1:],
            module_repositories=mapping,
            dependency_resolutions=resolutions,
        ).to_dict()
    )

    first = snapshot.dependency_resolution(consumers[0], dependency)
    assert first is not None
    assert first.repository == first_source
    assert first.resolved_sha == baselibs["v1.0.0"]
    assert first.latest_release == "0.3.5"
    assert first.behind_latest_release_by == 2
    assert first.behind_default_branch_by == 3
    opaque = snapshot.dependency_resolution(consumers[0], opaque_archive)
    assert opaque is not None
    assert opaque.resolved_sha is None
    assert opaque.behind_default_branch_by is None
    second = snapshot.dependency_resolution(consumers[1], dependency)
    assert second is not None
    assert second.repository == second_source
    assert second.resolved_sha == baselibs["v1.1.0"]
    assert second.latest_release == "0.3.4"
    assert second.behind_latest_release_by == 0
    assert snapshot.dependency_repository(consumers[2], dependency) is None
    pages = render_all_pages(snapshot)
    first_page = pages["tooling/index.html"]
    assert "first-org/first-org-consumer</a>" in first_page
    assert "second-org/second-org-consumer</a>" not in first_page
    second_page = pages["@orgs/second-org/tooling/index.html"]
    assert "second-org/second-org-consumer</a>" in second_page
    assert "first-org/first-org-consumer</a>" not in second_page
