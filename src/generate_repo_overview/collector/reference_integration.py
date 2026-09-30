from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import urlsplit

from repo_cache import default_cache_directory

from generate_repo_overview.org_config import is_safe_repository_path

from .git_checkout import sync_repository_checkout
from .registry_metadata import parse_bazel_registry_metadata
from .signal_detection import dedupe_preserving_order

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT_MODULE_PATH = Path("MODULE.bazel")
INCLUDE_PATTERN = re.compile(r'\binclude\s*\(\s*"(?P<label>[^"]+)"\s*\)')
BAZEL_DEP_PATTERN = re.compile(r"\bbazel_dep\s*\((?P<body>.*?)\)", re.DOTALL)
GIT_OVERRIDE_PATTERN = re.compile(r"\bgit_override\s*\((?P<body>.*?)\)", re.DOTALL)
NAME_PATTERN = re.compile(r'\bname\s*=\s*"(?P<value>[^"]+)"')
MODULE_NAME_PATTERN = re.compile(r'\bmodule_name\s*=\s*"(?P<value>[^"]+)"')
REMOTE_PATTERN = re.compile(r'\bremote\s*=\s*"(?P<value>[^"]+)"')


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

    module_file_contents = read_included_module_files(checkout_path)
    module_names = get_bazel_dep_names_from_contents(module_file_contents.values())
    git_override_repositories = get_git_override_repositories_by_module(
        module_file_contents.values(),
        active_repository_names=active_repository_names,
        org_name=org_name,
    )
    registry_repositories = get_bazel_registry_repositories_by_module(
        active_repository_names=active_repository_names,
        registry_repository=registry_repository,
    )

    repositories: list[str] = []
    for module_name in module_names:
        repository_name = git_override_repositories.get(module_name)
        if repository_name is None:
            repository_name = registry_repositories.get(module_name)
        if repository_name is not None:
            repositories.append(repository_name)

    return set(dedupe_preserving_order(repositories))


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

    versions: dict[str, KnownGoodPin] = {}
    for group_name, group in modules.items():
        if not isinstance(group, dict):
            continue
        for module_name, module in group.items():
            parsed_pin = _parse_known_good_module(
                module,
                module_name=str(module_name),
                group_name=str(group_name),
                active_repository_names=active_repository_names,
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
    active_repository_names: set[str],
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
    if repository_name not in active_repository_names:
        return None
    raw_version = module.get("version")
    raw_hash = module.get("hash")
    version = raw_version.strip() if isinstance(raw_version, str) else ""
    commit_hash = raw_hash.strip() if isinstance(raw_hash, str) else ""
    if not version and not commit_hash:
        return None
    raw_branch = module.get("branch")
    branch = raw_branch.strip() if isinstance(raw_branch, str) else ""
    return repository_name, KnownGoodPin(
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
    compare = getattr(repository, "compare", None)
    if not callable(compare):
        return None
    try:
        result = compare(left_ref, right_ref)
    except Exception:
        return None

    right_ahead_by = getattr(result, "ahead_by", None)
    left_ahead_by = getattr(result, "behind_by", None)
    if not isinstance(right_ahead_by, int) or not isinstance(left_ahead_by, int):
        return None
    return GitRefComparison(
        right_ahead_by=right_ahead_by,
        left_ahead_by=left_ahead_by,
    )


def read_included_module_files(checkout_path: Path) -> dict[Path, str]:
    pending = [ROOT_MODULE_PATH]
    seen: set[Path] = set()
    contents: dict[Path, str] = {}

    while pending:
        relative_path = pending.pop()
        if relative_path in seen:
            continue
        seen.add(relative_path)

        content = read_checkout_file(checkout_path, relative_path)
        if content is None:
            continue
        contents[relative_path] = content

        for include_label in get_include_labels(content):
            included_path = resolve_include_label(
                include_label,
                current_file=relative_path,
                checkout_path=checkout_path,
            )
            if included_path is not None and included_path not in seen:
                pending.append(included_path)

    return contents


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


def get_include_labels(text: str) -> tuple[str, ...]:
    return tuple(match.group("label") for match in INCLUDE_PATTERN.finditer(text))


def resolve_include_label(
    label: str,
    *,
    current_file: Path,
    checkout_path: Path,
) -> Path | None:
    if label.startswith("//"):
        label_path = label.removeprefix("//")
        package, separator, target = label_path.partition(":")
        if not separator or not target:
            return None
        relative_path = Path(package) / target
    elif label.startswith(":"):
        relative_path = current_file.parent / label.removeprefix(":")
    else:
        relative_path = current_file.parent / label

    try:
        safe_checkout_path(checkout_path, relative_path)
    except ValueError:
        return None
    return relative_path


def get_bazel_dep_names_from_contents(contents: Iterable[str]) -> tuple[str, ...]:
    names: list[str] = []
    for content in contents:
        names.extend(get_bazel_dep_names(content))
    return dedupe_preserving_order(names)


def get_bazel_dep_names(text: str | None) -> tuple[str, ...]:
    if not text:
        return ()

    names: list[str] = []
    for match in BAZEL_DEP_PATTERN.finditer(text):
        name_match = NAME_PATTERN.search(match.group("body"))
        if name_match is not None:
            names.append(name_match.group("value").strip())
    return dedupe_preserving_order(names)


def get_git_override_repositories_by_module(
    contents: Iterable[str],
    *,
    active_repository_names: set[str],
    org_name: str,
) -> dict[str, str]:
    repositories_by_module: dict[str, str] = {}
    for content in contents:
        repositories_by_module.update(
            get_git_override_repositories_from_text(
                content,
                active_repository_names=active_repository_names,
                org_name=org_name,
            )
        )
    return repositories_by_module


def get_git_override_repositories_from_text(
    text: str | None,
    *,
    active_repository_names: set[str],
    org_name: str,
) -> dict[str, str]:
    if not text:
        return {}

    repositories_by_module: dict[str, str] = {}
    for match in GIT_OVERRIDE_PATTERN.finditer(text):
        body = match.group("body")
        module_name_match = MODULE_NAME_PATTERN.search(body)
        remote_match = REMOTE_PATTERN.search(body)
        if module_name_match is None or remote_match is None:
            continue
        repository_name = parse_github_remote_repository_name(
            remote_match.group("value"),
            org_name=org_name,
        )
        if repository_name is None or repository_name not in active_repository_names:
            continue
        module_name = module_name_match.group("value").strip()
        if module_name:
            repositories_by_module[module_name] = repository_name
    return repositories_by_module


def parse_github_remote_repository_name(
    remote: str,
    *,
    org_name: str,
) -> str | None:
    parsed = urlsplit(remote)
    if parsed.netloc != "github.com":
        return None

    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) != 2:
        return None

    owner, repository_name = path_parts
    if owner != org_name:
        return None

    return repository_name.removesuffix(".git") or None


def get_bazel_registry_repositories_by_module(
    *,
    active_repository_names: set[str],
    registry_repository: str,
) -> dict[str, str]:
    if not is_safe_repository_path(registry_repository):
        return {}

    repositories_by_module: dict[str, str] = {}
    for metadata_path in sorted(
        (default_cache_directory() / registry_repository).glob(
            "modules/*/metadata.json"
        )
    ):
        try:
            content = metadata_path.read_text(encoding="utf-8")
        except OSError:
            continue

        module_name = metadata_path.parent.name
        metadata_by_repo = parse_bazel_registry_metadata(
            content,
            active_repository_names=active_repository_names,
        )
        for repository_name in metadata_by_repo:
            repositories_by_module.setdefault(module_name, repository_name)
    return repositories_by_module
