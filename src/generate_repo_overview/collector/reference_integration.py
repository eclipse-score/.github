from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from repo_cache import default_cache_directory

from generate_repo_overview.console import print_status
from generate_repo_overview.models import DependencyOverride, parse_github_repository

from .bazel_modules import parse_dependencies, read_module_files
from .git_checkout import sync_repository_checkout
from .registry_metadata import get_bazel_registry_repositories_by_module


@dataclass(frozen=True, slots=True)
class KnownGoodPin:
    module: str
    group: str
    branch: str
    version: str | None
    commit_hash: str | None


@dataclass(frozen=True, slots=True)
class GitRefComparison:
    right_ahead_by: int
    left_ahead_by: int


class _CompletableCommit(Protocol):
    """Minimal PyGithub commit interface needed to validate a lazy ref."""

    sha: str

    def complete(self) -> object: ...


def fetch_reference_integration_repository_names(
    *,
    reference_integration_repository: object | None,
    active_repository_names: set[str],
    registry_repository: str,
    org_name: str,
) -> set[str]:
    if reference_integration_repository is None:
        return set()

    default_branch = cast(
        "str | None",
        getattr(reference_integration_repository, "default_branch", None),
    )
    repository = cast(
        "str | None", getattr(reference_integration_repository, "full_name", None)
    )
    if default_branch is None or repository is None:
        return set()

    checkout_path = sync_repository_checkout(
        repository=repository,
        default_branch=default_branch,
        checkout_path=default_cache_directory() / repository,
    )
    if checkout_path is None:
        return set()

    declarations = parse_dependencies(
        read_module_files(
            lambda path: read_checkout_file(checkout_path, Path(path))
        ).values()
    )
    registry_repositories = get_bazel_registry_repositories_by_module(
        active_repository_names=active_repository_names,
        registry_repository=registry_repository,
        org_name=org_name,
    )

    # GitHub names compare case-insensitively, but the collector keys use API spelling.
    names_by_casefold = {name.casefold(): name for name in active_repository_names}
    repositories: set[str] = set()
    for declaration in declarations:
        if declaration.override is DependencyOverride.GIT and declaration.remote:
            repository_name = parse_github_remote_repository_name(
                declaration.remote, org_name=org_name
            )
        else:
            repository_name = registry_repositories.get(declaration.module)
        if repository_name is not None:
            active_name = names_by_casefold.get(repository_name.casefold())
            if active_name is not None:
                repositories.add(active_name)

    return repositories


def fetch_reference_integration_pins(
    *,
    reference_integration_repository: object | None,
    active_repository_names: set[str],
    org_name: str,
) -> dict[str, KnownGoodPin]:
    """Read each active repository's integration pin from known_good.json."""
    if reference_integration_repository is None:
        return {}

    default_branch = cast(
        "str | None",
        getattr(reference_integration_repository, "default_branch", None),
    )
    repository = cast(
        "str | None", getattr(reference_integration_repository, "full_name", None)
    )
    if default_branch is None or repository is None:
        return {}

    checkout_path = sync_repository_checkout(
        repository=repository,
        default_branch=default_branch,
        checkout_path=default_cache_directory() / repository,
    )
    if checkout_path is None:
        return {}
    content = read_checkout_file(checkout_path, Path("known_good.json"))
    if content is None:
        return {}
    return parse_known_good_pins(
        content,
        active_repository_names=active_repository_names,
        org_name=org_name,
    )


def parse_known_good_pins(
    content: str,
    *,
    active_repository_names: set[str],
    org_name: str,
) -> dict[str, KnownGoodPin]:
    """Map GitHub repositories to their module group, branch, and version pin."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    modules = data.get("modules")
    if not isinstance(modules, dict):
        return {}

    names_by_casefold = {name.casefold(): name for name in active_repository_names}
    versions: dict[str, KnownGoodPin] = {}
    for group_name, group in modules.items():
        if not isinstance(group, dict):
            continue
        for module_name, module in group.items():
            parsed_pin = _parse_known_good_module(
                module,
                module_name=str(module_name),
                group_name=str(group_name),
                names_by_casefold=names_by_casefold,
                org_name=org_name,
            )
            if parsed_pin is not None:
                repository_name, pin = parsed_pin
                versions[repository_name] = pin
    return versions


def _parse_known_good_module(
    module: object,
    *,
    module_name: str,
    group_name: str,
    names_by_casefold: dict[str, str],
    org_name: str,
) -> tuple[str, KnownGoodPin] | None:
    if not isinstance(module, dict):
        return None
    repository_url = module.get("repo")
    if not isinstance(repository_url, str):
        return None
    repository_name = parse_github_remote_repository_name(
        repository_url,
        org_name=org_name,
    )
    if repository_name is None:
        return None
    active_name = names_by_casefold.get(repository_name.casefold())
    if active_name is None:
        return None
    raw_version = module.get("version")
    raw_hash = module.get("hash")
    version = raw_version.strip() if isinstance(raw_version, str) else ""
    commit_hash = raw_hash.strip() if isinstance(raw_hash, str) else ""
    if not version and not commit_hash:
        return None
    raw_branch = module.get("branch")
    branch = raw_branch.strip() if isinstance(raw_branch, str) else ""
    return active_name, KnownGoodPin(
        module=module_name,
        group=group_name,
        branch=branch or "main",
        version=version or None,
        commit_hash=commit_hash or None,
    )


def resolve_reference_integration_pin(
    repository: object,
    pin: KnownGoodPin,
) -> str | None:
    """Resolve a known-good hash or version pin to a Git commit ref."""
    pin_ref = pin.commit_hash
    if pin_ref is None and pin.version:
        get_commit = getattr(repository, "get_commit", None)
        if not callable(get_commit):
            return None
        version_refs = [pin.version]
        if not pin.version.startswith("v"):
            version_refs.append(f"v{pin.version}")
        for version_ref in version_refs:
            try:
                commit = cast("_CompletableCommit", get_commit(version_ref))
                # The collector uses PyGithub's lazy mode. An incomplete
                # Commit can expose the requested ref as ``sha`` before
                # GitHub has confirmed that the ref exists.
                commit.complete()
                resolved_sha = commit.sha
            except Exception:
                continue
            if isinstance(resolved_sha, str) and resolved_sha:
                pin_ref = resolved_sha
                break
    if pin_ref is None:
        return None
    return pin_ref


def compare_git_refs(
    repository: object,
    *,
    left_ref: str,
    right_ref: str,
) -> GitRefComparison | None:
    """Compare refs and count commits unique to each side, including divergence."""

    # PyGithub runs in lazy mode, so the HTTP request fires on attribute access
    # rather than in ``compare()`` itself; those reads therefore live inside the
    # same guard as the request so no lazy failure can escape the worker pool.
    # A GitHub ``No common ancestor`` 404 is logged as a warning (it is an
    # expected divergent-lineage case) and treated as uncomparable.
    compare = getattr(repository, "compare", None)
    if not callable(compare):
        return None
    try:
        result = compare(left_ref, right_ref)
        right_ahead_by = getattr(result, "ahead_by", None)
        left_ahead_by = getattr(result, "behind_by", None)
    except Exception as exc:
        if "No common ancestor" in str(exc):
            print_status(
                f"warning: {_repository_label(repository)}: refs {left_ref!r} "
                f"and {right_ref!r} share no common ancestor; "
                "reference-integration metrics are unavailable.",
            )
        return None
    if not isinstance(right_ahead_by, int) or not isinstance(left_ahead_by, int):
        return None
    return GitRefComparison(
        right_ahead_by=right_ahead_by,
        left_ahead_by=left_ahead_by,
    )


def _repository_label(repository: object) -> str:
    for attribute in ("full_name", "name"):
        value = getattr(repository, attribute, None)
        if isinstance(value, str) and value:
            return value
    return "<unknown>"


def read_checkout_file(checkout_path: Path, relative_path: Path) -> str | None:
    try:
        path = safe_checkout_path(checkout_path, relative_path)
    except ValueError:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def safe_checkout_path(checkout_path: Path, relative_path: Path) -> Path:
    checkout_root = checkout_path.resolve()
    candidate = (checkout_root / relative_path).resolve()
    candidate.relative_to(checkout_root)
    return candidate


def parse_github_remote_repository_name(
    remote: str,
    *,
    org_name: str,
) -> str | None:
    repository = parse_github_repository(remote)
    if repository is None:
        return None
    owner, name = repository.split("/")
    return name if owner.casefold() == org_name.casefold() else None
