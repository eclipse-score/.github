import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import generate_repo_overview.collector as collector
from generate_repo_overview.metrics_report import render_metrics_report
from generate_repo_overview.models import RepoEntry, RepoSnapshot


def test_snapshot_round_trip_preserves_repository_overview(tmp_path: Path) -> None:
    snapshot = RepoSnapshot(
        schema_version=8,
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
                open_ready_prs=1,
                open_draft_prs=0,
                is_bazel_repo=True,
                bazel_version="8.4.2",
                codeowners=("@infra-team",),
                maintainers_in_bazel_registry=("Andrey Babanin (@4og)",),
                latest_bazel_registry_version="0.2.5",
                has_lint_config=True,
                has_gitlint_config=True,
                has_pyproject_toml=True,
                has_pre_commit_config=True,
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
        schema_version=8,
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
            self.open_issues_count = 3
            self.stargazers_count = 3
            self.forks_count = 4

        def get_branch(self, branch_name: str) -> SimpleNamespace:
            assert branch_name == "main"
            return SimpleNamespace(commit=SimpleNamespace(sha="abc123"))

        def get_git_tree(self, ref: str, recursive: bool = True) -> SimpleNamespace:
            self.tree_calls += 1
            return SimpleNamespace(tree=[])

        def get_pulls(self, state: str = "open") -> list[SimpleNamespace]:
            assert state == "open"
            return [SimpleNamespace(draft=False)]

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
        schema_version=collector.SNAPSHOT_SCHEMA_VERSION,
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
                is_bazel_repo=True,
                bazel_version="8.4.2",
                codeowners=("@infra-team",),
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
            open_ready_prs=1,
            open_draft_prs=0,
            is_bazel_repo=True,
            bazel_version="8.4.2",
            codeowners=("@infra-team",),
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


def test_get_open_pull_request_counts_splits_ready_and_draft() -> None:
    repository = SimpleNamespace(
        get_pulls=lambda state="open": [
            SimpleNamespace(draft=False),
            SimpleNamespace(raw_data={"draft": True}),
            SimpleNamespace(draft=False),
        ]
    )

    assert collector.get_open_pull_request_counts(repository) == {
        "ready": 2,
        "draft": 1,
        "total": 3,
    }
    assert collector.get_open_issue_count(
        SimpleNamespace(open_issues_count=5),
        open_pull_request_total=3,
    ) == 2


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


def test_get_bazel_dep_version_extracts_docs_as_code_dependency_version() -> None:
    assert (
        collector.get_bazel_dep_version(
            'bazel_dep(name = "score_docs_as_code", version = "4.0.0")\n',
            module_name="score_docs_as_code",
        )
        == "4.0.0"
    )


def test_get_bazel_dep_version_ignores_other_dependencies() -> None:
    assert (
        collector.get_bazel_dep_version(
            'bazel_dep(name = "score_process", version = "1.2.3")\n',
            module_name="score_docs_as_code",
        )
        is None
    )


def test_get_codeowners_for_path_prefers_specific_codeowners_rule() -> None:
    assert collector.get_codeowners_for_path(
        """
* @infra-team
.github/CODEOWNERS @docs-team @platform-team
""".strip(),
        target_path=".github/CODEOWNERS",
    ) == ("@docs-team", "@platform-team")


def test_get_codeowners_for_path_normalizes_comma_separated_owners() -> None:
    assert collector.get_codeowners_for_path(
        """
* @armin-acn, @johannes-esr, @masc2023
""".strip(),
        target_path=".github/CODEOWNERS",
    ) == ("@armin-acn", "@johannes-esr", "@masc2023")


def test_parse_bazel_registry_metadata_maps_active_repository_and_latest_version() -> None:
    metadata = collector.parse_bazel_registry_metadata(
        """
{
  "maintainers": [
    {
      "name": "Andrey Babanin",
      "github": "4og"
    }
  ],
  "repository": [
    "github:eclipse-score/baselibs",
    "github:someone-else/ignored"
  ],
  "versions": ["0.2.5", "0.2.4"]
}
""".strip(),
        active_repository_names={"baselibs"},
    )

    assert metadata == {
        "baselibs": {
            "maintainers_in_bazel_registry": ("Andrey Babanin (@4og)",),
            "latest_bazel_registry_version": "0.2.5",
        }
    }


def test_merge_bazel_registry_metadata_combines_owners_and_keeps_latest_version() -> None:
    assert collector.merge_bazel_registry_metadata(
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


def test_fetch_repositories_reports_per_repository_progress(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools_repo = SimpleNamespace(archived=False, name="tools")
    alpha_repo = SimpleNamespace(archived=False, name="alpha")
    organization = SimpleNamespace(
        get_repos=lambda: [tools_repo, alpha_repo],
        list_custom_property_values=list,
    )
    cached_snapshot = RepoSnapshot(
        schema_version=8,
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

    original_collect_repository_entry = collector.collect_repository_entry

    def fake_collect_repository_entry(**kwargs):
        return RepoEntry(
            name=kwargs["repository_name"],
            description="placeholder",
            category="Infrastructure",
            subcategory="Tooling",
        )

    try:
        collector.collect_repository_entry = fake_collect_repository_entry
        collector.fetch_repositories(
            organization,
            existing_snapshot=cached_snapshot,
        )
    finally:
        collector.collect_repository_entry = original_collect_repository_entry

    captured = capsys.readouterr()

    assert "Found 2 active repositories" in captured.err
    assert "Loaded custom properties for 0 repositories" in captured.err
    assert "Collecting repository details with up to 2 parallel workers" in captured.err
    assert "[1/2] Collecting alpha (using cached content signals)" in captured.err
    assert "[2/2] Collecting tools (fetching content signals)" in captured.err
    assert "[1/2] Finished alpha" in captured.err or "[1/2] Finished tools" in captured.err


def test_fetch_repositories_preserves_sorted_output_with_parallel_collection() -> None:
    alpha_repo = SimpleNamespace(archived=False, name="alpha")
    tools_repo = SimpleNamespace(archived=False, name="tools")
    organization = SimpleNamespace(
        get_repos=lambda: [tools_repo, alpha_repo],
        list_custom_property_values=list,
    )

    original_collect_repository_entry = collector.collect_repository_entry
    try:
        def fake_collect_repository_entry(**kwargs):
            if kwargs["repository_name"] == "alpha":
                time.sleep(0.03)
            return RepoEntry(
                name=kwargs["repository_name"],
                description="placeholder",
                category="Infrastructure",
                subcategory="Tooling",
            )

        collector.collect_repository_entry = fake_collect_repository_entry
        repos = collector.fetch_repositories(organization)
    finally:
        collector.collect_repository_entry = original_collect_repository_entry

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


def test_metrics_report_renders_summary_and_table() -> None:
    snapshot = RepoSnapshot(
        schema_version=8,
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
                open_prs=2,
                open_ready_prs=1,
                open_draft_prs=1,
                is_bazel_repo=True,
                bazel_version="8.4.2",
                codeowners=(
                    "@docs-team",
                    "@platform-team",
                    "@infra-team",
                    "@qa-team",
                ),
                maintainers_in_bazel_registry=(
                    "Andrey Babanin (@4og)",
                    "Nikola Radakovic (@nradakovic)",
                    "Pawel Rutka (@pawelrutkaq)",
                ),
                latest_bazel_registry_version="0.2.5",
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
    assert "## Table Of Contents" in markdown
    assert "- [Repository Overview](#repository-overview)" in markdown
    assert "- [Versions](#versions)" in markdown
    assert "- [Ownership](#ownership)" not in markdown
    assert "- [Ownership With Versions](#ownership-with-versions)" not in markdown
    assert "`⚙ GitHub Actions`: shown when `.github/workflows` exists." in markdown
    assert "## Repository Overview" in markdown
    assert "## Versions" in markdown
    assert "| Repository | Ownership | Last Commit |" in markdown
    assert "## Ownership" not in markdown
    assert "## Ownership With Versions" not in markdown
    assert "## Delivery And Automation" in markdown
    assert "### Infrastructure" in markdown
    assert (
        "| [tools](https://github.com/eclipse-score/tools) | "
        "<small><sub><small>Codeowners: @docs-team, @platform-team, @infra-team, @qa-team<br><br>"
        "Maintainers In Bazel Registry: @4og, @nradakovic, @pawelrutkaq</small></sub></small> | "
        "2026-04-12 | 2 | 1 | 1 | 🏗 | v1.2.3 | 🟡 7 | 3 | 4 |"
        in markdown
    )
    assert (
        "| [tools](https://github.com/eclipse-score/tools) | "
        "🟢 8.4.2 | ⚪ - |"
        in markdown
    )
    assert (
        "| [tools](https://github.com/eclipse-score/tools) | - | - | - | ⚙ | yes | no |"
        in markdown
    )


def test_metrics_report_uses_no_for_non_bazel_repo_in_overview() -> None:
    snapshot = RepoSnapshot(
        schema_version=8,
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
        "| [tools](https://github.com/eclipse-score/tools) | - "
        "| - | 0 | 0 | 0 | - | - | - | 0 | 0 |"
        in markdown
    )


def test_metrics_report_ownership_cell_skips_maintainers_for_non_bazel_repo() -> None:
    snapshot = RepoSnapshot(
        schema_version=8,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="tools",
                description="Tooling",
                category="Infrastructure",
                subcategory="Tooling",
                is_bazel_repo=False,
                codeowners=("@docs-team",),
                maintainers_in_bazel_registry=("Andrey Babanin (@4og)",),
            ),
        ),
    )

    markdown = render_metrics_report(snapshot)

    assert (
        "<small><sub><small>Codeowners: @docs-team</small></sub></small>"
        in markdown
    )
    assert "Maintainers In Bazel Registry:" not in markdown


def test_metrics_report_ownership_cell_marks_missing_maintainers_for_bazel_repo() -> None:
    snapshot = RepoSnapshot(
        schema_version=8,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="tools",
                description="Tooling",
                category="Infrastructure",
                subcategory="Tooling",
                is_bazel_repo=True,
                codeowners=("@docs-team",),
                maintainers_in_bazel_registry=(),
            ),
        ),
    )

    markdown = render_metrics_report(snapshot)

    assert "Maintainers In Bazel Registry:" not in markdown


def test_metrics_report_renders_versions_table() -> None:
    snapshot = RepoSnapshot(
        schema_version=8,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="process_description",
                description="Process docs",
                category="Infrastructure",
                subcategory="tooling",
                last_push_date="2026-04-12",
                open_issues=35,
                open_prs=8,
                open_ready_prs=6,
                open_draft_prs=2,
                is_bazel_repo=True,
                bazel_version="8.4.2",
                docs_as_code_version="4.0.0",
                has_ci=True,
                uses_cicd_daily_workflow=True,
            ),
        ),
    )

    markdown = render_metrics_report(snapshot)

    assert "## Versions" in markdown
    assert "🔴 6" in markdown
    assert (
        "| [process_description](https://github.com/eclipse-score/process_description) | "
        "🟢 8.4.2 | ⚪ 4.0.0 |"
        in markdown
    )


def test_versions_table_docs_as_code_color_rules() -> None:
    snapshot = RepoSnapshot(
        schema_version=8,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="docs-as-code",
                description="Docs",
                category="Infrastructure",
                subcategory="Tooling",
                latest_release_version="v4.1.3",
                bazel_version="8.6.0",
            ),
            RepoEntry(
                name="same-release",
                description="Same",
                category="Infrastructure",
                subcategory="Tooling",
                docs_as_code_version="4.1.3",
                bazel_version="8.5.0",
            ),
            RepoEntry(
                name="same-minor",
                description="Minor",
                category="Infrastructure",
                subcategory="Tooling",
                docs_as_code_version="4.1.1",
                bazel_version="8.4.0",
            ),
            RepoEntry(
                name="older",
                description="Older",
                category="Infrastructure",
                subcategory="Tooling",
                docs_as_code_version="3.9.9",
                bazel_version="8.3.0",
            ),
            RepoEntry(
                name="none",
                description="None",
                category="Infrastructure",
                subcategory="Tooling",
                docs_as_code_version=None,
                bazel_version=None,
            ),
        ),
    )

    markdown = render_metrics_report(snapshot)

    assert "| [docs-as-code](https://github.com/eclipse-score/docs-as-code) | 🟢 8.6.0 | ⚪ - |" in markdown
    assert "| [same-release](https://github.com/eclipse-score/same-release) | 🔴 8.5.0 | 🟢 4.1.3 |" in markdown
    assert "| [same-minor](https://github.com/eclipse-score/same-minor) | 🔴 8.4.0 | 🟡 4.1.1 |" in markdown
    assert "| [older](https://github.com/eclipse-score/older) | 🔴 8.3.0 | 🔴 3.9.9 |" in markdown
    assert "| [none](https://github.com/eclipse-score/none) | ⚪ - | ⚪ - |" in markdown


def test_fetch_repositories_does_not_reuse_content_signals_from_older_schema() -> None:
    pushed_at = datetime(2026, 4, 15, 10, 0, tzinfo=UTC)

    class FakeRepo:
        archived = False
        name = "logging"
        description = "Logging"
        default_branch = "main"

        def __init__(self) -> None:
            self.pushed_at = pushed_at
            self.open_issues_count = 1
            self.stargazers_count = 2
            self.forks_count = 3

        def get_branch(self, branch_name: str) -> SimpleNamespace:
            assert branch_name == "main"
            return SimpleNamespace(commit=SimpleNamespace(sha="abc123"))

        def get_pulls(self, state: str = "open") -> list[SimpleNamespace]:
            assert state == "open"
            return []

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
                name="logging",
                description="Logging",
                category="modules",
                subcategory="General",
                default_branch="main",
                default_branch_sha="abc123",
                bazel_version="8.3.0",
            ),
        ),
    )

    original_inspect_repository_content = collector.inspect_repository_content
    original_get_latest_release_details = collector.get_latest_release_details
    try:
        collector.inspect_repository_content = lambda repository, ref: {
            "is_bazel_repo": True,
            "bazel_version": "8.3.0",
            "codeowners": ("@infra-team",),
            "docs_as_code_version": "3.0.0",
            "has_lint_config": False,
            "has_ci": True,
            "uses_cicd_daily_workflow": False,
            "has_coverage_config": False,
        }
        collector.get_latest_release_details = lambda *args, **kwargs: {
            "version": None,
            "date": None,
            "commits_since_release": None,
        }

        repos = collector.fetch_repositories(
            organization,
            existing_snapshot=cached_snapshot,
        )
    finally:
        collector.inspect_repository_content = original_inspect_repository_content
        collector.get_latest_release_details = original_get_latest_release_details

    assert repos[0].docs_as_code_version == "3.0.0"
    assert repos[0].codeowners == ("@infra-team",)
