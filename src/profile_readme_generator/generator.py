from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from github import Auth, Github
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


@dataclass(frozen=True, slots=True)
class SubcategoryConfig:
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class CategoryConfig:
    name: str
    description: str
    subcategories: tuple[SubcategoryConfig, ...] = ()


@dataclass(frozen=True, slots=True)
class ReadmeConfig:
    categories: tuple[CategoryConfig, ...]


@dataclass(frozen=True, slots=True)
class ConfigIndex:
    category_positions: dict[str, int]
    category_names: dict[str, str]
    category_descriptions: dict[str, str]
    subcategory_names: dict[str, dict[str, str]]
    subcategory_descriptions: dict[str, dict[str, str]]

    @classmethod
    def from_config(cls, config: ReadmeConfig | None) -> ConfigIndex:
        if config is None:
            return cls(
                category_positions={},
                category_names={},
                category_descriptions={},
                subcategory_names={},
                subcategory_descriptions={},
            )

        category_positions: dict[str, int] = {}
        category_names: dict[str, str] = {}
        category_descriptions: dict[str, str] = {}
        subcategory_names: dict[str, dict[str, str]] = {}
        subcategory_descriptions: dict[str, dict[str, str]] = {}

        for index, category in enumerate(config.categories):
            category_key = category.name.casefold()
            category_positions[category_key] = index
            category_names[category_key] = category.name
            category_descriptions[category_key] = category.description
            subcategory_names[category_key] = {
                subcategory.name.casefold(): subcategory.name
                for subcategory in category.subcategories
            }
            subcategory_descriptions[category_key] = {
                subcategory.name.casefold(): subcategory.description
                for subcategory in category.subcategories
            }

        return cls(
            category_positions=category_positions,
            category_names=category_names,
            category_descriptions=category_descriptions,
            subcategory_names=subcategory_names,
            subcategory_descriptions=subcategory_descriptions,
        )

    def canonical_category_name(self, category: str) -> str:
        return self.category_names.get(category.casefold(), category)

    def category_description(self, category: str) -> str:
        return self.category_descriptions.get(category.casefold(), "")

    def canonical_subcategory_name(self, category: str, subcategory: str) -> str:
        return self.subcategory_names.get(category.casefold(), {}).get(
            subcategory.casefold(),
            subcategory,
        )

    def subcategory_description(self, category: str, subcategory: str) -> str:
        return self.subcategory_descriptions.get(category.casefold(), {}).get(
            subcategory.casefold(),
            "",
        )


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
        "--config",
        type=Path,
        help="Optional category config file that defines order and descriptions",
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
    try:
        from github import Auth, Github
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing PyGithub. Install project dependencies before running the generator."
        ) from exc

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
    print_status(f"Loading README config from {describe_config_source(args.config)}")
    config = load_config(args.config)
    print_status("Loading README template")
    template = load_template(args.template)
    print_status("Rendering README")
    markdown = render_readme(
        repos,
        template=template,
        config=config,
        org_name=args.org,
    )

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


def load_config(config_path: Path | None) -> ReadmeConfig:
    config_content = (
        config_path.read_text(encoding="utf-8")
        if config_path is not None
        else files("profile_readme_generator")
        .joinpath("profile_readme_config.toml")
        .read_text(encoding="utf-8")
    )
    config_source = describe_config_source(config_path)
    raw_categories = tomllib.loads(config_content).get("categories", [])
    if not isinstance(raw_categories, list):
        message = (
            f"Invalid config in {config_source}: 'categories' must be a list of tables."
        )
        raise ValueError(message)

    categories = tuple(
        parse_category_config(raw_category, config_source)
        for raw_category in raw_categories
    )
    return ReadmeConfig(categories=categories)


def parse_category_config(raw_category: object, config_source: str) -> CategoryConfig:
    if not isinstance(raw_category, dict):
        message = (
            f"Invalid config in {config_source}: each category entry must be a table."
        )
        raise ValueError(message)

    name = require_non_empty_string(
        raw_category.get("name"),
        config_source=config_source,
        field_name="each category needs a non-empty name",
    )
    description = require_string(
        raw_category.get("description", ""),
        config_source=config_source,
        field_name="category descriptions must be strings",
    ).strip()

    raw_subcategories = raw_category.get("subcategories", [])
    if not isinstance(raw_subcategories, list):
        message = (
            f"Invalid config in {config_source}: category subcategories must be a list of tables."
        )
        raise ValueError(message)

    subcategories = tuple(
        parse_subcategory_config(raw_subcategory, config_source)
        for raw_subcategory in raw_subcategories
    )
    return CategoryConfig(
        name=name,
        description=description,
        subcategories=subcategories,
    )


def parse_subcategory_config(
    raw_subcategory: object,
    config_source: str,
) -> SubcategoryConfig:
    if not isinstance(raw_subcategory, dict):
        message = (
            f"Invalid config in {config_source}: each subcategory entry must be a table."
        )
        raise ValueError(message)

    return SubcategoryConfig(
        name=require_non_empty_string(
            raw_subcategory.get("name"),
            config_source=config_source,
            field_name="each subcategory needs a non-empty name",
        ),
        description=require_string(
            raw_subcategory.get("description", ""),
            config_source=config_source,
            field_name="subcategory descriptions must be strings",
        ).strip(),
    )


def require_non_empty_string(
    value: object,
    *,
    config_source: str,
    field_name: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid config in {config_source}: {field_name}.")
    return value.strip()


def require_string(
    value: object,
    *,
    config_source: str,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Invalid config in {config_source}: {field_name}.")
    return value


def describe_config_source(config_path: Path | None) -> str:
    return str(config_path) if config_path is not None else "package default config"


def normalize_group_name(value: str | list[str] | None, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, list):
        cleaned = [item.strip() for item in value if item.strip()]
        return ", ".join(cleaned) if cleaned else fallback
    cleaned = value.strip()
    return cleaned or fallback


def group_repositories(
    repos: list[RepoEntry],
    config: ReadmeConfig | None = None,
) -> GroupedRepos:
    grouped: GroupedRepos = defaultdict(lambda: defaultdict(list))
    for repo in repos:
        grouped[repo.category][repo.subcategory].append(repo)

    config_index = ConfigIndex.from_config(config)

    return {
        category: {
            subcategory: sorted(entries, key=lambda entry: entry.name.casefold())
            for subcategory, entries in sorted(
                subcategories.items(),
                key=lambda item: item[0].casefold(),
            )
        }
        for category, subcategories in sorted(
            grouped.items(),
            key=lambda item: (
                config_index.category_positions.get(
                    item[0].casefold(),
                    len(config_index.category_positions),
                ),
                item[0].casefold(),
            ),
        )
    }


def render_readme(
    repos: list[RepoEntry],
    template: str,
    config: ReadmeConfig | None = None,
    org_name: str = DEFAULT_ORG,
) -> str:
    grouped = group_repositories(repos, config=config)
    config_index = ConfigIndex.from_config(config)
    lines: list[str] = []

    for index, (category, subcategories) in enumerate(grouped.items()):
        if index > 0:
            lines.extend(("---", ""))
        lines.extend(
            render_category_section(
                category=category,
                subcategories=subcategories,
                config_index=config_index,
                org_name=org_name,
            )
        )

    repo_sections = "\n".join(lines).rstrip()
    markdown = template.replace("{{ repo_sections }}", repo_sections)
    return markdown.rstrip() + "\n"


def render_category_section(
    *,
    category: str,
    subcategories: dict[str, list[RepoEntry]],
    config_index: ConfigIndex,
    org_name: str,
) -> list[str]:
    canonical_category = config_index.canonical_category_name(category)
    lines = [f"### {canonical_category}", ""]

    category_description = config_index.category_description(canonical_category)
    if category_description:
        lines.extend((category_description, ""))

    if len(subcategories) == 1 and DEFAULT_SUBCATEGORY in subcategories:
        lines.extend(
            render_general_subcategory_table(
                category=canonical_category,
                entries=subcategories[DEFAULT_SUBCATEGORY],
                config_index=config_index,
                org_name=org_name,
            )
        )
        return lines

    for subcategory, entries in subcategories.items():
        lines.extend(
            render_subcategory_section(
                category=canonical_category,
                subcategory=subcategory,
                entries=entries,
                config_index=config_index,
                org_name=org_name,
            )
        )

    return lines


def render_general_subcategory_table(
    *,
    category: str,
    entries: list[RepoEntry],
    config_index: ConfigIndex,
    org_name: str,
) -> list[str]:
    lines: list[str] = []
    description = config_index.subcategory_description(category, DEFAULT_SUBCATEGORY)
    if description:
        lines.extend((description, ""))
    lines.extend(render_repo_table(entries, org_name=org_name))
    return lines


def render_subcategory_section(
    *,
    category: str,
    subcategory: str,
    entries: list[RepoEntry],
    config_index: ConfigIndex,
    org_name: str,
) -> list[str]:
    canonical_subcategory = config_index.canonical_subcategory_name(
        category,
        subcategory,
    )
    lines = [f"#### {canonical_subcategory}"]

    description = config_index.subcategory_description(category, canonical_subcategory)
    if description:
        lines.extend(("", description))

    lines.extend(("", *render_repo_table(entries, org_name=org_name)))
    return lines


def render_repo_table(entries: list[RepoEntry], org_name: str) -> list[str]:
    lines = [
        "| Repository | Description |",
        "|------------|-------------|",
    ]
    lines.extend(render_repo_row(entry, org_name=org_name) for entry in entries)
    lines.append("")
    return lines


def render_repo_row(entry: RepoEntry, org_name: str = DEFAULT_ORG) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    safe_description = escape_markdown_table_cell(entry.description)
    return f"| [{entry.name}]({url}) | {safe_description} |"


def escape_markdown_table_cell(text: str) -> str:
    normalized = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return normalized.replace("|", r"\|")


def print_status(message: str) -> None:
    print(f"[generate-profile-readme] {message}", file=sys.stderr)
