from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import DEFAULT_ORG

if TYPE_CHECKING:
    from .models import RepoEntry, RepoSnapshot


def render_metrics_report(snapshot: RepoSnapshot) -> str:
    repos = sorted(snapshot.repos, key=lambda repo: repo.name.casefold())
    has_topic_views = any(repo.docs_as_code_version for repo in repos)
    lines = [
        "# Cross-Repo Metrics Report",
        "",
        f"Generated on {snapshot.generated_at}",
        "",
        *render_summary(repos),
        "",
        "## Table Of Contents",
        "",
        "- [Repository Overview](#repository-overview)",
        "- [Ownership](#ownership)",
        "- [Ownership With Versions](#ownership-with-versions)",
        "- [Delivery And Automation](#delivery-and-automation)",
        "",
    ]
    if has_topic_views:
        lines.insert(-1, "- [Topic Views](#topic-views)")
    lines.extend(render_overview_section(repos, org_name=snapshot.org_name))
    lines.extend(render_ownership_section(repos, org_name=snapshot.org_name))
    lines.extend(
        render_ownership_with_versions_section(repos, org_name=snapshot.org_name)
    )
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
    latest_release = entry.latest_release_version or "-"
    release_date = entry.latest_release_date or "-"
    commits_since_release = render_optional_int(entry.commits_since_latest_release)
    last_push = entry.last_push_date or "-"
    return (
        f"| [{entry.name}]({url}) | {entry.category} | {last_push} | "
        f"{entry.open_issues} | {entry.open_ready_prs} | {entry.open_draft_prs} | "
        f"{render_bool(entry.is_bazel_repo)} | "
        f"{render_bool(entry.has_lint_config)} | {render_bool(entry.has_ci)} | "
        f"{render_bool(entry.uses_cicd_daily_workflow)} | "
        f"{render_bool(entry.has_coverage_config)} | {latest_release} | "
        f"{release_date} | {commits_since_release} | {entry.stars} | {entry.forks} |"
    )


def render_overview_section(repos: list[RepoEntry], org_name: str) -> list[str]:
    lines = [
        "## Repository Overview",
        "",
        "- `Open Issues`: open issues only. Pull requests are excluded.",
        "- `Open Ready PRs` and `Open Draft PRs`: open pull requests split by draft status.",
        "- `Bazel Repo`: `yes` if the repo contains `.bazelversion`, `MODULE.bazel`, `WORKSPACE`, or `WORKSPACE.bazel`.",
        "",
    ]
    lines.extend(
        render_category_tables(
            repos,
            org_name=org_name,
            header="| Repository | Last Push | Open Issues | Open Ready PRs | Open Draft PRs | Bazel Repo | Stars | Forks |",
            divider="|------------|-----------|-------------|----------------|----------------|------------|-------|-------|",
            row_renderer=render_overview_row,
        )
    )
    return lines


def render_ownership_section(repos: list[RepoEntry], org_name: str) -> list[str]:
    lines = [
        "## Ownership",
        "",
        "- `Maintainers In Bazel Registry`: names listed in `bazel_registry/modules/*/metadata.json`. This is registry metadata, not authoritative maintainer truth.",
        "- `Codeowners (.github/CODEOWNERS)`: owners resolved for the `.github/CODEOWNERS` path from that repository's `.github/CODEOWNERS` file. `-` means the file is missing or no owners matched.",
        "",
    ]
    lines.extend(
        render_category_tables(
            repos,
            org_name=org_name,
            header="| Repository | Maintainers In Bazel Registry | Codeowners (.github/CODEOWNERS) |",
            divider="|------------|------------------------------|--------------------------------|",
            row_renderer=render_ownership_row,
        )
    )
    return lines


def render_ownership_with_versions_section(
    repos: list[RepoEntry],
    org_name: str,
) -> list[str]:
    lines = [
        "## Ownership With Versions",
        "",
        "- `Latest Bazel Registry Version`: first version listed for that module in bazel_registry metadata.",
        '- `Docs-As-Code Version`: `version = "..."` for `bazel_dep(name = "score_docs_as_code", ...)` in the repository root `MODULE.bazel`.',
        "- `Latest Release`: release tag name, falling back to the release name when needed.",
        "- `Release Date`: published date of the latest release when available.",
        "- `Commits Since Release`: compare the latest release tag to the current default branch head. `-` means no release or no comparable tag.",
        "",
    ]
    lines.extend(
        render_category_tables(
            repos,
            org_name=org_name,
            header="| Repository | Maintainers In Bazel Registry | Codeowners (.github/CODEOWNERS) | Latest Bazel Registry Version | Bazel Version | Docs-As-Code Version | Latest Release | Release Date | Commits Since Release |",
            divider="|------------|------------------------------|--------------------------------|-------------------------------|---------------|----------------------|----------------|--------------|-----------------------|",
            row_renderer=render_ownership_with_versions_row,
        )
    )
    return lines


def render_automation_section(repos: list[RepoEntry], org_name: str) -> list[str]:
    lines = [
        "## Delivery And Automation",
        "",
        "- `Lint/Style Config`: `yes` if `.gitlint`, `.editorconfig`, or `.pre-commit-config.yaml` exists.",
        "- `GitHub Actions`: `yes` if `.github/workflows` exists.",
        "- `Daily Workflow`: `yes` if any workflow file references `cicd-workflows/.github/workflows/daily.yml@...`.",
        "- `Coverage Config`: `yes` if `coverage.yml`, `coverage.xml`, `pytest.ini`, or `.coveragerc` exists.",
        "",
    ]
    lines.extend(
        render_category_tables(
            repos,
            org_name=org_name,
            header="| Repository | Lint/Style Config | GitHub Actions | Daily Workflow | Coverage Config |",
            divider="|------------|-------------------|----------------|----------------|-----------------|",
            row_renderer=render_automation_row,
        )
    )
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
        '- `Docs-As-Code Version`: `version = "..."` for `bazel_dep(name = "score_docs_as_code", ...)` in the repository root `MODULE.bazel`.',
        "",
    ]
    lines.extend(
        render_category_tables(
            topic_repos,
            org_name=org_name,
            header="| Repository | Docs-As-Code Version | Bazel Version | GitHub Actions | Daily Workflow | Last Push | Open Issues | Open Ready PRs | Open Draft PRs |",
            divider="|------------|----------------------|---------------|----------------|----------------|-----------|-------------|----------------|----------------|",
            row_renderer=render_docs_as_code_row,
            heading_level=4,
        )
    )
    return lines


def render_category_tables(
    repos: list[RepoEntry],
    *,
    org_name: str,
    header: str,
    divider: str,
    row_renderer,
    heading_level: int = 3,
) -> list[str]:
    lines: list[str] = []
    heading_prefix = "#" * heading_level
    for category, category_repos in group_repos_by_category(repos):
        lines.extend(
            [
                f"{heading_prefix} {category}",
                "",
                header,
                divider,
            ]
        )
        for repo in category_repos:
            lines.append(row_renderer(repo, org_name=org_name))
        lines.append("")
    return lines


def group_repos_by_category(repos: list[RepoEntry]) -> list[tuple[str, list[RepoEntry]]]:
    grouped: dict[str, list[RepoEntry]] = {}
    for repo in repos:
        grouped.setdefault(repo.category, []).append(repo)

    return [
        (category, sorted(category_repos, key=lambda repo: repo.name.casefold()))
        for category, category_repos in sorted(grouped.items(), key=lambda item: item[0].casefold())
    ]


def render_overview_row(entry: RepoEntry, *, org_name: str) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    return (
        f"| [{entry.name}]({url}) | {entry.last_push_date or '-'} | "
        f"{entry.open_issues} | {entry.open_ready_prs} | {entry.open_draft_prs} | "
        f"{render_bool(entry.is_bazel_repo)} | "
        f"{entry.stars} | {entry.forks} |"
    )


def render_ownership_row(entry: RepoEntry, *, org_name: str) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    return (
        f"| [{entry.name}]({url}) | {render_list(entry.maintainers_in_bazel_registry)} | "
        f"{render_list(entry.codeowners)} |"
    )


def render_ownership_with_versions_row(entry: RepoEntry, *, org_name: str) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    return (
        f"| [{entry.name}]({url}) | {render_list(entry.maintainers_in_bazel_registry)} | "
        f"{render_list(entry.codeowners)} | {entry.latest_bazel_registry_version or '-'} | "
        f"{entry.bazel_version or '-'} | {entry.docs_as_code_version or '-'} | "
        f"{entry.latest_release_version or '-'} | {entry.latest_release_date or '-'} | "
        f"{render_optional_int(entry.commits_since_latest_release)} |"
    )


def render_automation_row(entry: RepoEntry, *, org_name: str) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    return (
        f"| [{entry.name}]({url}) | {render_bool(entry.has_lint_config)} | "
        f"{render_bool(entry.has_ci)} | {render_bool(entry.uses_cicd_daily_workflow)} | "
        f"{render_bool(entry.has_coverage_config)} |"
    )


def render_docs_as_code_row(entry: RepoEntry, *, org_name: str) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    return (
        f"| [{entry.name}]({url}) | {entry.docs_as_code_version or '-'} | "
        f"{entry.bazel_version or '-'} | {render_bool(entry.has_ci)} | "
        f"{render_bool(entry.uses_cicd_daily_workflow)} | {entry.last_push_date or '-'} | "
        f"{entry.open_issues} | {entry.open_ready_prs} | {entry.open_draft_prs} |"
    )


def render_bool(value: bool) -> str:
    return "yes" if value else "no"


def render_optional_int(value: int | None) -> str:
    return str(value) if value is not None else "-"


def render_list(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def has_latest_release(entry: RepoEntry) -> bool:
    return entry.latest_release_version is not None or entry.latest_release_date is not None
