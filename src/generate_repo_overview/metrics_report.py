from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import DEFAULT_ORG

if TYPE_CHECKING:
    from .models import RepoEntry, RepoSnapshot


def render_metrics_report(snapshot: RepoSnapshot) -> str:
    repos = sorted(snapshot.repos, key=lambda repo: repo.name.casefold())
    lines = [
        "# Cross-Repo Metrics Report",
        "",
        f"Generated on {snapshot.generated_at}",
        "",
        *render_summary(repos),
        "",
        "## Signal Definitions",
        "",
        "- `Bazel Version`: first non-comment line from `.bazelversion`. `-` means the repo does not declare one there.",
        "- `Lint/Style Config`: `yes` if `.gitlint`, `.editorconfig`, or `.pre-commit-config.yaml` exists.",
        "- `GitHub Actions`: `yes` if `.github/workflows` exists.",
        "- `Daily Workflow`: `yes` if any workflow file references `cicd-workflows/.github/workflows/daily.yml@...`.",
        "- `Coverage Config`: `yes` if `coverage.yml`, `coverage.xml`, `pytest.ini`, or `.coveragerc` exists.",
        "- `Latest Release`: release tag name, falling back to the release name when needed.",
        "- `Commits Since Release`: compare the latest release tag to the current default branch head. `-` means no release or no comparable tag.",
        "",
        "| Repository | Category | Last Push | Issues | PRs | Bazel Version | Lint/Style Config | GitHub Actions | Daily Workflow | Coverage Config | Latest Release | Release Date | Commits Since Release | Stars | Forks |",
        "|------------|----------|-----------|--------|-----|---------------|-------------------|----------------|----------------|-----------------|----------------|--------------|-----------------------|-------|-------|",
    ]
    lines.extend(render_metrics_row(repo, org_name=snapshot.org_name) for repo in repos)
    return "\n".join(lines).rstrip() + "\n"


def render_summary(repos: list[RepoEntry]) -> list[str]:
    return [
        f"- Repositories: {len(repos)}",
        f"- With GitHub Actions: {sum(repo.has_ci for repo in repos)}",
        f"- Using daily workflow: {sum(repo.uses_cicd_daily_workflow for repo in repos)}",
        f"- With lint/style config: {sum(repo.has_lint_config for repo in repos)}",
        f"- With coverage config: {sum(repo.has_coverage_config for repo in repos)}",
        f"- With releases: {sum(has_latest_release(repo) for repo in repos)}",
    ]


def render_metrics_row(entry: RepoEntry, org_name: str = DEFAULT_ORG) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    bazel_version = entry.bazel_version or "-"
    latest_release = entry.latest_release_version or "-"
    release_date = entry.latest_release_date or "-"
    commits_since_release = render_optional_int(entry.commits_since_latest_release)
    last_push = entry.last_push_date or "-"
    return (
        f"| [{entry.name}]({url}) | {entry.category} | {last_push} | "
        f"{entry.open_issues} | {entry.open_prs} | {bazel_version} | "
        f"{render_bool(entry.has_lint_config)} | {render_bool(entry.has_ci)} | "
        f"{render_bool(entry.uses_cicd_daily_workflow)} | "
        f"{render_bool(entry.has_coverage_config)} | {latest_release} | "
        f"{release_date} | {commits_since_release} | {entry.stars} | {entry.forks} |"
    )


def render_bool(value: bool) -> str:
    return "yes" if value else "no"


def render_optional_int(value: int | None) -> str:
    return str(value) if value is not None else "-"


def has_latest_release(entry: RepoEntry) -> bool:
    return entry.latest_release_version is not None or entry.latest_release_date is not None
