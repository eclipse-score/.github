import json
import os
import subprocess
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest

import generate_repo_overview.collector as collector
import generate_repo_overview.collector.reference_integration as reference_integration
import generate_repo_overview.collector.registry_metadata as registry_metadata
import generate_repo_overview.collector.repo_entry as repo_entry
import generate_repo_overview.collector.signal_detection as signal_detection
import generate_repo_overview.collector.snapshot_io as snapshot_io
from generate_repo_overview._html_index import render_index_page
from generate_repo_overview.collector.signal_detection import default_content_signals
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    DependencyDeclaration,
    GroupingLevel,
    OrganizationSignals,
    RegistrySignals,
    RepoEntry,
    RepoSnapshot,
    SphinxItem,
    TrackedDep,
    VolatileMetricsSnapshot,
    WorkflowSignal,
)
from generate_repo_overview.org_config import OrgConfig, OverviewConfig


def _run_git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_snapshot_round_trip_preserves_repository_overview(tmp_path: Path) -> None:
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="tools",
                description="Tooling",
                category="Infrastructure",
                subcategory="Tooling",
                default_branch="main",
                default_branch_sha="abc123",
                content=DeepContentSignals(
                    is_bazel_repo=True,
                    has_bazel_module=True,
                    bazel_module_name="score_tools",
                    bazel_version="8.4.2",
                    codeowners=("@infra-team",),
                    referenced_by_reference_integration=True,
                    has_lint_config=True,
                    has_gitlint_config=True,
                    has_pyproject_toml=True,
                    has_pre_commit_config=True,
                    has_ci=True,
                    matched_workflow_signals=("Daily Workflow",),
                    has_coverage_config=False,
                    sphinx_features=(
                        SphinxItem(
                            path="docs/features/tools",
                            title="Tools",
                            identifier="feat__tools",
                            source_repo="eclipse-score/score",
                        ),
                    ),
                    sphinx_modules=(
                        SphinxItem(
                            path="docs/modules/tools",
                            title="Tools",
                            identifier="mod__tools",
                            source_repo="eclipse-score/score",
                        ),
                    ),
                    docs_feature_paths=("docs/features/tools",),
                ),
                registry=RegistrySignals(
                    maintainers_in_bazel_registry=("Andrey Babanin (@4og)",),
                    latest_bazel_registry_version="0.2.5",
                ),
                volatile=VolatileMetricsSnapshot(
                    last_push_date="2026-04-12",
                    open_issues=2,
                    open_prs=1,
                    open_ready_prs=1,
                    open_draft_prs=0,
                    latest_release_version="v1.2.3",
                    latest_release_date="2026-04-01",
                    commits_since_latest_release=7,
                ),
                stars=3,
                forks=4,
            ),
        ),
        organization_signals={
            "eclipse-score": OrganizationSignals(
                tracked_deps=(
                    TrackedDep(
                        repo="eclipse-score/docs-as-code",
                        module_name="score_docs_as_code",
                    ),
                ),
                workflow_signals=(
                    WorkflowSignal(
                        label="Daily Workflow",
                        reference="org/cicd/.github/workflows/daily.yml@",
                    ),
                ),
            )
        },
    )
    snapshot_path = tmp_path / "repo_overview.json"

    snapshot_io.write_snapshot(snapshot, snapshot_path)

    assert snapshot_io.load_snapshot(snapshot_path) == snapshot


def test_ensure_snapshot_prefers_existing_cache(tmp_path: Path) -> None:
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(RepoEntry("tools", "Tooling", "Infrastructure", "Tooling"),),
    )
    snapshot_path = tmp_path / "repo_overview.json"
    snapshot_io.write_snapshot(snapshot, snapshot_path)

    loaded_snapshot = collector.ensure_snapshot(
        config=OverviewConfig((OrgConfig(org_name="eclipse-score"),)),
        cache_path=snapshot_path,
    )

    assert loaded_snapshot == snapshot


def test_fetch_repositories_reuses_cached_content_signals() -> None:
    pushed_at = datetime(2026, 4, 13, 10, 0, tzinfo=UTC)
    release_at = datetime(2026, 4, 1, 8, 0, tzinfo=UTC)

    class FakeRepo:
        archived = False
        name = "tools"
        description = "Tooling"
        default_branch = "main"

        def __init__(self) -> None:
            self.tree_calls = 0
            self.pushed_at = pushed_at
            self.open_issues_count = 3
            self.stargazers_count = 3
            self.forks_count = 4

        def get_branch(self, branch_name: str) -> SimpleNamespace:
            assert branch_name == "main"
            return SimpleNamespace(commit=SimpleNamespace(sha="abc123"))

        def get_git_tree(self, ref: str, recursive: bool = True) -> SimpleNamespace:
            self.tree_calls += 1
            return SimpleNamespace(tree=[])

        def get_pulls(
            self,
            state: str = "open",
            **_: Any,
        ) -> list[SimpleNamespace]:
            if state == "open":
                return [SimpleNamespace(draft=False)]
            if state == "closed":
                return []
            raise AssertionError(f"Unexpected pull state: {state}")

        def get_latest_release(self) -> SimpleNamespace:
            return SimpleNamespace(
                raw_data={"tag_name": "v1.2.3"},
                tag_name="latest",
                published_at=release_at,
            )

        def compare(self, base: str, head: str) -> SimpleNamespace:
            assert base == "v1.2.3"
            assert head == "abc123"
            return SimpleNamespace(total_commits=7)

    fake_repo = FakeRepo()
    organization = SimpleNamespace(login="eclipse-score")
    cached_snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="tools",
                description="Tooling",
                category="Infrastructure",
                subcategory="Tooling",
                default_branch="main",
                default_branch_sha="abc123",
                content=DeepContentSignals(
                    is_bazel_repo=True,
                    bazel_version="8.4.2",
                    codeowners=("@infra-team",),
                    has_lint_config=True,
                    has_ci=True,
                    has_dependabot_config=False,
                    matched_workflow_signals=("Daily Workflow",),
                    has_coverage_config=False,
                ),
                volatile=VolatileMetricsSnapshot(
                    volatile_metrics_fetched_at="2026-04-13T11:30:00+00:00",
                ),
            ),
        ),
    )

    original_fetch_active_repositories = collector.fetch_active_repositories
    try:
        collector.fetch_active_repositories = lambda organization, **_kwargs: {
            "tools": collector.ActiveRepositoryData(
                repository=fake_repo,
                custom_properties={},
            )
        }
        repos = collector.fetch_repositories(
            cast("Any", organization),
            existing_snapshot=cached_snapshot,
        )
    finally:
        collector.fetch_active_repositories = original_fetch_active_repositories

    assert fake_repo.tree_calls == 1
    assert len(repos) == 1
    entry = repos[0]
    assert entry.name == "tools"
    assert entry.default_branch_sha == "abc123"
    assert entry.content.is_bazel_repo is True
    assert entry.content.bazel_version == "8.4.2"
    assert entry.volatile.last_push_date == "2026-04-13"
    assert entry.volatile.open_issues == 2
    assert entry.volatile.open_prs == 1
    assert entry.volatile.open_ready_prs == 1
    assert entry.volatile.open_draft_prs == 0
    assert entry.volatile.latest_release_version == "v1.2.3"
    assert entry.volatile.latest_release_date == "2026-04-01"
    assert entry.volatile.commits_since_latest_release == 7
    assert entry.volatile.volatile_metrics_fetched_at is not None
    assert entry.stars == 3
    assert entry.forks == 4


def test_fetch_repositories_invalidates_cache_when_signal_labels_change() -> None:
    """D4.1: When workflow signal labels in config differ from cached snapshot,
    content cache is ignored and signals are re-evaluated from scratch."""
    pushed_at = datetime(2026, 4, 13, 10, 0, tzinfo=UTC)

    class FakeRepo:
        archived = False
        name = "tools"
        description = "Tooling"
        default_branch = "main"

        def __init__(self) -> None:
            self.pushed_at = pushed_at
            self.open_issues_count = 0
            self.stargazers_count = 0
            self.forks_count = 0

        def get_branch(self, branch_name: str) -> SimpleNamespace:
            return SimpleNamespace(commit=SimpleNamespace(sha="abc123"))

        def get_git_tree(self, ref: str, recursive: bool = True) -> SimpleNamespace:
            return SimpleNamespace(tree=[])

        def get_pulls(self, state: str = "open", **_: Any) -> list[SimpleNamespace]:
            return []

        def get_latest_release(self) -> SimpleNamespace:
            raise Exception("no releases")

    fake_repo = FakeRepo()
    organization = SimpleNamespace(login="eclipse-score")

    cached_snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        organization_signals={
            "eclipse-score": OrganizationSignals(
                workflow_signals=(
                    WorkflowSignal(
                        label="Daily Workflow",
                        reference="org/cicd/.github/workflows/daily.yml@",
                    ),
                )
            )
        },
        repos=(
            RepoEntry(
                name="tools",
                description="Tooling",
                category="Infrastructure",
                subcategory="Tooling",
                default_branch="main",
                default_branch_sha="abc123",
                content=DeepContentSignals(
                    is_bazel_repo=True,
                    matched_workflow_signals=("Daily Workflow",),
                ),
            ),
        ),
    )

    config = OrgConfig(
        org_name="eclipse-score",
        workflow_signals=(WorkflowSignal(label="Nightly Build", reference="org/ref@"),),
    )

    original_fetch = collector.fetch_active_repositories
    try:
        collector.fetch_active_repositories = lambda organization, **_kwargs: {
            "tools": collector.ActiveRepositoryData(
                repository=fake_repo,
                custom_properties={},
            )
        }
        repos = collector.fetch_repositories(
            cast("Any", organization),
            existing_snapshot=cached_snapshot,
            config=config,
        )
    finally:
        collector.fetch_active_repositories = original_fetch

    assert len(repos) == 1
    entry = repos[0]
    # Cache was invalidated: is_bazel_repo should be False (empty tree)
    # instead of True (from cache)
    assert entry.content.is_bazel_repo is False
    assert entry.content.matched_workflow_signals == ()


def test_fetch_repositories_uses_resolved_registry_repository_cache_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_registry_repositories: list[str] = []
    organization = SimpleNamespace(login="eclipse-score")
    config = OrgConfig(
        org_name="eclipse-score",
        reference_integration_repo="eclipse-score/reference-integration",
        registry_repo="eclipse-score/bazel_registry",
    )
    resolved_registry_repository = SimpleNamespace(
        full_name="Eclipse-Score/Bazel_Registry"
    )

    monkeypatch.setattr(
        collector,
        "fetch_active_repositories",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        collector.registry_metadata,
        "fetch_bazel_registry_metadata_by_repo",
        lambda **_kwargs: {},
    )

    def fake_fetch_reference_integration_repository_names(
        **kwargs: Any,
    ) -> set[str]:
        observed_registry_repositories.append(kwargs["registry_repository"])
        return set()

    monkeypatch.setattr(
        collector.reference_integration,
        "fetch_reference_integration_repository_names",
        fake_fetch_reference_integration_repository_names,
    )

    assert (
        collector.fetch_repositories(
            cast("Any", organization),
            config=config,
            registry_repository=resolved_registry_repository,
        )
        == []
    )
    assert observed_registry_repositories == ["Eclipse-Score/Bazel_Registry"]


@pytest.mark.parametrize("lazy", [False, True])
def test_fetch_repositories_skips_missing_external_reference_integration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], lazy: bool
) -> None:
    from github import GithubException

    class MissingRepository:
        @property
        def default_branch(self) -> str:
            raise GithubException(404, {"message": "Not Found"}, {})

    class RepositoryResolver:
        def get_repo(self, full_name_or_id: str) -> MissingRepository:
            assert full_name_or_id == "other-org/integration"
            if not lazy:
                raise GithubException(404, {"message": "Not Found"}, {})
            return MissingRepository()

    monkeypatch.setattr(
        collector, "fetch_active_repositories", lambda *_args, **_kwargs: {}
    )
    assert (
        collector.fetch_repositories(
            cast("Any", SimpleNamespace(login="first-org")),
            config=OrgConfig(
                org_name="first-org", reference_integration_repo="other-org/integration"
            ),
            github=RepositoryResolver(),
        )
        == []
    )
    assert (
        "Reference integration repository other-org/integration is unavailable"
        in capsys.readouterr().err
    )


def test_collect_repository_entry_reuses_cached_details_when_unchanged() -> None:
    class FakeRepo:
        default_branch = "main"
        description = "Tooling (updated)"
        stargazers_count = 12
        forks_count = 3

        def get_branch(self, branch_name: str) -> SimpleNamespace:
            assert branch_name == "main"
            return SimpleNamespace(commit=SimpleNamespace(sha="abc123"))

        def get_git_tree(self, ref: str, recursive: bool = True) -> SimpleNamespace:
            raise AssertionError(
                "get_git_tree should not be called in cache-aware fast mode"
            )

        def get_pulls(self, *args: Any, **kwargs: Any) -> list[SimpleNamespace]:
            raise AssertionError(
                "get_pulls should not be called in cache-aware fast mode"
            )

        def get_latest_release(self) -> SimpleNamespace:
            raise AssertionError(
                "get_latest_release should not be called in cache-aware fast mode"
            )

    repo = FakeRepo()
    cached_entry = RepoEntry(
        name="tools",
        description="Tooling",
        category="Infrastructure",
        subcategory="Tooling",
        default_branch="main",
        default_branch_sha="abc123",
        content=DeepContentSignals(
            is_bazel_repo=True,
            bazel_version="8.4.2",
            codeowners=("@infra-team",),
            referenced_by_reference_integration=False,
            has_lint_config=True,
            has_gitlint_config=True,
            has_pyproject_toml=True,
            has_pre_commit_config=True,
            has_ci=True,
            matched_workflow_signals=("Daily Workflow",),
            has_coverage_config=True,
            bazel_deps=(DependencyDeclaration("score_docs_as_code", "1.2.3"),),
        ),
        registry=RegistrySignals(
            maintainers_in_bazel_registry=("Old Maintainer",),
            latest_bazel_registry_version="0.1.0",
        ),
        volatile=VolatileMetricsSnapshot(
            last_push_date="2026-04-10",
            merged_prs_30_days=8,
            open_issues=7,
            open_prs=4,
            open_ready_prs=3,
            open_draft_prs=1,
            latest_release_version="v1.2.3",
            latest_release_date="2026-04-01",
            commits_since_latest_release=5,
            volatile_metrics_fetched_at="2099-01-01T00:00:00+00:00",
        ),
        stars=1,
        forks=1,
    )

    entry = repo_entry.collect_repository_entry(
        repository_name="tools",
        repository=repo,
        custom_properties={"category": "Engineering", "subcategory": "Platform"},
        grouping_levels=(
            GroupingLevel(property="category", default="Uncategorized"),
            GroupingLevel(property="subcategory", default="General"),
        ),
        bazel_registry_metadata={
            "maintainers_in_bazel_registry": ("New Maintainer",),
            "latest_bazel_registry_version": "0.2.0",
        },
        cached_entry=cached_entry,
        referenced_by_reference_integration=True,
    )

    assert entry == RepoEntry(
        name="tools",
        description="Tooling (updated)",
        category="Engineering",
        subcategory="Platform",
        default_branch="main",
        default_branch_sha="abc123",
        content=DeepContentSignals(
            is_bazel_repo=True,
            bazel_version="8.4.2",
            codeowners=("@infra-team",),
            referenced_by_reference_integration=True,
            has_lint_config=True,
            has_gitlint_config=True,
            has_pyproject_toml=True,
            has_pre_commit_config=True,
            has_ci=True,
            matched_workflow_signals=("Daily Workflow",),
            has_coverage_config=True,
            bazel_deps=(DependencyDeclaration("score_docs_as_code", "1.2.3"),),
        ),
        registry=RegistrySignals(
            maintainers_in_bazel_registry=("New Maintainer",),
            latest_bazel_registry_version="0.2.0",
        ),
        volatile=VolatileMetricsSnapshot(
            last_push_date="2026-04-10",
            merged_prs_30_days=8,
            open_issues=7,
            open_prs=4,
            open_ready_prs=3,
            open_draft_prs=1,
            latest_release_version="v1.2.3",
            latest_release_date="2026-04-01",
            commits_since_latest_release=5,
            volatile_metrics_fetched_at="2099-01-01T00:00:00+00:00",
        ),
        stars=12,
        forks=3,
    )


def test_collect_repository_entry_accepts_repository_without_commits(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    subprocess.run(
        ["git", "init", "--initial-branch=main", str(source)],
        check=True,
        capture_output=True,
        text=True,
    )

    class EmptyRepo:
        clone_url = str(source)
        default_branch = "main"
        description = "Reserved repository"
        forks_count = 0
        full_name = "eclipse-score/empty"
        open_issues_count = 0
        pushed_at = None
        stargazers_count = 0

        def get_branch(self, branch_name: str) -> object:
            raise RuntimeError(f"Branch {branch_name} does not exist")

        def get_languages(self) -> dict[str, int]:
            return {}

        def get_latest_release(self) -> object:
            raise RuntimeError("No releases")

        def get_pulls(self, **_: Any) -> list[object]:
            return []

    monkeypatch.setattr(
        repo_entry,
        "DEFAULT_REPOSITORY_CHECKOUTS",
        tmp_path / "checkouts",
    )
    monkeypatch.setattr(repo_entry, "sync_repository_checkout", lambda **_: None)

    entry = repo_entry.collect_repository_entry(
        repository_name="empty",
        repository=EmptyRepo(),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=None,
    )

    assert entry.name == "empty"
    assert entry.default_branch == "main"
    assert entry.default_branch_sha is None
    assert entry.content == DeepContentSignals()
    assert entry.volatile.last_push_date is None


def test_collect_repository_entry_accepts_repository_without_default_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    subprocess.run(
        ["git", "init", "--initial-branch=main", str(source)],
        check=True,
        capture_output=True,
        text=True,
    )
    _run_git(source, "config", "user.name", "Test User")
    _run_git(source, "config", "user.email", "test@example.com")
    (source / "README.md").write_text("reserved\n", encoding="utf-8")
    _run_git(source, "add", "README.md")
    _run_git(source, "commit", "-m", "initial")
    _run_git(source, "tag", "v0.0.0")
    _run_git(source, "update-ref", "-d", "refs/heads/main")

    class RepositoryWithoutDefaultBranch:
        clone_url = str(source)
        default_branch = "main"
        description = "Reserved repository"
        forks_count = 0
        full_name = "eclipse-score/empty-no-default-branch"
        open_issues_count = 0
        pushed_at = None
        stargazers_count = 0

        def get_branch(self, branch_name: str) -> object:
            raise RuntimeError(f"Branch {branch_name} does not exist")

        def get_languages(self) -> dict[str, int]:
            return {}

        def get_latest_release(self) -> object:
            raise RuntimeError("No releases")

        def get_pulls(self, **_: Any) -> list[object]:
            return []

    monkeypatch.setattr(
        repo_entry,
        "DEFAULT_REPOSITORY_CHECKOUTS",
        tmp_path / "checkouts",
    )
    monkeypatch.setattr(repo_entry, "sync_repository_checkout", lambda **_: None)

    entry = repo_entry.collect_repository_entry(
        repository_name="empty-no-default-branch",
        repository=RepositoryWithoutDefaultBranch(),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=None,
    )

    assert entry.default_branch == "main"
    assert entry.default_branch_sha is None
    assert entry.content == DeepContentSignals()


def test_collect_repository_entry_does_not_reuse_cached_registry_when_metadata_missing() -> (
    None
):
    class FakeRepo:
        default_branch = "main"
        description = "Tooling"
        stargazers_count = 5
        forks_count = 2

        def get_branch(self, branch_name: str) -> SimpleNamespace:
            assert branch_name == "main"
            return SimpleNamespace(commit=SimpleNamespace(sha="abc123"))

        def get_git_tree(self, ref: str, recursive: bool = True) -> SimpleNamespace:
            raise AssertionError(
                "get_git_tree should not be called in cache-aware fast mode"
            )

        def get_pulls(self, *args: Any, **kwargs: Any) -> list[SimpleNamespace]:
            raise AssertionError(
                "get_pulls should not be called in cache-aware fast mode"
            )

        def get_latest_release(self) -> SimpleNamespace:
            raise AssertionError(
                "get_latest_release should not be called in cache-aware fast mode"
            )

    cached_entry = RepoEntry(
        name="tools",
        description="Tooling",
        category="Infrastructure",
        subcategory="Tooling",
        default_branch="main",
        default_branch_sha="abc123",
        content=DeepContentSignals(is_bazel_repo=True),
        registry=RegistrySignals(
            maintainers_in_bazel_registry=("Stale Maintainer",),
            latest_bazel_registry_version="9.9.9",
        ),
        volatile=VolatileMetricsSnapshot(
            volatile_metrics_fetched_at="2099-01-01T00:00:00+00:00",
        ),
    )

    entry = repo_entry.collect_repository_entry(
        repository_name="tools",
        repository=FakeRepo(),
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=cached_entry,
    )

    assert entry.registry == RegistrySignals()


@pytest.mark.parametrize("legacy_snapshot", [False, True], ids=["expired", "legacy"])
def test_collect_repository_entry_refreshes_volatile_metrics_with_cached_content(
    monkeypatch: pytest.MonkeyPatch,
    legacy_snapshot: bool,
) -> None:
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            current = cls(2026, 4, 17, 12, 0, tzinfo=UTC)
            return current if tz is not None else current.replace(tzinfo=None)

    monkeypatch.setattr(repo_entry, "datetime", FixedDatetime)

    class FakeRepo:
        default_branch = "main"
        description = "Tooling"
        stargazers_count = 2
        forks_count = 3
        pushed_at = datetime(2026, 4, 16, 12, 0, tzinfo=UTC)
        open_issues_count = 6

        def __init__(self) -> None:
            self.tree_calls = 0

        def get_branch(self, branch_name: str) -> SimpleNamespace:
            assert branch_name == "main"
            return SimpleNamespace(
                commit=SimpleNamespace(
                    sha="abc123",
                    commit=SimpleNamespace(
                        committer=SimpleNamespace(date=self.pushed_at)
                    ),
                )
            )

        def get_git_tree(self, ref: str, recursive: bool = True) -> SimpleNamespace:
            self.tree_calls += 1
            return SimpleNamespace(tree=[])

        def get_pulls(self, state: str = "open", **_: Any) -> list[SimpleNamespace]:
            if state == "open":
                return [SimpleNamespace(draft=False), SimpleNamespace(draft=True)]
            return []

        def get_latest_release(self) -> SimpleNamespace:
            return SimpleNamespace(
                raw_data={"tag_name": "v1.0.0"}, published_at=self.pushed_at
            )

        def compare(self, base: str, head: str) -> SimpleNamespace:
            assert base == "v1.0.0"
            assert head == "abc123"
            return SimpleNamespace(total_commits=4)

    repo = FakeRepo()
    cached_entry = RepoEntry(
        name="tools",
        description="Tooling",
        category="Infrastructure",
        subcategory="Tooling",
        default_branch="main",
        default_branch_sha="abc123",
        content=DeepContentSignals(
            is_bazel_repo=True,
            bazel_version="8.4.2",
            codeowners=("@infra-team",),
            has_lint_config=True,
            has_ci=True,
            has_dependabot_config=False,
            matched_workflow_signals=("Daily Workflow",),
            has_coverage_config=False,
        ),
        volatile=VolatileMetricsSnapshot(
            open_issues=1,
            open_prs=1,
            open_ready_prs=1,
            merged_prs_30_days=1,
            latest_release_version="v0.9.0",
            latest_release_date="2026-04-01",
            commits_since_latest_release=1,
            volatile_metrics_fetched_at="2026-04-17T09:00:00+00:00",
        ),
    )

    if legacy_snapshot:
        # The timestamp is fresh, but the snapshot predates the PR counters.
        cached_data = cached_entry.to_dict()
        cached_data["volatile"]["volatile_metrics_fetched_at"] = FixedDatetime.now(
            UTC
        ).isoformat()
        cached_data["volatile"].pop("open_renovate_prs")
        cached_data["volatile"].pop("open_dependabot_prs")
        cached_entry = RepoEntry.from_dict(cached_data)

    entry = repo_entry.collect_repository_entry(
        repository_name="tools",
        repository=repo,
        custom_properties={},
        bazel_registry_metadata=None,
        cached_entry=cached_entry,
    )

    assert repo.tree_calls == 1
    assert entry.content.is_bazel_repo is True
    assert entry.volatile.open_prs == 2
    assert entry.volatile.open_ready_prs == 1
    assert entry.volatile.open_draft_prs == 1
    assert entry.volatile.open_renovate_prs == 0
    assert entry.volatile.open_dependabot_prs == 0
    assert entry.volatile.open_issues == 4
    assert entry.volatile.latest_release_version == "v1.0.0"
    assert entry.volatile.commits_since_latest_release == 4
    assert entry.volatile.volatile_metrics_fetched_at == "2026-04-17T12:00:00+00:00"


def test_get_open_pull_request_counts_splits_ready_draft_and_bot_authors() -> None:
    repository = SimpleNamespace(
        get_pulls=lambda state="open": [
            SimpleNamespace(draft=False, user=SimpleNamespace(login="renovate[bot]")),
            SimpleNamespace(
                raw_data={"draft": True}, user=SimpleNamespace(login="dependabot[bot]")
            ),
            SimpleNamespace(
                draft=False,
                user=SimpleNamespace(login="eclipse-score-bot"),
                labels=[SimpleNamespace(name="renovate")],
            ),
            SimpleNamespace(
                draft=False,
                user=SimpleNamespace(login="eclipse-score-bot"),
                labels=[SimpleNamespace(name="automation")],
            ),
            SimpleNamespace(
                draft=False,
                user=SimpleNamespace(login="contributor"),
                labels=[SimpleNamespace(name="renovate")],
            ),
        ]
    )

    assert repo_entry.get_open_pull_request_counts(repository) == {
        "ready": 4,
        "draft": 1,
        "total": 5,
        "renovate": 2,
        "dependabot": 1,
    }
    assert (
        repo_entry.get_open_issue_count(
            SimpleNamespace(open_issues_count=7),
            open_pull_request_total=5,
        )
        == 2
    )


def test_unavailable_bot_counts_do_not_invalidate_snapshot_timestamp() -> None:
    fetched_at = "2026-04-17T12:00:00+00:00"
    volatile = VolatileMetricsSnapshot.from_dict(
        {
            "volatile_metrics_fetched_at": fetched_at,
            "open_renovate_prs": None,
            "open_dependabot_prs": None,
        }
    )

    assert volatile.volatile_metrics_fetched_at == fetched_at


@pytest.mark.parametrize("suffix", ["yml", "yaml"])
def test_cached_repository_backfills_dependabot_config_from_checkout(
    tmp_path: Path, suffix: str
) -> None:
    config = tmp_path / ".github" / f"dependabot.{suffix}"
    config.parent.mkdir()
    config.write_text("version: 2\n", encoding="utf-8")
    cached_entry = RepoEntry(
        name="tools",
        description="Tooling",
        category="Infrastructure",
        subcategory="Tooling",
        default_branch="main",
        default_branch_sha="abc123",
        volatile=VolatileMetricsSnapshot(
            volatile_metrics_fetched_at=datetime.now(UTC).isoformat()
        ),
    )

    entry = repo_entry.maybe_collect_repository_entry_fast_path(
        repository_name="tools",
        repository=SimpleNamespace(),
        custom_properties={},
        bazel_registry_metadata=None,
        referenced_by_reference_integration=False,
        cached_entry=cached_entry,
        default_branch="main",
        default_branch_sha="abc123",
        checkout_path=tmp_path,
    )

    assert entry is not None
    assert entry.content.has_dependabot_config is True
    assert entry.volatile == cached_entry.volatile


def test_get_merged_pull_request_count_last_30_days_filters_by_branch_and_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return now if tz is not None else now.replace(tzinfo=None)

    now = FixedDatetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    cutoff = now - repo_entry.timedelta(days=repo_entry.MERGED_PULL_REQUEST_WINDOW_DAYS)

    monkeypatch.setattr(repo_entry, "datetime", FixedDatetime)

    def get_pulls(
        *, state: str, sort: str, direction: str, base: str
    ) -> list[SimpleNamespace]:
        assert state == "closed"
        assert sort == "updated"
        assert direction == "desc"
        assert base == "main"
        return [
            SimpleNamespace(
                merged_at=now - repo_entry.timedelta(days=5),
                updated_at=now - repo_entry.timedelta(days=4),
                base=SimpleNamespace(ref="main"),
            ),
            SimpleNamespace(
                merged_at=now - repo_entry.timedelta(days=2),
                updated_at=now - repo_entry.timedelta(days=1),
                base=SimpleNamespace(ref="release"),
            ),
            SimpleNamespace(
                merged_at=None,
                updated_at=now - repo_entry.timedelta(days=1),
                base=SimpleNamespace(ref="main"),
            ),
            SimpleNamespace(
                merged_at=cutoff - repo_entry.timedelta(days=1),
                updated_at=cutoff - repo_entry.timedelta(days=1),
                base=SimpleNamespace(ref="main"),
            ),
        ]

    repository = SimpleNamespace(get_pulls=get_pulls)

    assert (
        repo_entry.get_merged_pull_request_count_last_30_days(
            repository,
            default_branch="main",
        )
        == 1
    )


def test_get_merged_pull_request_count_last_30_days_returns_zero_without_default_branch() -> (
    None
):
    repository = SimpleNamespace(get_pulls=lambda **kwargs: [])

    assert (
        repo_entry.get_merged_pull_request_count_last_30_days(
            repository,
            default_branch=None,
        )
        == 0
    )


def test_get_latest_release_details_returns_none_when_release_lookup_is_lazy() -> None:
    class LazyFailingRelease:
        @property
        def tag_name(self) -> str:
            raise RuntimeError("Not Found")

    repository = SimpleNamespace(get_latest_release=lambda: LazyFailingRelease())

    assert repo_entry.get_latest_release_details(
        repository,
        default_branch="main",
        default_branch_sha="abc123",
    ) == {
        "version": None,
        "date": None,
        "commits_since_release": None,
        "latest_release_ahead_of_default_branch_by": None,
        "default_branch_ahead_of_latest_release_by": None,
        "release_bazel_version": None,
        "release_bazel_deps": (),
    }


def test_get_latest_release_version_prefers_raw_tag_name() -> None:
    release = SimpleNamespace(
        raw_data={"tag_name": "v0.2.5", "name": "Release 0.2.5"},
        name="Release 0.2.5",
        tag_name="latest",
    )

    assert repo_entry.get_latest_release_version(release) == "v0.2.5"


def test_get_latest_release_version_ignores_latest_sentinel_without_raw_data() -> None:
    release = SimpleNamespace(name="latest", title="latest")

    assert repo_entry.get_latest_release_version(release) is None


def test_detect_bazel_version_ignores_module_version_without_dot_bazelversion() -> None:
    assert (
        signal_detection.detect_bazel_version(
            SimpleNamespace(),
            tree_paths={"MODULE.bazel"},
            ref="abc123",
        )
        is None
    )


def test_get_bazel_module_name_extracts_root_module_name() -> None:
    assert (
        signal_detection.get_bazel_module_name(
            '# module(name = "example")\n'
            "module(\n    name = 'score_logging',\n    version = '1.0.0',\n)\n"
            'bazel_dep(name = "score_tooling", version = "2.0.0")\n'
        )
        == "score_logging"
    )


def test_get_bazel_module_name_returns_none_without_module_declaration() -> None:
    assert (
        signal_detection.get_bazel_module_name(
            'bazel_dep(name = "score_tooling", version = "2.0.0")\n'
        )
        is None
    )


def test_detect_docs_feature_paths_uses_named_feature_folders() -> None:
    assert signal_detection.detect_docs_feature_paths(
        {
            "docs/features/logging/index.rst",
            "docs/features/tracing/architecture/index.rst",
        }
    ) == ("docs/features/logging", "docs/features/tracing")


def test_detect_docs_feature_paths_recognizes_single_feature_variant() -> None:
    assert signal_detection.detect_docs_feature_paths(
        {
            "docs/features/architecture/index.rst",
            "docs/features/safety_analysis/fmea.rst",
            "docs/module/index.rst",
        }
    ) == ("docs/features",)


def test_parse_sphinx_config_names_extracts_project_and_prefix() -> None:
    assert signal_detection.parse_sphinx_config_names(
        'project = "S-CORE Logging"\nproject_prefix = "LOGGING_"\n'
    ) == ("S-CORE Logging", "LOGGING_")


def test_detect_sphinx_config_names_uses_legacy_fallback_path() -> None:
    assert signal_detection.detect_sphinx_config_names(
        tree_paths={"docs/sphinx/conf.py"},
        read_text=lambda path: (
            'project = "S-CORE Logging"\nproject_prefix = "LOGGING_"\n'
            if path == "docs/sphinx/conf.py"
            else None
        ),
    ) == ("S-CORE Logging", "LOGGING_")


def test_detect_repo_sphinx_items_reads_feature_architecture() -> None:
    features, modules = signal_detection.detect_repo_sphinx_items(
        tree_paths={"docs/features/architecture/index.rst"},
        read_text=lambda path: (
            ".. feat:: Logging Feature\n"
            "   :id: feat__logging_repo\n\n"
            ".. mod:: Logging\n"
            "   :id: mod__logging_repo\n"
            if path == "docs/features/architecture/index.rst"
            else None
        ),
    )

    assert features == (
        SphinxItem(
            path="docs/features/architecture/index.rst",
            title="Logging Feature",
            identifier="feat__logging_repo",
        ),
    )
    assert modules == (
        SphinxItem(
            path="docs/features/architecture/index.rst",
            title="Logging",
            identifier="mod__logging_repo",
        ),
    )


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        (
            'git_override(module_name = "score_tooling", remote = "https://github.com/FIRST-ORG/Tooling.git")',
            ({"tooling"}, set()),
        ),
        (
            'git_override(module_name = "score_tooling", remote = "git@github.com:first-org/tooling.git")',
            ({"tooling"}, set()),
        ),
        (
            'git_override(module_name = "score_tooling", remote = "ssh://git@github.com/first-org/tooling.git")',
            ({"tooling"}, set()),
        ),
        (
            '# git_override(module_name = "score_tooling", remote = "https://github.com/first-org/tooling.git")',
            ({"tooling"}, {"tooling"}),
        ),
    ],
)
def test_reference_integration_resolves_active_overrides_before_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: str,
    expected: tuple[set[str], set[str]],
) -> None:
    (tmp_path / "MODULE.bazel").write_text(
        f'bazel_dep(name = "score_tooling")\n{override}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        reference_integration, "sync_repository_checkout", lambda **kwargs: tmp_path
    )
    monkeypatch.setattr(
        reference_integration,
        "get_bazel_registry_repositories_by_module",
        lambda **kwargs: {"score_tooling": "tooling"},
    )
    repository = SimpleNamespace(
        default_branch="main", full_name="first-org/integration"
    )

    def collect(org_name: str) -> set[str]:
        return reference_integration.fetch_reference_integration_repository_names(
            reference_integration_repository=repository,
            active_repository_names={"tooling"},
            registry_repository="second-org/registry",
            org_name=org_name,
        )

    assert (collect("first-org"), collect("second-org")) == expected


def test_known_good_pin_parser_accepts_hashes_and_versions_and_ignores_invalid_entries() -> (
    None
):
    content = json.dumps(
        {
            "modules": {
                "Core": {
                    "versioned": {
                        "repo": "https://github.com/Eclipse-Score/Versioned.git",
                        "version": "1.2.3",
                    },
                    "hashed": {
                        "repo": "https://github.com/eclipse-score/hashed.git",
                        "hash": "abc1234",
                        "branch": "integration",
                    },
                    "malformed": "not a module object",
                    "inactive": {
                        "repo": "https://github.com/eclipse-score/inactive.git",
                        "version": "1.0.0",
                    },
                    "external": {
                        "repo": "https://github.com/example/external.git",
                        "hash": "deadbee",
                    },
                },
                "malformed group": ["not a module group"],
            }
        }
    )

    pins = reference_integration.parse_known_good_pins(
        content,
        active_repository_names={"versioned", "hashed"},
        org_name="eclipse-score",
    )

    assert pins == {
        "versioned": reference_integration.KnownGoodPin(
            module="versioned",
            group="Core",
            branch="main",
            version="1.2.3",
            commit_hash=None,
        ),
        "hashed": reference_integration.KnownGoodPin(
            module="hashed",
            group="Core",
            branch="integration",
            version=None,
            commit_hash="abc1234",
        ),
    }


def test_known_good_pin_parser_ignores_malformed_json() -> None:
    assert (
        reference_integration.parse_known_good_pins(
            "{invalid json",
            active_repository_names={"repo"},
            org_name="eclipse-score",
        )
        == {}
    )


def test_version_pin_retries_v_prefixed_tag_after_plain_version_is_rejected() -> None:
    """Resolve a module version through a real tag before comparing Git commits.

    ``known_good.json`` stores ``8.3.0``, while this repository's Git tag is
    ``v8.3.0``. PyGithub's lazy commit initially echoes either requested ref as
    ``sha``; completion must reject the plain version and return the tag's real
    commit SHA before the resolver accepts it.
    """
    module_version = "8.3.0"
    github_tag = "v8.3.0"
    verified_commit_sha = "0123456789abcdef0123456789abcdef01234567"
    attempted_refs: list[str] = []

    class LazyCommit:
        """Mirror PyGithub: before completion, sha still echoes the requested ref."""

        def __init__(self, requested_ref: str) -> None:
            self.sha = requested_ref

        def complete(self) -> None:
            if self.sha != github_tag:
                raise LookupError(f"No Git ref named {self.sha}")
            self.sha = verified_commit_sha

    class Repository:
        def get_commit(self, requested_ref: str) -> LazyCommit:
            attempted_refs.append(requested_ref)
            return LazyCommit(requested_ref)

    version_pin = reference_integration.KnownGoodPin(
        module="score_docs_as_code",
        group="Core",
        branch="main",
        version=module_version,
        commit_hash=None,
    )

    assert (
        reference_integration.resolve_reference_integration_pin(
            Repository(), version_pin
        )
        == verified_commit_sha
    )
    assert attempted_refs == [module_version, github_tag]


def test_latest_release_details_keep_divergence_from_single_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Repository:
        compare_calls = 0

        def get_latest_release(self) -> SimpleNamespace:
            return SimpleNamespace(raw_data={"tag_name": "v1.2.3"})

        def compare(self, base: str, head: str) -> SimpleNamespace:
            self.compare_calls += 1
            assert (base, head) == ("v1.2.3", "main-sha")
            return SimpleNamespace(total_commits=7, ahead_by=7, behind_by=2)

    monkeypatch.setattr(
        repo_entry, "fetch_repository_tree_paths", lambda *_args, **_kwargs: ()
    )
    monkeypatch.setattr(
        repo_entry, "detect_bazel_version", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        repo_entry, "detect_bazel_dependencies", lambda *_args, **_kwargs: ()
    )
    repository = Repository()

    details = repo_entry.get_latest_release_details(
        repository,
        default_branch="main",
        default_branch_sha="main-sha",
    )

    assert repository.compare_calls == 1
    assert details["commits_since_release"] == 7
    assert details["latest_release_ahead_of_default_branch_by"] == 2
    assert details["default_branch_ahead_of_latest_release_by"] == 7


def test_compare_git_refs_happy_path_counts_divergence() -> None:
    class Repository:
        def compare(self, left: str, right: str) -> SimpleNamespace:
            return SimpleNamespace(ahead_by=3, behind_by=1)

    comparison = reference_integration.compare_git_refs(
        Repository(),
        left_ref="main",
        right_ref="v1.0.0",
    )

    assert comparison == reference_integration.GitRefComparison(
        right_ahead_by=3,
        left_ahead_by=1,
    )


def test_compare_git_refs_returns_none_when_compare_itself_raises() -> None:
    class Repository:
        def compare(self, left: str, right: str) -> object:
            raise RuntimeError("compare exploded")

    assert (
        reference_integration.compare_git_refs(
            Repository(),
            left_ref="main",
            right_ref="v1.0.0",
        )
        is None
    )


def test_compare_git_refs_logs_warning_and_returns_none_for_no_common_ancestor(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A lazy 404 ``No common ancestor`` must not escape and must be surfaced."""
    from github import GithubException

    class LazyNoCommonAncestor:
        @property
        def ahead_by(self) -> int:
            # Mirrors PyGithub lazy mode: the HTTP error fires on attribute
            # access, after ``compare()`` has already returned.
            raise GithubException(
                404,
                data={},
                message=(
                    "No common ancestor between archival-branch and "
                    "6ea826c43f965f9ebe23cdc813566cf8141ebaf1."
                ),
            )

    class Repository:
        full_name = "example-org/ancient-repo"

        def compare(self, left: str, right: str) -> LazyNoCommonAncestor:
            return LazyNoCommonAncestor()

    result = reference_integration.compare_git_refs(
        Repository(),
        left_ref="archival-branch",
        right_ref="6ea826c43f965f9ebe23cdc813566cf8141ebaf1",
    )

    assert result is None
    captured = capsys.readouterr()
    assert "ancient-repo" in captured.err
    assert "archival-branch" in captured.err


def test_version_pin_uses_resolved_sha_for_commit_link() -> None:
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="versioned",
                description="Versioned repository",
                category="Core",
                subcategory="Modules",
                content=DeepContentSignals(
                    referenced_by_reference_integration=True,
                    reference_integration_version="1.2.3",
                    reference_integration_resolved_hash="abc123456789",
                    reference_integration_pin_ahead_of_main_by=2,
                    reference_integration_main_ahead_of_pin_by=0,
                ),
            ),
        ),
    )

    html = render_index_page(snapshot)

    assert ">1.2.3</a>" in html
    assert "https://github.com/eclipse-score/versioned/commit/abc123456789" in html


def test_reference_integration_maps_bazel_registry_modules_to_repositories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_repository = "eclipse-score/bazel_registry"
    registry_root = tmp_path / registry_repository
    metadata_dir = registry_root / "modules" / "score_process"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "metadata.json").write_text(
        """
{
  "repository": ["github:eclipse-score/process_description"],
  "versions": ["1.0.0"]
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        registry_metadata,
        "default_cache_directory",
        lambda: tmp_path,
    )

    assert registry_metadata.get_bazel_registry_repositories_by_module(
        active_repository_names={"process_description"},
        registry_repository=registry_repository,
    ) == {"score_process": "process_description"}


@pytest.mark.parametrize(
    ("registry_repository", "expected_repositories"),
    [
        ("../outside", {}),
        ("/tmp/registry", {}),
        ("C:/registry", {}),
        ("org/../registry", {}),
        (r"org\..\registry", {}),
    ],
)
def test_reference_integration_ignores_unsafe_registry_repository_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    registry_repository: str,
    expected_repositories: dict[str, str],
) -> None:
    monkeypatch.setattr(
        registry_metadata,
        "default_cache_directory",
        lambda: tmp_path / "cache",
    )

    assert (
        registry_metadata.get_bazel_registry_repositories_by_module(
            active_repository_names={"process_description"},
            registry_repository=registry_repository,
        )
        == expected_repositories
    )


def test_get_codeowners_for_path_prefers_specific_codeowners_rule() -> None:
    assert signal_detection.get_codeowners_for_path(
        """
* @infra-team
.github/CODEOWNERS @docs-team @platform-team
""".strip(),
        target_path=".github/CODEOWNERS",
    ) == ("@docs-team", "@platform-team")


def test_get_codeowners_for_path_normalizes_comma_separated_owners() -> None:
    assert signal_detection.get_codeowners_for_path(
        """
* @armin-acn, @johannes-esr, @masc2023
""".strip(),
        target_path=".github/CODEOWNERS",
    ) == ("@armin-acn", "@johannes-esr", "@masc2023")


def test_parse_bazel_registry_metadata_maps_active_repository_and_latest_version() -> (
    None
):
    metadata = registry_metadata.parse_bazel_registry_metadata(
        """
{
  "maintainers": [
    {
      "name": "Andrey Babanin",
      "github": "4og"
    }
  ],
  "repository": [
    "github:Eclipse-Score/BaseLibs",
    "github:someone-else/ignored"
  ],
  "versions": ["0.2.5", "0.2.4"]
}
""".strip(),
        active_repository_names={"baselibs", "ignored"},
        org_name="eclipse-score",
    )

    assert metadata == {
        "baselibs": {
            "maintainers_in_bazel_registry": ("Andrey Babanin (@4og)",),
            "latest_bazel_registry_version": "0.2.5",
        }
    }


def test_merge_bazel_registry_metadata_combines_owners_and_keeps_latest_version() -> (
    None
):
    assert registry_metadata.merge_bazel_registry_metadata(
        {
            "maintainers_in_bazel_registry": ("Andrey Babanin (@4og)",),
            "latest_bazel_registry_version": "0.2.5",
        },
        {
            "maintainers_in_bazel_registry": (
                "Andrey Babanin (@4og)",
                "Nikola Radakovic (@nradakovic)",
            ),
            "latest_bazel_registry_version": "0.2.4",
        },
    ) == {
        "maintainers_in_bazel_registry": (
            "Andrey Babanin (@4og)",
            "Nikola Radakovic (@nradakovic)",
        ),
        "latest_bazel_registry_version": "0.2.5",
    }


def test_detect_matched_workflow_signals_detects_shared_workflow_reference() -> None:
    from generate_repo_overview.models import WorkflowSignal

    assert signal_detection.detect_matched_workflow_signals(
        tree_paths={".github/workflows/nightly.yml"},
        read_text=lambda path: (
            "jobs:\n"
            "  daily:\n"
            "    uses: eclipse-score/cicd-workflows/.github/workflows/daily.yml@main\n"
            if path == ".github/workflows/nightly.yml"
            else None
        ),
        workflow_signals=(
            WorkflowSignal(
                label="Daily Workflow",
                reference="eclipse-score/cicd-workflows/.github/workflows/daily.yml@",
            ),
        ),
    ) == ("Daily Workflow",)


def test_detect_matched_workflow_signals_multiple_signals_partial_match() -> None:
    from generate_repo_overview.models import WorkflowSignal

    result = signal_detection.detect_matched_workflow_signals(
        tree_paths={".github/workflows/ci.yml"},
        read_text=lambda _: (
            "jobs:\n"
            "  daily:\n"
            "    uses: org/workflows/.github/workflows/daily.yml@main\n"
        ),
        workflow_signals=(
            WorkflowSignal(
                label="Daily Workflow",
                reference="org/workflows/.github/workflows/daily.yml@",
            ),
            WorkflowSignal(
                label="Nightly Build",
                reference="org/workflows/.github/workflows/nightly.yml@",
            ),
        ),
    )
    assert result == ("Daily Workflow",)


def test_get_commits_since_release_returns_none_when_compare_is_lazy() -> None:
    class LazyComparison:
        @property
        def total_commits(self) -> int:
            raise RuntimeError("Not Found")

    repository = SimpleNamespace(compare=lambda base, head: LazyComparison())
    release = SimpleNamespace(tag_name="v1.2.3")

    assert (
        repo_entry.get_commits_since_release(
            repository,
            release=release,
            default_branch="main",
            default_branch_sha="abc123",
        )
        is None
    )


def test_collect_snapshot_reports_rest_api_limits_before_and_after(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_github_module = ModuleType("github")

    class FakeToken:
        def __init__(self, token: str) -> None:
            self.token = token

    class FakeAuth:
        Token = FakeToken

    class FakeGithub:
        def __init__(self, *, auth: FakeToken, lazy: bool) -> None:
            self.auth = auth
            self.lazy = lazy
            self.rate_limit_calls = 0

        def get_rate_limit(self) -> SimpleNamespace:
            self.rate_limit_calls += 1
            return SimpleNamespace(
                core=SimpleNamespace(
                    limit=5000,
                    remaining=5000 - self.rate_limit_calls,
                    used=self.rate_limit_calls,
                    reset=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
                )
            )

        def get_organization(self, org_name: str) -> SimpleNamespace:
            return SimpleNamespace(name=org_name)

    fake_github_module_any = cast("Any", fake_github_module)
    fake_github_module_any.Auth = FakeAuth
    fake_github_module_any.Github = FakeGithub

    monkeypatch.setitem(sys.modules, "github", fake_github_module)
    monkeypatch.setattr(collector, "resolve_github_token", lambda token_env: "token")
    monkeypatch.setenv("GH_TOKEN", "original-token")
    observed_gh_tokens: list[str | None] = []

    def fake_fetch_repositories(*args: Any, **kwargs: Any) -> list[RepoEntry]:
        observed_gh_tokens.append(os.getenv("GH_TOKEN"))
        return []

    monkeypatch.setattr(collector, "fetch_repositories", fake_fetch_repositories)

    snapshot = collector.collect_snapshot(
        config=OverviewConfig((OrgConfig(org_name="eclipse-score"),)),
        cache_path=None,
    )

    captured = capsys.readouterr()

    assert snapshot.org_name == "eclipse-score"
    assert snapshot.repos == ()
    assert observed_gh_tokens == ["token"]
    assert os.getenv("GH_TOKEN") == "original-token"
    assert (
        "GitHub REST API rate limit before collection: remaining 4999/5000, "
        "used 1, resets at 2026-04-14T12:00:00+00:00" in captured.err
    )
    assert (
        "GitHub REST API rate limit after collection: remaining 4998/5000, "
        "used 2, resets at 2026-04-14T12:00:00+00:00" in captured.err
    )


def test_fetch_repositories_reports_per_repository_progress(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools_repo = SimpleNamespace(archived=False, name="tools")
    alpha_repo = SimpleNamespace(archived=False, name="alpha")
    organization = SimpleNamespace(login="eclipse-score")
    cached_snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="alpha",
                description="Alpha",
                category="Infrastructure",
                subcategory="Tooling",
            ),
        ),
    )

    original_collect_repository_entry = repo_entry.collect_repository_entry
    original_fetch_active_repositories = collector.fetch_active_repositories

    def fake_collect_repository_entry(**kwargs: Any) -> RepoEntry:
        return RepoEntry(
            name=kwargs["repository_name"],
            description="placeholder",
            category="Infrastructure",
            subcategory="Tooling",
        )

    try:
        collector.fetch_active_repositories = lambda organization, **_kwargs: {
            "tools": collector.ActiveRepositoryData(
                repository=tools_repo,
                custom_properties={},
            ),
            "alpha": collector.ActiveRepositoryData(
                repository=alpha_repo,
                custom_properties={},
            ),
        }
        repo_entry.collect_repository_entry = fake_collect_repository_entry
        collector.fetch_repositories(
            cast("Any", organization),
            existing_snapshot=cached_snapshot,
        )
    finally:
        repo_entry.collect_repository_entry = original_collect_repository_entry
        collector.fetch_active_repositories = original_fetch_active_repositories

    captured = capsys.readouterr()

    assert "Found 2 active repositories" in captured.err
    assert "Extracted custom properties for 0 repositories" in captured.err
    assert "Collecting repository details with up to 2 parallel workers" in captured.err


def test_platform_docs_loads_all_configured_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repos = [
        RepoEntry(
            "logging",
            "",
            "Modules",
            "General",
            content=DeepContentSignals(
                sphinx_features=(
                    SphinxItem(
                        "docs/features/removed",
                        "Removed",
                        "feat__removed",
                        "removed/source",
                    ),
                ),
            ),
        )
    ]
    resolved: list[str] = []

    class Resolver:
        def get_repo(self, full_name_or_id: str) -> object:
            resolved.append(full_name_or_id)
            return SimpleNamespace(
                full_name=full_name_or_id,
                clone_url=f"https://github.com/{full_name_or_id}.git",
                default_branch="main",
            )

    resolver = Resolver()

    def fake_enrich(
        repos: list[RepoEntry],
        *,
        checkout_path: Path,
        source_repo: str,
    ) -> list[RepoEntry]:
        assert checkout_path.name == source_repo.rsplit("/", maxsplit=1)[-1]
        return [
            replace(
                entry,
                content=replace(
                    entry.content,
                    sphinx_features=(
                        *entry.content.sphinx_features,
                        SphinxItem(
                            "docs/features/logging",
                            "Logging",
                            "feat__logging",
                            source_repo,
                        ),
                    ),
                ),
            )
            if entry.name == "logging"
            else entry
            for entry in repos
        ]

    monkeypatch.setattr(
        collector.platform_docs,
        "enrich_repositories_from_platform_docs",
        fake_enrich,
    )
    monkeypatch.setattr(
        collector,
        "sync_repository_checkout",
        lambda **kwargs: Path(kwargs["checkout_path"]),
    )

    enriched = collector.enrich_repositories_with_platform_docs(
        repos,
        github=resolver,
        platform_repos=(
            "eclipse-score/score",
            "example/private-features",
        ),
        status_prefix="test",
    )

    assert resolved == [
        "eclipse-score/score",
        "example/private-features",
    ]
    assert tuple(item.source_repo for item in enriched[0].content.sphinx_features) == (
        "eclipse-score/score",
        "example/private-features",
    )


def test_fetch_repositories_preserves_sorted_output_with_parallel_collection() -> None:
    alpha_repo = SimpleNamespace(archived=False, name="alpha")
    tools_repo = SimpleNamespace(archived=False, name="tools")
    organization = SimpleNamespace(login="eclipse-score")

    original_collect_repository_entry = repo_entry.collect_repository_entry
    original_fetch_active_repositories = collector.fetch_active_repositories
    try:
        collector.fetch_active_repositories = lambda organization, **_kwargs: {
            "tools": collector.ActiveRepositoryData(
                repository=tools_repo,
                custom_properties={},
            ),
            "alpha": collector.ActiveRepositoryData(
                repository=alpha_repo,
                custom_properties={},
            ),
        }

        def fake_collect_repository_entry(**kwargs: Any) -> RepoEntry:
            if kwargs["repository_name"] == "alpha":
                time.sleep(0.03)
            return RepoEntry(
                name=kwargs["repository_name"],
                description="placeholder",
                category="Infrastructure",
                subcategory="Tooling",
            )

        repo_entry.collect_repository_entry = fake_collect_repository_entry
        repos = collector.fetch_repositories(cast("Any", organization))
    finally:
        repo_entry.collect_repository_entry = original_collect_repository_entry
        collector.fetch_active_repositories = original_fetch_active_repositories

    assert [repo.name for repo in repos] == ["alpha", "tools"]


def test_resolve_max_collection_workers_prefers_positive_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REPO_OVERVIEW_MAX_WORKERS", "12")

    assert collector.resolve_max_collection_workers() == 12


def test_resolve_max_collection_workers_ignores_invalid_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REPO_OVERVIEW_MAX_WORKERS", "nope")

    assert (
        collector.resolve_max_collection_workers()
        == collector.DEFAULT_MAX_COLLECTION_WORKERS
    )


class TestBuildRepoEntryGroupingLevels:
    """Tests for grouping_levels parameter on build_repo_entry."""

    def _minimal_signals(self) -> "repo_entry.DeepContentPayload":
        return default_content_signals()

    def test_no_grouping_levels_returns_defaults(self) -> None:
        entry = repo_entry.build_repo_entry(
            "my-repo",
            "A repo",
            custom_properties={"category": "Infra", "subcategory": "Tooling"},
            grouping_levels=(),
            content_signals=self._minimal_signals(),
            registry_signals=RegistrySignals(),
            volatile_metrics=repo_entry.collect_volatile_metrics(
                _FakeMinimalRepo(), default_branch=None, default_branch_sha=None
            ),
        )
        from generate_repo_overview.models import DEFAULT_CATEGORY, DEFAULT_SUBCATEGORY

        assert entry.category == DEFAULT_CATEGORY
        assert entry.subcategory == DEFAULT_SUBCATEGORY

    def test_one_grouping_level_resolves_category_only(self) -> None:
        entry = repo_entry.build_repo_entry(
            "my-repo",
            "A repo",
            custom_properties={"area": "Platform"},
            grouping_levels=(GroupingLevel(property="area", default="Unknown"),),
            content_signals=self._minimal_signals(),
            registry_signals=RegistrySignals(),
            volatile_metrics=repo_entry.collect_volatile_metrics(
                _FakeMinimalRepo(), default_branch=None, default_branch_sha=None
            ),
        )
        from generate_repo_overview.models import DEFAULT_SUBCATEGORY

        assert entry.category == "Platform"
        assert entry.subcategory == DEFAULT_SUBCATEGORY

    def test_one_grouping_level_uses_level_default_on_missing_property(self) -> None:
        entry = repo_entry.build_repo_entry(
            "my-repo",
            "A repo",
            custom_properties={},
            grouping_levels=(GroupingLevel(property="area", default="Unknown"),),
            content_signals=self._minimal_signals(),
            registry_signals=RegistrySignals(),
            volatile_metrics=repo_entry.collect_volatile_metrics(
                _FakeMinimalRepo(), default_branch=None, default_branch_sha=None
            ),
        )
        assert entry.category == "Unknown"

    def test_two_custom_grouping_levels_both_resolved(self) -> None:
        entry = repo_entry.build_repo_entry(
            "my-repo",
            "A repo",
            custom_properties={"area": "Platform", "team": "Core"},
            grouping_levels=(
                GroupingLevel(property="area", default="Unknown"),
                GroupingLevel(property="team", default="Common"),
            ),
            content_signals=self._minimal_signals(),
            registry_signals=RegistrySignals(),
            volatile_metrics=repo_entry.collect_volatile_metrics(
                _FakeMinimalRepo(), default_branch=None, default_branch_sha=None
            ),
        )
        assert entry.category == "Platform"
        assert entry.subcategory == "Core"

    def test_classic_grouping_levels_match_old_hardcoded_behavior(self) -> None:
        entry = repo_entry.build_repo_entry(
            "my-repo",
            "A repo",
            custom_properties={"category": "Infra", "subcategory": "Tooling"},
            grouping_levels=(
                GroupingLevel(property="category", default="Uncategorized"),
                GroupingLevel(property="subcategory", default="General"),
            ),
            content_signals=self._minimal_signals(),
            registry_signals=RegistrySignals(),
            volatile_metrics=repo_entry.collect_volatile_metrics(
                _FakeMinimalRepo(), default_branch=None, default_branch_sha=None
            ),
        )
        assert entry.category == "Infra"
        assert entry.subcategory == "Tooling"


class _FakeMinimalRepo:
    """Minimal repo stub for volatile metrics collection with no API calls."""

    open_issues_count = 0
    pushed_at = None
    stargazers_count = 0
    forks_count = 0

    def get_branch(self, _: str) -> None:
        return None

    def get_pulls(self, *_: Any, **__: Any) -> list[Any]:
        return []

    def get_latest_release(self) -> None:
        return None


def test_snapshot_from_dict_filters_empty_tracked_deps() -> None:
    """D4.6: TrackedDep with empty repo/module_name is dropped during deserialization."""
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="test",
        generated_at="2026-01-01",
        repos=(),
        organization_signals={
            "test": OrganizationSignals(
                tracked_deps=(TrackedDep(repo="org/valid", module_name="valid_mod"),)
            )
        },
    )
    raw = snapshot.to_dict()
    raw["organization_signals"]["test"]["tracked_deps"].extend(
        [
            {"repo": "", "module_name": "empty_repo"},
            {"repo": "org/x", "module_name": ""},
        ]
    )

    loaded = RepoSnapshot.from_dict(raw)

    assert loaded.signals_for("test").tracked_deps == (
        TrackedDep(repo="org/valid", module_name="valid_mod"),
    )


def test_load_snapshot_if_present_ignores_mismatched_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cache_path = tmp_path / "repo_overview.json"
    cache_path.write_text(
        (
            "{\n"
            '  "schema_version": 2,\n'
            '  "org_name": "eclipse-score",\n'
            '  "generated_at": "2026-04-13T12:00:00+00:00",\n'
            '  "repos": []\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    assert snapshot_io.load_snapshot_if_present(cache_path) is None
    # A full collection after a schema change must be explainable in CI logs.
    diagnostics = capsys.readouterr().err
    assert "Cannot reuse snapshot cache" in diagnostics
    assert "Unsupported snapshot schema version 2" in diagnostics
    assert "collecting without cached data" in diagnostics


def _fetch_with_failing_repositories(
    monkeypatch: pytest.MonkeyPatch,
    *,
    repository_names: tuple[str, ...],
    failing: set[str],
    cached: tuple[RepoEntry, ...] = (),
    snapshot_workflow_signals: tuple[WorkflowSignal, ...] = (),
) -> list[RepoEntry]:
    def collect(**kwargs: Any) -> RepoEntry:
        name = kwargs["repository_name"]
        if name in failing:
            raise RuntimeError(f"Could not synchronize repository {name}.")
        return RepoEntry(
            name=name, description="fresh", category="Tools", subcategory="General"
        )

    monkeypatch.setattr(
        collector,
        "fetch_active_repositories",
        lambda organization, **_kwargs: {
            name: collector.ActiveRepositoryData(
                repository=SimpleNamespace(archived=False, name=name),
                custom_properties={},
            )
            for name in repository_names
        },
    )
    monkeypatch.setattr(repo_entry, "collect_repository_entry", collect)
    return collector.fetch_repositories(
        cast("Any", SimpleNamespace(login="eclipse-score")),
        existing_snapshot=RepoSnapshot(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            org_name="eclipse-score",
            generated_at="2026-04-13T12:00:00+00:00",
            repos=cached,
            organization_signals={
                "eclipse-score": OrganizationSignals(
                    workflow_signals=snapshot_workflow_signals
                )
            },
        ),
    )


def test_failed_repository_keeps_its_earlier_result_and_others_are_collected(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repos = _fetch_with_failing_repositories(
        monkeypatch,
        repository_names=("alpha", "beta", "broken", "new-and-broken"),
        failing={"broken", "new-and-broken"},
        cached=(
            RepoEntry(
                name="broken",
                description="earlier",
                category="Tools",
                subcategory="General",
            ),
        ),
    )

    assert [(repo.name, repo.description) for repo in repos] == [
        ("alpha", "fresh"),
        ("beta", "fresh"),
        ("broken", "earlier"),
    ]
    assert (
        "warning: collection failed for 2 of 4 repositories in eclipse-score: "
        "broken, new-and-broken" in capsys.readouterr().err
    )


def test_collection_fails_when_most_repositories_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="failed for 2 of 3 repositories"):
        _fetch_with_failing_repositories(
            monkeypatch,
            repository_names=("alpha", "beta", "gamma"),
            failing={"alpha", "beta"},
            cached=(
                RepoEntry(
                    name="alpha",
                    description="earlier",
                    category="Tools",
                    subcategory="General",
                ),
            ),
        )


def test_only_repository_of_an_organization_may_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    earlier = RepoEntry(
        name="only", description="earlier", category="Tools", subcategory="General"
    )

    repos = _fetch_with_failing_repositories(
        monkeypatch,
        repository_names=("only",),
        failing={"only"},
        cached=(earlier,),
        # Changed workflow signals invalidate the content cache, but the
        # earlier entry still stands in for the failed repository.
        snapshot_workflow_signals=(WorkflowSignal("Old", "org/repo/old.yml@"),),
    )

    assert [(repo.name, repo.description) for repo in repos] == [("only", "earlier")]
