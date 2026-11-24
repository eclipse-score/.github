"""Resolve shared workflow pins once per collection, outside consumer content caches."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Protocol, cast

import yaml

from generate_repo_overview.console import print_status
from generate_repo_overview.metrics_report import parse_version_key
from generate_repo_overview.models import WorkflowRefResolution

from .reference_integration import GitRefComparison, compare_git_refs
from .signal_detection import fetch_text_file

if TYPE_CHECKING:
    from collections.abc import Iterable

    from generate_repo_overview.models import RepoEntry

    from . import RepositoryResolverLike


_VERSION_TAG = re.compile(
    r"v?\d+(?:\.\d+){0,2}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
)
_STABLE_COMPONENT_VERSION = re.compile(r"v\d+\.\d+\.\d+")


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
    workflow_components: dict[str, str]
    component_releases: dict[str, str | None]


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
    comparisons: dict[tuple[str, str, str], GitRefComparison | None] = {}
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
        commit_key = (repository_name, pin)
        if commit_key not in commits:
            commits[commit_key] = _resolve_commit(context, pin)
        sha = commits[commit_key]
        component = context.workflow_components.get(path)
        latest_release = None
        if component is None:
            component = PurePosixPath(path).stem
            latest_release = context.latest_release
        latest_release = context.component_releases.get(component, latest_release)
        version_tag = _matching_version_tag(context, component, sha, latest_release)
        comparison = None
        if latest_release and sha:
            comparison_key = (repository_name, latest_release, sha)
            if comparison_key not in comparisons:
                comparisons[comparison_key] = _compare_pin(context, latest_release, sha)
            comparison = comparisons[comparison_key]
        resolutions.append(
            WorkflowRefResolution(
                reference=reference,
                resolved_sha=sha,
                version_tag=version_tag,
                latest_release=latest_release,
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
    labeler = fetch_text_file(repository, ".github/labeler.yml", ref=None)
    return _ReleaseContext(
        repository,
        tags,
        latest_release,
        _workflow_components(labeler),
        _latest_component_releases(tags),
    )


def _single_labeler_rule(rules: object, key: str) -> object:
    if isinstance(rules, list) and len(rules) == 1:
        rule = cast("list[object]", rules)[0]
        if isinstance(rule, dict) and rule.keys() == {key}:
            return cast("dict[str, object]", rule)[key]
    return None


def _workflow_components(labeler: str | None) -> dict[str, str]:
    """Read explicit workflow paths from the rules used by monorepo releases."""
    if not labeler:
        return {}
    try:
        labels: object = yaml.safe_load(labeler)
    except yaml.YAMLError:
        return {}
    if not isinstance(labels, dict):
        return {}

    components_by_path: dict[str, set[str]] = {}
    component_names: set[str] = set()
    for label, rules in cast("dict[object, object]", labels).items():
        if not isinstance(label, str):
            return {}
        component = re.sub(r"\.[^.]{1,3}\Z", "", label)
        changed_files = _single_labeler_rule(rules, "changed-files")
        paths = _single_labeler_rule(changed_files, "any-glob-to-any-file")
        if isinstance(paths, str):
            paths = [paths]
        if (
            not component.strip()
            or component in component_names
            or not isinstance(paths, list)
            or not paths
        ):
            return {}
        component_names.add(component)
        for path in cast("list[object]", paths):
            if not isinstance(path, str) or not path.strip():
                return {}
            components_by_path.setdefault(path, set()).add(component)

    return {
        path: next(iter(components))
        for path, components in components_by_path.items()
        if len(components) == 1
    }


def _latest_component_releases(tags: Iterable[str]) -> dict[str, str | None]:
    """Include known series with no stable release so they have no global baseline."""
    releases: dict[str, str | None] = {}
    versions: dict[str, tuple[int, ...]] = {}
    for tag in tags:
        component, _, version = tag.rpartition("/")
        if not component or not _VERSION_TAG.fullmatch(version):
            continue
        releases.setdefault(component, None)
        if _STABLE_COMPONENT_VERSION.fullmatch(version):
            key = parse_version_key(version) or ()
            if key > versions.get(component, ()):
                versions[component] = key
                releases[component] = tag
    return releases


def _compare_pin(
    context: _ReleaseContext, latest_release: str, sha: str
) -> GitRefComparison | None:
    if context.tags.get(latest_release) == sha:
        return GitRefComparison(0, 0)
    return compare_git_refs(context.repository, left_ref=latest_release, right_ref=sha)


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
    context: _ReleaseContext,
    component: str,
    sha: str | None,
    latest_release: str | None,
) -> str | None:
    if sha is None:
        return None
    # A shared commit can carry tags from several independent release series.
    candidates = [
        tag
        for tag, tag_sha in context.tags.items()
        if tag_sha == sha
        and tag.rpartition("/")[0] in ("", component)
        and _VERSION_TAG.fullmatch(tag.rsplit("/", 1)[-1])
    ]
    return max(
        candidates,
        key=lambda tag: (
            "/" in tag,
            tag in (latest_release, context.latest_release),
            parse_version_key(tag.rsplit("/", 1)[-1]) or (),
            tag,
        ),
        default=None,
    )
