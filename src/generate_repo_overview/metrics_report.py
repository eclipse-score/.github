"""Shared helpers for grouping repositories and comparing versions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import RepoEntry, TrackedDep


def group_repos_by_category(
    repos: list[RepoEntry],
) -> list[tuple[str, list[RepoEntry]]]:
    grouped: dict[str, list[RepoEntry]] = {}
    for repo in repos:
        grouped.setdefault(repo.category, []).append(repo)

    return [
        (category, sorted(category_repos, key=lambda repo: repo.name.casefold()))
        for category, category_repos in sorted(
            grouped.items(), key=lambda item: item[0].casefold()
        )
    ]


def parse_version_key(value: str | None) -> tuple[int, ...] | None:
    if value is None:
        return None
    numeric_parts = re.findall(r"\d+", value)
    if not numeric_parts:
        return None
    return tuple(int(part) for part in numeric_parts[:3])


def get_max_bazel_version(repos: list[RepoEntry]) -> tuple[int, ...] | None:
    keys = [
        key
        for repo in repos
        if (key := parse_version_key(repo.content.bazel_version)) is not None
    ]
    return max(keys) if keys else None


def tracked_dep_label(dep: TrackedDep) -> str:
    return dep.repo.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").title()


def has_latest_release(entry: RepoEntry) -> bool:
    return (
        entry.volatile.latest_release_version is not None
        or entry.volatile.latest_release_date is not None
    )
