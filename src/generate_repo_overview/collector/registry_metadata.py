from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

from .git_checkout import sync_repository_checkout
from .signal_detection import dedupe_preserving_order


class RegistrySignalsPayload(TypedDict):
    maintainers_in_bazel_registry: tuple[str, ...]
    latest_bazel_registry_version: str | None


BAZEL_REGISTRY_LOCAL_CHECKOUT = Path("profile/cache/bazel_registry_checkout")


def fetch_bazel_registry_metadata_by_repo(
    *,
    bazel_registry_repository: object | None,
    active_repository_names: set[str],
    github_token: str | None,
) -> dict[str, RegistrySignalsPayload]:
    if bazel_registry_repository is None:
        return {}

    default_branch = cast("str | None", getattr(bazel_registry_repository, "default_branch", None))
    clone_url = cast("str | None", getattr(bazel_registry_repository, "clone_url", None))
    if default_branch is None or clone_url is None:
        return {}

    checkout_path = sync_repository_checkout(
        clone_url=clone_url,
        default_branch=default_branch,
        github_token=github_token,
        checkout_path=BAZEL_REGISTRY_LOCAL_CHECKOUT,
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

    repository_entries = cast("list[object]", raw_repositories)
    for raw_repository in repository_entries:
        repository_name = parse_github_repository_name(raw_repository)
        if repository_name is None or repository_name not in active_repository_names:
            continue
        metadata_by_repo_name[repository_name] = {
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


def parse_github_repository_name(value: object) -> str | None:
    if not isinstance(value, str) or not value.startswith("github:"):
        return None

    owner_and_repo = value.removeprefix("github:")
    if "/" not in owner_and_repo:
        return None

    _, repository_name = owner_and_repo.split("/", maxsplit=1)
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
