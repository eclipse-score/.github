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
        '- `Docs-As-Code Version`: `version = "..."` for `bazel_dep(name = "score_docs_as_code", ...)` in the repository root `MODULE.bazel`.',
        "- `Lint/Style Config`: `yes` if `.gitlint`, `.editorconfig`, or `.pre-commit-config.yaml` exists.",
        "- `GitHub Actions`: `yes` if `.github/workflows` exists.",
        "- `Daily Workflow`: `yes` if any workflow file references `cicd-workflows/.github/workflows/daily.yml@...`.",
        "- `Coverage Config`: `yes` if `coverage.yml`, `coverage.xml`, `pytest.ini`, or `.coveragerc` exists.",
        "- `Latest Release`: release tag name, falling back to the release name when needed.",
        "- `Commits Since Release`: compare the latest release tag to the current default branch head. `-` means no release or no comparable tag.",
        "",
    ]
    lines.extend(render_overview_section(repos, org_name=snapshot.org_name))
    lines.extend(render_automation_section(repos, org_name=snapshot.org_name))
    lines.extend(render_topic_sections(repos, org_name=snapshot.org_name))
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


def render_overview_section(repos: list[RepoEntry], org_name: str) -> list[str]:
    lines = [
        "## Repository Overview",
        "",
        "| Repository | Category | Last Push | Issues | PRs | Bazel Version | Stars | Forks |",
        "|------------|----------|-----------|--------|-----|---------------|-------|-------|",
    ]
    for repo in repos:
        url = f"https://github.com/{org_name}/{repo.name}"
        lines.append(
            f"| [{repo.name}]({url}) | {repo.category} | {repo.last_push_date or '-'} | "
            f"{repo.open_issues} | {repo.open_prs} | {repo.bazel_version or '-'} | "
            f"{repo.stars} | {repo.forks} |"
        )
    lines.append("")
    return lines


def render_automation_section(repos: list[RepoEntry], org_name: str) -> list[str]:
    lines = [
        "## Delivery And Automation",
        "",
        "| Repository | Lint/Style Config | GitHub Actions | Daily Workflow | Coverage Config | Latest Release | Release Date | Commits Since Release |",
        "|------------|-------------------|----------------|----------------|-----------------|----------------|--------------|-----------------------|",
    ]
    for repo in repos:
        url = f"https://github.com/{org_name}/{repo.name}"
        lines.append(
            f"| [{repo.name}]({url}) | {render_bool(repo.has_lint_config)} | "
            f"{render_bool(repo.has_ci)} | {render_bool(repo.uses_cicd_daily_workflow)} | "
            f"{render_bool(repo.has_coverage_config)} | {repo.latest_release_version or '-'} | "
            f"{repo.latest_release_date or '-'} | {render_optional_int(repo.commits_since_latest_release)} |"
        )
    lines.append("")
    return lines


def render_topic_sections(repos: list[RepoEntry], org_name: str) -> list[str]:
    topic_repos = [repo for repo in repos if repo.docs_as_code_version]
    if not topic_repos:
        return []

    lines = [
        "## Topic Views",
        "",
        "### Docs-As-Code",
        "",
        "| Repository | Category | Docs-As-Code Version | Bazel Version | GitHub Actions | Daily Workflow | Last Push | Issues | PRs |",
        "|------------|----------|----------------------|---------------|----------------|----------------|-----------|--------|-----|",
    ]
    for repo in topic_repos:
        url = f"https://github.com/{org_name}/{repo.name}"
        lines.append(
            f"| [{repo.name}]({url}) | {repo.category} | {repo.docs_as_code_version or '-'} | "
            f"{repo.bazel_version or '-'} | {render_bool(repo.has_ci)} | "
            f"{render_bool(repo.uses_cicd_daily_workflow)} | {repo.last_push_date or '-'} | "
            f"{repo.open_issues} | {repo.open_prs} |"
        )
    lines.append("")
    return lines


def render_bool(value: bool) -> str:
    return "yes" if value else "no"


def render_optional_int(value: int | None) -> str:
    return str(value) if value is not None else "-"


def has_latest_release(entry: RepoEntry) -> bool:
    return entry.latest_release_version is not None or entry.latest_release_date is not None
