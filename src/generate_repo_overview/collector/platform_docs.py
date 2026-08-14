from __future__ import annotations

import re
from dataclasses import replace
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from generate_repo_overview.module_name_matching import (
    MATCH_MARGIN,
    MATCH_THRESHOLD,
    alias_match_score,
    normalized_aliases,
)

from .git_checkout import list_repository_paths, read_repository_text
from .sphinx import parse_sphinx_directives

if TYPE_CHECKING:
    from pathlib import Path

    from generate_repo_overview.models import RepoEntry, SphinxItem

FEATURE_ROOT = "docs/features/"
MODULE_ROOT = "docs/modules/"


def enrich_repositories_from_platform_docs(
    repos: list[RepoEntry],
    *,
    checkout_path: Path,
    source_repo: str,
) -> list[RepoEntry]:
    tree_paths = list_repository_paths(checkout_path)
    if not tree_paths:
        raise RuntimeError(
            f"Could not inspect configured platform repository {source_repo}."
        )

    features, modules = discover_sphinx_items(
        checkout_path,
        tree_paths=tree_paths,
        source_repo=source_repo,
    )
    module_repos = [entry for entry in repos if entry.category.casefold() == "modules"]
    features_by_repo = associate_sphinx_items(features, module_repos)
    modules_by_repo = associate_sphinx_items(modules, module_repos)

    return [
        replace(
            entry,
            content=replace(
                entry.content,
                sphinx_features=_merge_sphinx_items(
                    entry.content.sphinx_features,
                    features_by_repo.get(entry.name, ()),
                ),
                sphinx_modules=_merge_sphinx_items(
                    entry.content.sphinx_modules,
                    modules_by_repo.get(entry.name, ()),
                ),
            ),
        )
        if entry.category.casefold() == "modules"
        else entry
        for entry in repos
    ]


def discover_sphinx_items(
    checkout_path: Path,
    *,
    tree_paths: set[str],
    source_repo: str,
) -> tuple[tuple[SphinxItem, ...], tuple[SphinxItem, ...]]:
    text_cache: dict[str, str | None] = {}

    def read(path: str) -> str | None:
        if path not in text_cache:
            text_cache[path] = read_repository_text(checkout_path, path)
        return text_cache[path]

    feature_architecture_paths = sorted(
        path
        for path in tree_paths
        if path.startswith(FEATURE_ROOT)
        and "/architecture/" in path
        and PurePosixPath(path).name in {"index.rst", "feature_architecture.rst"}
    )
    feature_items: list[SphinxItem] = []
    feature_base_paths: set[str] = set()
    bases_with_feature: set[str] = set()
    for path in feature_architecture_paths:
        base_path = path.split("/architecture/", maxsplit=1)[0]
        feature_base_paths.add(base_path)
        items = parse_sphinx_directives(
            read(path),
            "feat",
            path=base_path,
            source_repo=source_repo,
        )
        if items:
            bases_with_feature.add(base_path)
            feature_items.extend(items)

    for base_path in sorted(feature_base_paths - bases_with_feature):
        index_path = f"{base_path}/index.rst"
        if index_path not in tree_paths:
            continue
        text = read(index_path)
        items = parse_sphinx_directives(
            text,
            "feat",
            path=base_path,
            source_repo=source_repo,
        )
        if not items:
            items = parse_sphinx_directives(
                text,
                "document",
                path=base_path,
                source_repo=source_repo,
            )
        feature_items.extend(items)

    module_items: list[SphinxItem] = []
    module_doc_paths = sorted(
        path
        for path in tree_paths
        if re.fullmatch(r"docs/modules/[^/]+/docs/index\.rst", path)
    )
    for path in module_doc_paths:
        parts = PurePosixPath(path).parts
        base_path = "/".join(parts[:3])
        module_items.extend(
            parse_sphinx_directives(
                read(path),
                "mod",
                path=base_path,
                source_repo=source_repo,
            )
        )

    return (
        _dedupe_sphinx_items(feature_items),
        _dedupe_sphinx_items(module_items),
    )


def parse_sphinx_directive(
    text: str | None,
    directive: str,
    *,
    path: str,
    source_repo: str = "",
) -> SphinxItem | None:
    items = parse_sphinx_directives(
        text,
        directive,
        path=path,
        source_repo=source_repo,
    )
    return items[0] if items else None


def associate_sphinx_items(
    items: tuple[SphinxItem, ...],
    repos: list[RepoEntry],
) -> dict[str, tuple[SphinxItem, ...]]:
    associated: dict[str, list[SphinxItem]] = {}
    for item in items:
        ranked = sorted(
            ((_match_score(item, entry), entry.name) for entry in repos),
            reverse=True,
        )
        if not ranked or ranked[0][0] < MATCH_THRESHOLD:
            continue
        if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < MATCH_MARGIN:
            continue
        associated.setdefault(ranked[0][1], []).append(item)
    return {
        repo_name: tuple(sorted(repo_items, key=lambda item: item.path))
        for repo_name, repo_items in associated.items()
    }


def _match_score(item: SphinxItem, entry: RepoEntry) -> float:
    return alias_match_score(_item_aliases(item), _repo_aliases(entry))


def _item_aliases(item: SphinxItem) -> set[str]:
    path_parts = PurePosixPath(item.path).parts[2:]
    values = [item.title, item.identifier]
    if path_parts:
        values.append(path_parts[-1])
    return normalized_aliases(values)


def _repo_aliases(entry: RepoEntry) -> set[str]:
    values = [entry.name]
    if entry.content.bazel_module_name:
        values.append(entry.content.bazel_module_name)
    values.extend(
        (
            entry.content.sphinx_project_name or "",
            entry.content.sphinx_project_prefix or "",
        )
    )
    values.extend(
        path.rsplit("/", maxsplit=1)[-1] for path in entry.content.docs_feature_paths
    )
    for item in (
        *entry.content.repo_sphinx_features,
        *entry.content.repo_sphinx_modules,
    ):
        values.extend((item.title, item.identifier))
    return normalized_aliases(values)


def _dedupe_sphinx_items(items: list[SphinxItem]) -> tuple[SphinxItem, ...]:
    deduped: dict[tuple[str, str, str], SphinxItem] = {}
    for item in items:
        deduped[(item.source_repo, item.path, item.identifier or item.title)] = item
    return tuple(
        sorted(
            deduped.values(),
            key=lambda item: (item.source_repo, item.path, item.title),
        )
    )


def _merge_sphinx_items(
    existing: tuple[SphinxItem, ...],
    discovered: tuple[SphinxItem, ...],
) -> tuple[SphinxItem, ...]:
    return _dedupe_sphinx_items([*existing, *discovered])
