from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, TypedDict, cast
from urllib.parse import unquote, urlsplit

from repo_cache import default_cache_directory

from generate_repo_overview.models import DependencyPinKind, parse_github_repository
from generate_repo_overview.org_config import is_safe_repository_path

from .git_checkout import sync_repository_checkout
from .signal_detection import dedupe_preserving_order

if TYPE_CHECKING:
    from pathlib import Path

_VERSION = re.compile(
    r"[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*"
    r"(?:-[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)?"
    r"(?:\+[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)?"
)


@dataclass(frozen=True, slots=True)
class RegistryCheckout:
    repository: str
    branch: str

    def matches_url(self, url: str) -> bool:
        """Match GitHub's raw URLs for the registry root on the cached branch."""
        try:
            parsed = urlsplit(url)
        except ValueError:
            return False
        if parsed.scheme != "https" or parsed.query or parsed.fragment:
            return False
        parts = parsed.path.strip("/").split("/", 2)
        if len(parts) != 3:
            return False
        owner, repo, ref = (unquote(part) for part in parts)
        if f"{owner}/{repo}".casefold() != self.repository.casefold():
            return False
        if parsed.netloc.casefold() == "github.com" and ref.startswith("raw/"):
            ref = ref.removeprefix("raw/")
        elif parsed.netloc.casefold() != "raw.githubusercontent.com":
            return False
        return ref in (f"refs/heads/{self.branch}", self.branch)


@dataclass(frozen=True, slots=True)
class RegistryGitSource:
    repository: str
    kind: DependencyPinKind
    revision: str
    package_modified: bool = False


@dataclass(frozen=True, slots=True)
class RegistryModule:
    directory: Path
    repositories: tuple[str, ...]
    latest_version: str | None
    versions: frozenset[str]

    def has_version(self, version: str) -> bool:
        return (
            _VERSION.fullmatch(version) is not None
            and version.partition("+")[0] in self.versions
        )

    def update_available(self, version: str) -> bool | None:
        if self.latest_version is None or not self.has_version(version):
            return None
        pin = _bazel_version_key(version)
        latest = _bazel_version_key(self.latest_version)
        # A pin newer than the last non-yanked release may itself be yanked.
        return pin < latest if pin <= latest else None

    def git_source(self, version: str) -> RegistryGitSource | None:
        if not _VERSION.fullmatch(version):
            return None
        normalized_version = version.partition("+")[0]
        source = _read_object(self.directory / normalized_version / "source.json")
        package_modified = bool(source.get("patches") or source.get("overlay"))
        if source.get("type", "archive") == "archive":
            url = source.get("url")
            git_source = _github_archive_source(url) if isinstance(url, str) else None
            return (
                replace(git_source, package_modified=True)
                if git_source is not None and package_modified
                else git_source
            )
        if source.get("type") != "git_repository":
            return None
        remote = source.get("remote")
        repository = (
            parse_github_repository(remote) if isinstance(remote, str) else None
        )
        if repository is None:
            return None
        for kind in (
            DependencyPinKind.COMMIT,
            DependencyPinKind.TAG,
            DependencyPinKind.BRANCH,
        ):
            revision = source.get(kind.value)
            if isinstance(revision, str) and revision:
                return RegistryGitSource(repository, kind, revision, package_modified)
        return None


class RegistrySignalsPayload(TypedDict):
    maintainers_in_bazel_registry: tuple[str, ...]
    latest_bazel_registry_version: str | None


def fetch_bazel_registry_metadata_by_repo(
    *,
    bazel_registry_repository: object | None,
    active_repository_names: set[str],
    org_name: str = "",
) -> dict[str, RegistrySignalsPayload]:
    if bazel_registry_repository is None:
        return {}

    default_branch = cast(
        "str | None", getattr(bazel_registry_repository, "default_branch", None)
    )
    repository = cast(
        "str | None", getattr(bazel_registry_repository, "full_name", None)
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

    metadata_paths = sorted(checkout_path.glob("modules/*/metadata.json"))

    metadata_by_repo_name: dict[str, RegistrySignalsPayload] = {}
    for metadata_path in metadata_paths:
        try:
            content = metadata_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for repository_name, metadata in parse_bazel_registry_metadata(
            content,
            active_repository_names=active_repository_names,
            org_name=org_name,
        ).items():
            metadata_by_repo_name[repository_name] = merge_bazel_registry_metadata(
                metadata_by_repo_name.get(repository_name),
                metadata,
            )
    return metadata_by_repo_name


def parse_bazel_registry_metadata(
    text: str | None,
    *,
    active_repository_names: set[str],
    org_name: str = "",
) -> dict[str, RegistrySignalsPayload]:
    if not text:
        return {}
    try:
        raw_metadata_object: object = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw_metadata_object, dict):
        return {}
    raw_metadata = cast("dict[str, object]", raw_metadata_object)

    maintainers = parse_bazel_registry_maintainers(raw_metadata.get("maintainers"))
    latest_version = parse_latest_bazel_registry_version(raw_metadata.get("versions"))

    metadata_by_repo_name: dict[str, RegistrySignalsPayload] = {}
    raw_repositories = raw_metadata.get("repository")
    if not isinstance(raw_repositories, list):
        return metadata_by_repo_name

    active_names_by_identity = {
        name.casefold(): name for name in active_repository_names
    }
    repository_entries = cast("list[object]", raw_repositories)
    for raw_repository in repository_entries:
        repository_name = parse_github_repository_name(
            raw_repository, org_name=org_name
        )
        if repository_name is None:
            continue
        active_name = active_names_by_identity.get(repository_name.casefold())
        if active_name is None:
            continue
        metadata_by_repo_name[active_name] = {
            "maintainers_in_bazel_registry": maintainers,
            "latest_bazel_registry_version": latest_version,
        }

    return metadata_by_repo_name


def parse_bazel_registry_maintainers(raw_maintainers: object) -> tuple[str, ...]:
    if not isinstance(raw_maintainers, list):
        return ()

    maintainers: list[str] = []
    maintainer_entries = cast("list[object]", raw_maintainers)
    for raw_maintainer in maintainer_entries:
        if not isinstance(raw_maintainer, dict):
            continue
        maintainer = cast("dict[str, object]", raw_maintainer)

        name = maintainer.get("name")
        github_handle = maintainer.get("github")
        email = maintainer.get("email")

        display_parts: list[str] = []
        if isinstance(name, str) and name.strip():
            display_parts.append(name.strip())
        if isinstance(github_handle, str) and github_handle.strip():
            display_parts.append(f"(@{github_handle.strip()})")
        if not display_parts and isinstance(email, str) and email.strip():
            display_parts.append(email.strip())
        if display_parts:
            maintainers.append(" ".join(display_parts))

    return dedupe_preserving_order(maintainers)


def parse_latest_bazel_registry_version(raw_versions: object) -> str | None:
    if not isinstance(raw_versions, list):
        return None
    version_entries = cast("list[object]", raw_versions)
    for raw_version in version_entries:
        if isinstance(raw_version, str) and raw_version.strip():
            return raw_version.strip()
    return None


def parse_github_repository_name(value: object, *, org_name: str = "") -> str | None:
    if not isinstance(value, str) or not value.startswith("github:"):
        return None

    owner_and_repo = value.removeprefix("github:")
    if "/" not in owner_and_repo:
        return None

    owner, repository_name = owner_and_repo.split("/", maxsplit=1)
    if org_name and owner.casefold() != org_name.casefold():
        return None
    repository_name = repository_name.strip()
    return repository_name or None


def merge_bazel_registry_metadata(
    existing: RegistrySignalsPayload | None,
    incoming: RegistrySignalsPayload,
) -> RegistrySignalsPayload:
    if existing is None:
        return incoming

    return {
        "maintainers_in_bazel_registry": dedupe_preserving_order(
            list(existing["maintainers_in_bazel_registry"])
            + list(incoming["maintainers_in_bazel_registry"])
        ),
        "latest_bazel_registry_version": existing["latest_bazel_registry_version"]
        or incoming["latest_bazel_registry_version"],
    }


def get_bazel_registry_repositories_by_module(
    *,
    active_repository_names: set[str],
    registry_repository: str,
    org_name: str = "",
) -> dict[str, str]:
    active_by_identity = {name.casefold(): name for name in active_repository_names}
    repositories: dict[str, str] = {}
    for module, metadata in get_bazel_registry_modules(registry_repository).items():
        for source in metadata.repositories:
            owner, name = source.split("/")
            if org_name and owner.casefold() != org_name.casefold():
                continue
            if active_name := active_by_identity.get(name.casefold()):
                repositories.setdefault(module, active_name)
    return repositories


def get_bazel_registry_modules(
    registry_repository: str, *, cache_directory: Path | None = None
) -> dict[str, RegistryModule]:
    """Read the source identities and latest non-yanked version of each module."""
    if not is_safe_repository_path(registry_repository):
        return {}

    modules: dict[str, RegistryModule] = {}
    for metadata_path in sorted(
        ((cache_directory or default_cache_directory()) / registry_repository).glob(
            "modules/*/metadata.json"
        )
    ):
        metadata = _read_object(metadata_path)
        entries = metadata.get("repository")
        sources = tuple(
            repository
            for entry in (
                cast("list[object]", entries) if isinstance(entries, list) else ()
            )
            if isinstance(entry, str)
            and entry.startswith("github:")
            and (
                repository := parse_github_repository(
                    "https://github.com/" + entry.removeprefix("github:")
                )
            )
            is not None
        )
        raw_versions = metadata.get("versions")
        versions = [
            version
            for version in (
                cast("list[object]", raw_versions)
                if isinstance(raw_versions, list)
                else ()
            )
            if isinstance(version, str) and _VERSION.fullmatch(version)
        ]
        yanked = metadata.get("yanked_versions")
        latest = max(
            (
                version
                for version in versions
                if not isinstance(yanked, dict) or version not in yanked
            ),
            key=_bazel_version_key,
            default=None,
        )
        modules[metadata_path.parent.name] = RegistryModule(
            metadata_path.parent,
            sources,
            latest,
            frozenset(version.partition("+")[0] for version in versions),
        )
    return modules


def _bazel_version_key(
    version: str,
) -> tuple[tuple[tuple[bool, int, str], ...], bool, tuple[tuple[bool, int, str], ...]]:
    # Bazel uses SemVer precedence with any number of alphanumeric release
    # identifiers. Build metadata does not affect precedence.
    release, _, prerelease = version.partition("+")[0].partition("-")

    def identifiers(part: str) -> tuple[tuple[bool, int, str], ...]:
        return (
            tuple(
                (not item.isdigit(), int(item) if item.isdigit() else 0, item)
                for item in part.split(".")
            )
            if part
            else ()
        )

    return identifiers(release), not prerelease, identifiers(prerelease)


def _read_object(path: Path) -> dict[str, object]:
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return cast("dict[str, object]", data) if isinstance(data, dict) else {}


def _github_archive_source(url: str) -> RegistryGitSource | None:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    parts = parsed.path.lstrip("/").split("/", 2)
    if parsed.scheme != "https" or len(parts) != 3:
        return None
    owner, name, archive = parts
    repository = parse_github_repository(f"https://github.com/{owner}/{name}")
    if repository is None:
        return None
    archive_ref = _archive_ref(parsed.hostname, archive)
    if archive_ref is None:
        return None
    revision = unquote(archive_ref)
    for prefix, kind in (
        ("refs/tags/", DependencyPinKind.TAG),
        ("refs/heads/", DependencyPinKind.BRANCH),
    ):
        if revision.startswith(prefix) and revision != prefix:
            return RegistryGitSource(repository, kind, revision.removeprefix(prefix))
    if re.fullmatch(r"[0-9a-fA-F]{7,40}", revision):
        return RegistryGitSource(repository, DependencyPinKind.COMMIT, revision)
    return None


def _archive_ref(host: str | None, path: str) -> str | None:
    if host == "github.com" and path.startswith("archive/"):
        for extension in (".tar.gz", ".zip"):
            if path.endswith(extension):
                return path.removeprefix("archive/").removesuffix(extension)
    if host == "codeload.github.com":
        archive_format, _, ref = path.partition("/")
        if archive_format in ("tar.gz", "zip"):
            return ref
    return None
