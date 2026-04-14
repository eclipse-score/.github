import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import generate_repo_overview.collector as collector
from generate_repo_overview.metrics_report import render_metrics_report
from generate_repo_overview.models import RepoEntry, RepoSnapshot


def test_snapshot_round_trip_preserves_repository_overview(tmp_path: Path) -> None:
    snapshot = RepoSnapshot(
        schema_version=2,
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
                last_push_date="2026-04-12",
                open_issues=2,
                open_prs=1,
                bazel_version="8.4.2",
                has_lint_config=True,
                has_ci=True,
                uses_cicd_daily_workflow=True,
                has_coverage_config=False,
                latest_release_version="v1.2.3",
                latest_release_date="2026-04-01",
                commits_since_latest_release=7,
                stars=3,
                forks=4,
            ),
        ),
    )
    snapshot_path = tmp_path / "repo_overview.json"

    collector.write_snapshot(snapshot, snapshot_path)

    assert collector.load_snapshot(snapshot_path) == snapshot


def test_ensure_snapshot_prefers_existing_cache(tmp_path: Path) -> None:
    snapshot = RepoSnapshot(
        schema_version=2,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(RepoEntry("tools", "Tooling", "Infrastructure", "Tooling"),),
    )
    snapshot_path = tmp_path / "repo_overview.json"
    collector.write_snapshot(snapshot, snapshot_path)

    loaded_snapshot = collector.ensure_snapshot(cache_path=snapshot_path)

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
            self.open_issues_count = 2
            self.stargazers_count = 3
            self.forks_count = 4

        def get_branch(self, branch_name: str) -> SimpleNamespace:
            assert branch_name == "main"
            return SimpleNamespace(commit=SimpleNamespace(sha="abc123"))

        def get_git_tree(self, ref: str, recursive: bool = True) -> SimpleNamespace:
            self.tree_calls += 1
            return SimpleNamespace(tree=[])

        def get_pulls(self, state: str = "open") -> SimpleNamespace:
            assert state == "open"
            return SimpleNamespace(totalCount=1)

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
    organization = SimpleNamespace(
        get_repos=lambda: [fake_repo],
        list_custom_property_values=list,
    )
    cached_snapshot = RepoSnapshot(
        schema_version=2,
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
                bazel_version="8.4.2",
                has_lint_config=True,
                has_ci=True,
                uses_cicd_daily_workflow=True,
                has_coverage_config=False,
            ),
        ),
    )

    repos = collector.fetch_repositories(
        organization,
        existing_snapshot=cached_snapshot,
    )

    assert fake_repo.tree_calls == 0
    assert repos == [
        RepoEntry(
            name="tools",
            description="Tooling",
            category="Uncategorized",
            subcategory="General",
            default_branch="main",
            default_branch_sha="abc123",
            last_push_date="2026-04-13",
            open_issues=2,
            open_prs=1,
            bazel_version="8.4.2",
            has_lint_config=True,
            has_ci=True,
            uses_cicd_daily_workflow=True,
            has_coverage_config=False,
            latest_release_version="v1.2.3",
            latest_release_date="2026-04-01",
            commits_since_latest_release=7,
            stars=3,
            forks=4,
        )
    ]


def test_get_latest_release_details_returns_none_when_release_lookup_is_lazy() -> None:
    class LazyFailingRelease:
        @property
        def tag_name(self) -> str:
            raise RuntimeError("Not Found")

    repository = SimpleNamespace(get_latest_release=lambda: LazyFailingRelease())

    assert collector.get_latest_release_details(
        repository,
        default_branch="main",
        default_branch_sha="abc123",
    ) == {
        "version": None,
        "date": None,
        "commits_since_release": None,
    }


def test_get_latest_release_version_prefers_raw_tag_name() -> None:
    release = SimpleNamespace(
        raw_data={"tag_name": "v0.2.5", "name": "Release 0.2.5"},
        name="Release 0.2.5",
        tag_name="latest",
    )

    assert collector.get_latest_release_version(release) == "v0.2.5"


def test_get_latest_release_version_ignores_latest_sentinel_without_raw_data() -> None:
    release = SimpleNamespace(name="latest", title="latest")

    assert collector.get_latest_release_version(release) is None


def test_detect_bazel_version_ignores_module_version_without_dot_bazelversion() -> None:
    assert (
        collector.detect_bazel_version(
            SimpleNamespace(),
            tree_paths={"MODULE.bazel"},
            ref="abc123",
        )
        is None
    )


def test_uses_cicd_daily_workflow_detects_shared_daily_workflow_reference() -> None:
    class FakeRepo:
        def get_contents(self, path: str, ref: str) -> SimpleNamespace:
            assert path == ".github/workflows/nightly.yml"
            assert ref == "abc123"
            return SimpleNamespace(
                decoded_content=(
                    b"jobs:\n"
                    b"  daily:\n"
                    b"    uses: eclipse-score/cicd-workflows/.github/workflows/daily.yml@main\n"
                )
            )

    assert collector.uses_cicd_daily_workflow(
        FakeRepo(),
        tree_paths={".github/workflows/nightly.yml"},
        ref="abc123",
    )


def test_get_commits_since_release_returns_none_when_compare_is_lazy() -> None:
    class LazyComparison:
        @property
        def total_commits(self) -> int:
            raise RuntimeError("Not Found")

    repository = SimpleNamespace(compare=lambda base, head: LazyComparison())
    release = SimpleNamespace(tag_name="v1.2.3")

    assert (
        collector.get_commits_since_release(
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

    fake_github_module.Auth = FakeAuth
    fake_github_module.Github = FakeGithub

    monkeypatch.setitem(sys.modules, "github", fake_github_module)
    monkeypatch.setattr(collector, "resolve_github_token", lambda token_env: "token")
    monkeypatch.setattr(collector, "fetch_repositories", lambda *args, **kwargs: [])

    snapshot = collector.collect_snapshot(cache_path=None)

    captured = capsys.readouterr()

    assert snapshot.org_name == "eclipse-score"
    assert snapshot.repos == ()
    assert (
        "GitHub REST API rate limit before collection: remaining 4999/5000, "
        "used 1, resets at 2026-04-14T12:00:00+00:00"
        in captured.err
    )
    assert (
        "GitHub REST API rate limit after collection: remaining 4998/5000, "
        "used 2, resets at 2026-04-14T12:00:00+00:00"
        in captured.err
    )


def test_metrics_report_renders_summary_and_table() -> None:
    snapshot = RepoSnapshot(
        schema_version=2,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="tools",
                description="Tooling",
                category="Infrastructure",
                subcategory="Tooling",
                last_push_date="2026-04-12",
                open_issues=2,
                open_prs=1,
                bazel_version="8.4.2",
                has_lint_config=True,
                has_ci=True,
                uses_cicd_daily_workflow=True,
                has_coverage_config=False,
                latest_release_version="v1.2.3",
                latest_release_date="2026-04-01",
                commits_since_latest_release=7,
                stars=3,
                forks=4,
            ),
        ),
    )

    markdown = render_metrics_report(snapshot)

    assert "# Cross-Repo Metrics Report" in markdown
    assert "- Repositories: 1" in markdown
    assert "- With GitHub Actions: 1" in markdown
    assert "- Using daily workflow: 1" in markdown
    assert "## Signal Definitions" in markdown
    assert "`GitHub Actions`: `yes` if `.github/workflows` exists." in markdown
    assert (
        "| [tools](https://github.com/eclipse-score/tools) | Infrastructure | "
        "2026-04-12 | 2 | 1 | 8.4.2 | yes | yes | yes | no | v1.2.3 | 2026-04-01 | 7 | 3 | 4 |"
        in markdown
    )


def test_metrics_report_uses_dash_for_missing_bazel_version() -> None:
    snapshot = RepoSnapshot(
        schema_version=2,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="tools",
                description="Tooling",
                category="Infrastructure",
                subcategory="Tooling",
            ),
        ),
    )

    markdown = render_metrics_report(snapshot)

    assert (
        "| [tools](https://github.com/eclipse-score/tools) | Infrastructure | - | 0 | 0 | - | no | no | no | no | - | - | - | 0 | 0 |"
        in markdown
    )
