from __future__ import annotations

import html
from pathlib import Path
from typing import TYPE_CHECKING

from .metrics_report import parse_version_key

if TYPE_CHECKING:
    from .models import RepoEntry, WorkflowRefResolution

_TEMPLATES = Path(__file__).parent / "templates"

CSS = (_TEMPLATES / "styles.css").read_text(encoding="utf-8")

BAZEL_ICON = '<img src="bazel_logo.svg" alt="Bazel" class="icon-bazel">'

BAZEL_DETAIL_ICON = '<img src="../bazel_logo.svg" alt="Bazel" class="icon-bazel">'


GITHUB_ICON = (
    '<svg viewBox="0 0 16 16" fill="currentColor">'
    '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17'
    ".55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94"
    "-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87"
    " 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59"
    ".82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27"
    ".68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51"
    ".56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07"
    '-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"/>'
    "</svg>"
)

DOCS_ICON = "📑"
DOCS_AS_CODE_MODULE = "score_docs_as_code"


def docs_url(org_name: str, repo_name: str) -> str:
    """Compute docs site URL from repo URL.

    https://github.com/{org}/{repo} → https://{org}.github.io/{repo}
    """
    return f"https://{org_name}.github.io/{repo_name}"


def uses_docs_as_code(entry: RepoEntry) -> bool:
    return any(
        module_name == DOCS_AS_CODE_MODULE
        for module_name, _ in entry.content.bazel_deps
    )


_LANGUAGE_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "C++": "#f34b7d",
    "C": "#555555",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Java": "#b07219",
    "Kotlin": "#A97BFF",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Starlark": "#76d275",
    "Shell": "#89e051",
    "CMake": "#DA3434",
    "Makefile": "#427819",
}


def e(text: str) -> str:
    return html.escape(text, quote=True)


def language_badge(lang: str | None) -> str:
    if not lang:
        return '<span class="text-muted">—</span>'
    color = _LANGUAGE_COLORS.get(lang, "#888888")
    return f'<span class="lang-badge" style="--lang-color:{color}">{e(lang)}</span>'


def repo_name_cell(
    entry: RepoEntry,
    org_name: str,
    *,
    bazel_icon: bool = True,
    include_description: bool = True,
) -> str:
    detail_url = f"{e(entry.name)}/index.html"
    github_url = f"https://github.com/{org_name}/{entry.name}"
    docs_link_str = docs_url(org_name, entry.name)
    cell = f'<a href="{detail_url}">{e(entry.name)}</a>'
    if bazel_icon and entry.content.is_bazel_repo:
        cell += f" {BAZEL_ICON}"
    cell += (
        f' <a href="{e(github_url)}" class="gh-link" title="Open on GitHub ↗"'
        f' target="_blank" rel="noopener">{GITHUB_ICON}</a>'
    )
    if uses_docs_as_code(entry):
        cell += (
            f' <a href="{e(docs_link_str)}" class="docs-link" title="Documentation ↗"'
            f' aria-label="Documentation ↗"'
            f' target="_blank" rel="noopener">{DOCS_ICON}</a>'
        )
    if include_description and entry.description:
        cell += f' <span class="repo-desc">{e(entry.description)}</span>'
    return cell


def version_badge(
    version: str | None,
    max_bazel: tuple[int, ...] | None,
    *,
    latest_dep_version: str | None,
    is_bazel: bool,
) -> str:
    """Render a colored version badge span.

    Bazel versions are green when equal to *max_bazel*, red otherwise.
    Dep versions compare against *latest_dep_version*: green if equal,
    yellow if same major.minor, red if older, muted if unknown.
    """
    if version is None or not version.strip():
        return '<span class="badge muted">—</span>'

    cleaned = version.strip()
    parsed = parse_version_key(cleaned)

    if is_bazel:
        if parsed is not None and max_bazel is not None and parsed == max_bazel:
            return f'<span class="badge green">{e(cleaned)}</span>'
        return f'<span class="badge red">{e(cleaned)}</span>'

    if latest_dep_version is None:
        return f'<span class="badge muted">{e(cleaned)}</span>'
    latest_cleaned = latest_dep_version.strip()
    if cleaned == latest_cleaned:
        return f'<span class="badge green">{e(cleaned)}</span>'
    if parsed is not None:
        latest_parsed = parse_version_key(latest_cleaned)
        if (
            latest_parsed is not None
            and len(parsed) >= 2
            and len(latest_parsed) >= 2
            and parsed[:2] == latest_parsed[:2]
        ):
            return f'<span class="badge yellow">{e(cleaned)}</span>'
    return f'<span class="badge red">{e(cleaned)}</span>'


def workflow_ref_badges(
    entry: RepoEntry,
    label: str,
    resolutions: tuple[WorkflowRefResolution, ...] = (),
) -> str:
    """Link each distinct configured workflow pin to its source on GitHub."""
    from urllib.parse import quote

    badges: list[str] = []
    for reference in sorted(
        {ref for name, ref in entry.content.workflow_refs if name == label}
    ):
        workflow, _, pin = reference.rpartition("@")
        segments = workflow.split("/", 2)
        if len(segments) != 3 or not pin:
            continue
        owner, repo, path = segments
        url = f"https://github.com/{quote(owner, safe='')}/{quote(repo, safe='')}/blob/{quote(pin, safe='')}/{quote(path, safe='/')}"
        short_pin = (
            pin[:12]
            if len(pin) == 40 and all(c in "0123456789abcdefABCDEF" for c in pin)
            else pin
        )
        resolution = next((r for r in resolutions if r.reference == reference), None)
        display = (
            resolution.version_tag
            if resolution and resolution.version_tag
            else short_pin
        )
        title = reference
        if resolution and resolution.resolved_sha:
            title += f"\nResolved commit: {resolution.resolved_sha}"
        badge = f'<a class="badge muted mono" href="{e(url)}" title="{e(title)}">{e(display)}</a>'
        if resolution and resolution.latest_release:
            release = resolution.latest_release
            difference = render_ref_difference(
                resolution.ahead_by,
                resolution.behind_by,
                left_ref=f"latest release {release}",
                right_ref=f"workflow pin {pin}",
            )
            badge += f' <span class="text-muted">vs {e(release)}</span> {difference}'
        badges.append(f'<span class="workflow-pin">{badge}</span>')
    return " ".join(badges) or '<span class="text-muted">—</span>'


def render_ref_difference(
    ahead_by: int | None,
    behind_by: int | None,
    *,
    left_ref: str,
    right_ref: str,
) -> str:
    """Show commits unique to either ref with a plain-language tooltip."""
    if ahead_by is None or behind_by is None:
        title = f"Could not compare {left_ref} with {right_ref}."
        return f'<span class="git-ref-diff unavailable" title="{e(title)}">?</span>'
    if ahead_by == 0 and behind_by == 0:
        title = f"{left_ref} and {right_ref} point to the same commit."
        return f'<span class="git-ref-diff equal" title="{e(title)}">=</span>'
    arrows: list[str] = []
    if ahead_by:
        commit_word = "commit" if ahead_by == 1 else "commits"
        missing_clause = "which is not" if ahead_by == 1 else "which are not"
        title = (
            f"{right_ref} is {ahead_by} {commit_word} ahead of {left_ref}. "
            f"It contains {ahead_by} {commit_word} {missing_clause} in {left_ref}."
        )
        size_class = _ref_difference_size_class(ahead_by)
        arrows.append(
            f'<span class="git-ref-count {size_class}" title="{e(title)}">'
            f"↑{ahead_by}</span>"
        )
    if behind_by:
        commit_word = "commit" if behind_by == 1 else "commits"
        missing_clause = "which is not" if behind_by == 1 else "which are not"
        title = (
            f"{left_ref} is {behind_by} {commit_word} ahead of {right_ref}. "
            f"It contains {behind_by} {commit_word} {missing_clause} in {right_ref}."
        )
        size_class = _ref_difference_size_class(behind_by)
        arrows.append(
            f'<span class="git-ref-count {size_class}" title="{e(title)}">'
            f"↓{behind_by}</span>"
        )
    return f'<span class="git-ref-diff">{" ".join(arrows)}</span>'


def _ref_difference_size_class(commit_count: int) -> str:
    """Color a difference by size without assigning meaning to its direction."""
    if commit_count >= 20:
        return "large"
    if commit_count >= 5:
        return "medium"
    return "small"
