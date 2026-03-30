from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, cast

from github import Auth, Github

if TYPE_CHECKING:
    from github.Organization import Organization

DEFAULT_ORG = "eclipse-score"
DEFAULT_OUTPUT = Path("profile/README.md")
DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_SUBCATEGORY = "General"


@dataclass(frozen=True, slots=True)
class RepoEntry:
    name: str
    description: str
    category: str
    subcategory: str


GroupedRepos = dict[str, dict[str, list[RepoEntry]]]
CustomPropertyValue = str | list[str] | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", default=DEFAULT_ORG, help="GitHub organization name")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Markdown file to write",
    )
    parser.add_argument(
        "--template",
        type=Path,
        help="Optional markdown template file with a {{ repo_sections }} placeholder",
    )
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable that contains the GitHub token",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated markdown instead of writing the file",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print_status("Resolving GitHub token")
    token = resolve_github_token(args.token_env)
    if not token:
        message = f"Missing GitHub token. Set {args.token_env} or authenticate with `gh auth login`."
        raise SystemExit(message)

    print_status(f"Connecting to GitHub organization {args.org}")
    github = Github(auth=Auth.Token(token), lazy=True)
    organization = github.get_organization(args.org)
    print_status("Fetching repositories and custom properties")
    repos = fetch_repositories(organization)
    print_status(f"Loaded {len(repos)} repositories")
    print_status("Loading README template")
    template = load_template(args.template)
    print_status("Rendering README")
    markdown = render_readme(repos, template=template, org_name=args.org)

    if args.dry_run:
        print_status("Dry run complete")
        print(markdown)
        return 0

    print_status(f"Writing {args.output}")
    args.output.write_text(markdown, encoding="utf-8")
    print_status("README generation complete")
    return 0


def resolve_github_token(token_env: str) -> str | None:
    token = os.getenv(token_env)
    if token:
        return token
    return get_gh_auth_token()


def get_gh_auth_token() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    token = result.stdout.strip()
    return token or None


def fetch_repositories(organization: Organization) -> list[RepoEntry]:
    print_status("Loading repository descriptions")
    descriptions_by_name = fetch_repository_descriptions(organization)
    print_status("Loading repository custom properties in bulk")
    active_repository_names = set(descriptions_by_name)

    repos_by_name: dict[str, RepoEntry] = {}
    for repository_properties in organization.list_custom_property_values():
        if repository_properties.repository_name not in active_repository_names:
            continue
        repo_entry = build_repo_entry(
            repository_name=repository_properties.repository_name,
            description=descriptions_by_name.get(repository_properties.repository_name),
            custom_properties=cast(
                "dict[str, CustomPropertyValue]",
                repository_properties.properties,
            ),
        )
        repos_by_name[repo_entry.name] = repo_entry

    for repository_name, description in descriptions_by_name.items():
        repos_by_name.setdefault(
            repository_name,
            build_repo_entry(
                repository_name=repository_name,
                description=description,
                custom_properties={},
            ),
        )

    return sorted(repos_by_name.values(), key=lambda repo: repo.name.casefold())


def fetch_repository_descriptions(organization: Organization) -> dict[str, str | None]:
    descriptions_by_name: dict[str, str | None] = {}
    for repository in organization.get_repos():
        if repository.archived:
            continue
        descriptions_by_name[repository.name] = repository.description
    return descriptions_by_name


def build_repo_entry(
    repository_name: str,
    description: str | None,
    custom_properties: dict[str, CustomPropertyValue],
) -> RepoEntry:
    category = normalize_group_name(custom_properties.get("category"), DEFAULT_CATEGORY)
    subcategory = normalize_group_name(
        custom_properties.get("subcategory"),
        DEFAULT_SUBCATEGORY,
    )
    return RepoEntry(
        name=repository_name,
        description=description or "(no description)",
        category=category,
        subcategory=subcategory,
    )


def load_template(template_path: Path | None) -> str:
    if template_path is not None:
        return template_path.read_text(encoding="utf-8")
    return (
        files("profile_readme_generator")
        .joinpath("templates/profile_readme.md")
        .read_text(encoding="utf-8")
    )


def normalize_group_name(value: str | list[str] | None, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, list):
        cleaned = [item.strip() for item in value if item.strip()]
        return ", ".join(cleaned) if cleaned else fallback
    cleaned = value.strip()
    return cleaned or fallback


def group_repositories(repos: list[RepoEntry]) -> GroupedRepos:
    grouped: GroupedRepos = defaultdict(lambda: defaultdict(list))
    for repo in repos:
        grouped[repo.category][repo.subcategory].append(repo)
    return {
        category: {
            subcategory: sorted(entries, key=lambda entry: entry.name.casefold())
            for subcategory, entries in sorted(
                subcategories.items(),
                key=lambda item: item[0].casefold(),
            )
        }
        for category, subcategories in sorted(
            grouped.items(), key=lambda item: item[0].casefold()
        )
    }


def render_readme(
    repos: list[RepoEntry],
    template: str,
    org_name: str = DEFAULT_ORG,
) -> str:
    grouped = group_repositories(repos)
    lines: list[str] = []

    for category, subcategories in grouped.items():
        lines.extend((f"### {category}", ""))
        if len(subcategories) == 1 and DEFAULT_SUBCATEGORY in subcategories:
            lines.extend(
                (
                    "| Repository | Description |",
                    "|------------|-------------|",
                )
            )
            lines.extend(
                render_repo_row(entry, org_name=org_name)
                for entry in subcategories[DEFAULT_SUBCATEGORY]
            )
            lines.extend(("",))
            continue

        for subcategory, entries in subcategories.items():
            lines.extend(
                (
                    f"#### {subcategory}",
                    "",
                    "| Repository | Description |",
                    "|------------|-------------|",
                )
            )
            lines.extend(render_repo_row(entry, org_name=org_name) for entry in entries)
            lines.extend(("",))

    repo_sections = "\n".join(lines).rstrip()
    markdown = template.replace("{{ repo_sections }}", repo_sections)
    return markdown.rstrip() + "\n"


def render_repo_row(entry: RepoEntry, org_name: str = DEFAULT_ORG) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    return f"| [{entry.name}]({url}) | {entry.description} |"


def print_status(message: str) -> None:
    print(f"[generate-profile-readme] {message}", file=sys.stderr)
