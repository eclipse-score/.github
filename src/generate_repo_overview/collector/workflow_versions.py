"""Resolve shared workflow pins once per collection, outside consumer content caches."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Protocol, cast

from generate_repo_overview.console import print_status
from generate_repo_overview.metrics_report import parse_version_key
from generate_repo_overview.models import WorkflowRefResolution

from .reference_integration import GitRefComparison, compare_git_refs

if TYPE_CHECKING:
    from collections.abc import Iterable

    from generate_repo_overview.models import RepoEntry

    from . import RepositoryResolverLike


class _CommitLike(Protocol):
    sha: str

    def complete(self) -> object: ...


class _TagLike(Protocol):
    name: str
    commit: _CommitLike


class _ReleaseLike(Protocol):
    tag_name: str


class _RepositoryLike(Protocol):
    def get_tags(self) -> Iterable[_TagLike]: ...

    def get_latest_release(self) -> _ReleaseLike: ...

    def get_commit(self, sha: str) -> _CommitLike: ...


@dataclass(frozen=True)
class _ReleaseContext:
    repository: _RepositoryLike
    tags: dict[str, str]
    latest_release: str | None


def fetch_workflow_ref_resolutions(
    repos: Iterable[RepoEntry],
    *,
    github: RepositoryResolverLike,
    status_prefix: str = "repo-overview",
) -> tuple[WorkflowRefResolution, ...]:
    """Refresh source-repository releases even when consumer content is unchanged.

    A pin can appear in many consumers or call multiple workflow paths. Cache
    source metadata and comparisons for this collection only, so moved branch
    pins, newly published tags, and releases cannot leave stale display values.
    """
    references = sorted(
        {ref for repo in repos for _, ref in repo.content.workflow_refs}
    )
    contexts: dict[str, _ReleaseContext | None] = {}
    commits: dict[tuple[str, str], str | None] = {}
    comparisons: dict[tuple[str, str], GitRefComparison | None] = {}
    resolutions: list[WorkflowRefResolution] = []
    for reference in references:
        source, separator, pin = reference.rpartition("@")
        segments = source.split("/", 2)
        if not separator or not pin or len(segments) != 3:
            continue
        owner, name, path = segments
        repository_name = f"{owner}/{name}"
        if repository_name not in contexts:
            contexts[repository_name] = _fetch_release_context(
                github, repository_name, status_prefix=status_prefix
            )
        context = contexts[repository_name]
        if context is None:
            continue
        key = (repository_name, pin)
        if key not in commits:
            commits[key] = _resolve_commit(context, pin)
        sha = commits[key]
        version_tag = _matching_version_tag(context, path, sha)
        comparison = None
        if context.latest_release and sha:
            if key not in comparisons:
                comparisons[key] = compare_git_refs(
                    context.repository,
                    left_ref=context.latest_release,
                    right_ref=sha,
                )
            comparison = comparisons[key]
        resolutions.append(
            WorkflowRefResolution(
                reference=reference,
                resolved_sha=sha,
                version_tag=version_tag,
                latest_release=context.latest_release,
                ahead_by=comparison.right_ahead_by if comparison else None,
                behind_by=comparison.left_ahead_by if comparison else None,
            )
        )
    return tuple(resolutions)


def _fetch_release_context(
    github: RepositoryResolverLike,
    repository_name: str,
    *,
    status_prefix: str,
) -> _ReleaseContext | None:
    try:
        repository = cast("_RepositoryLike", github.get_repo(repository_name))
    except Exception as exc:
        print_status(
            f"Could not resolve workflow repository {repository_name}: {exc}",
            prefix=status_prefix,
        )
        return None
    # Tags and releases are independent: a repository may have tags without
    # releases, or expose a release while listing its tags fails temporarily.
    try:
        tags = {tag.name: tag.commit.sha for tag in repository.get_tags()}
    except Exception:
        tags = {}
    try:
        latest_release = repository.get_latest_release().tag_name
    except Exception:
        latest_release = None
    return _ReleaseContext(repository, tags, latest_release)


def _resolve_commit(context: _ReleaseContext, pin: str) -> str | None:
    if re.fullmatch(r"[0-9a-fA-F]{40}", pin):
        return pin.lower()
    if pin in context.tags:
        return context.tags[pin]
    try:
        commit = context.repository.get_commit(pin)
        # Collection uses lazy PyGithub objects. Complete the request before
        # reading sha, which can otherwise just echo an unresolved input ref.
        commit.complete()
        return commit.sha
    except Exception:
        return None


def _matching_version_tag(
    context: _ReleaseContext, path: str, sha: str | None
) -> str | None:
    if sha is None:
        return None
    workflow_name = PurePosixPath(path).stem
    # Workflow-specific tags belong to that workflow only. Global version tags
    # apply to the repository; ignore tags for a different workflow at this SHA.
    candidates = [
        tag
        for tag, tag_sha in context.tags.items()
        if tag_sha == sha
        and ("/" not in tag or tag.startswith(f"{workflow_name}/"))
        and re.fullmatch(
            r"v?\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?", tag.rsplit("/", 1)[-1]
        )
    ]
    return max(
        candidates,
        key=lambda tag: (
            tag.startswith(f"{workflow_name}/"),
            tag == context.latest_release,
            parse_version_key(tag.rsplit("/", 1)[-1]) or (),
            tag,
        ),
        default=None,
    )
