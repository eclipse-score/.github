import re

from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    DependencyDeclaration,
    DependencyOverride,
    DependencyPinKind,
    DependencyResolution,
    RepoEntry,
    RepoSnapshot,
    VolatileMetricsSnapshot,
)

PIN = "0123456789abcdef0123456789abcdef01234567"
BASELIBS = "eclipse-score/baselibs"


def _repo(
    name: str,
    *,
    default_branch: str | None = None,
    content: DeepContentSignals | None = None,
    volatile: VolatileMetricsSnapshot | None = None,
) -> RepoEntry:
    return RepoEntry(
        name,
        "",
        "Platform",
        "General",
        owner="eclipse-score",
        default_branch=default_branch,
        content=content or DeepContentSignals(),
        volatile=volatile or VolatileMetricsSnapshot(),
    )


def _snapshot() -> RepoSnapshot:
    baselibs = _repo(
        "baselibs",
        default_branch="main",
        content=DeepContentSignals(bazel_module_name="score_baselibs"),
        volatile=VolatileMetricsSnapshot(latest_release_version="v1.1.0"),
    )
    current = _repo(
        "current",
        content=DeepContentSignals(
            bazel_deps=(DependencyDeclaration("score_baselibs", "1.1.0"),)
        ),
        volatile=VolatileMetricsSnapshot(
            latest_release_version="v2.0.0",
            release_bazel_deps=(DependencyDeclaration("score_baselibs", "1.0.0"),),
        ),
    )
    pinned = _repo(
        "pinned",
        content=DeepContentSignals(
            bazel_deps=(
                DependencyDeclaration(
                    "score_baselibs",
                    "0.0.0",
                    DependencyOverride.GIT,
                    remote="https://github.com/eclipse-score/baselibs.git",
                    revision=PIN,
                    pin_kind=DependencyPinKind.COMMIT,
                ),
                DependencyDeclaration("score_unknown", "9.9.9"),
                DependencyDeclaration("rules_python", "1.0.0"),
                DependencyDeclaration("external", "2.0.0"),
            )
        ),
    )
    return RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-11-20T00:00:00+00:00",
        repos=(baselibs, current, pinned),
        module_repositories={
            "score_baselibs": BASELIBS,
            "score_unknown": BASELIBS,
            "external": "other-org/external",
        },
        dependency_resolutions=(
            DependencyResolution(BASELIBS, "1.1.0", "b" * 40, "v1.1.0", 0, 0, 1),
            DependencyResolution(BASELIBS, "1.0.0", "a" * 40, "v1.1.0", 2, 0, 3),
            DependencyResolution(
                BASELIBS, PIN, PIN, "v1.1.0", None, 1, 3, DependencyPinKind.COMMIT
            ),
            DependencyResolution(BASELIBS, "9.9.9", latest_release="v1.1.0"),
        ),
    )


def _row(page: str, label: str) -> str:
    match = re.search(rf"<tr><td>(?:(?!</tr>).)*{re.escape(label)}.*?</tr>", page, re.S)
    assert match, f"no row for {label}"
    return match.group(0)


def test_detail_page_shows_release_and_default_branch_freshness_separately() -> None:
    pages = render_all_pages(_snapshot())

    current = _row(pages["current/index.html"], "score_baselibs")
    head, release = re.findall(r"<td>(.*?)</td>", current, re.S)[1:3]
    assert "latest release" in head
    assert "v1.1.0" in head
    assert "1 behind main" in head
    assert "1.0.0" in release
    assert "v1.1.0 available" in release
    assert "3 behind main" in release
    assert 'href="../baselibs/index.html"' in current
    assert 'href="https://github.com/eclipse-score/baselibs"' in current

    pinned = pages["pinned/index.html"]
    git_pin = _row(pinned, "score_baselibs")
    assert "0123456" in git_pin
    assert "0.0.0" not in git_pin
    assert "diverged from main" in git_pin
    assert "v1.1.0 · comparison unavailable" in git_pin
    assert "unresolved" in _row(pinned, "score_unknown")
    assert "source unknown" in _row(pinned, "rules_python")
    external = _row(pinned, "other-org/external")
    assert "outside overview" in external
    assert 'href="https://github.com/other-org/external"' in external


def test_detail_page_lists_consumers_with_the_versions_they_use() -> None:
    page = render_all_pages(_snapshot())["baselibs/index.html"]
    used_by = page[page.index('id="used-by"') :]

    current = _row(used_by, "eclipse-score/current")
    assert "1.1.0" in current
    assert "1.0.0" in current
    assert "in v2.0.0" in current
    pinned = _row(used_by, "eclipse-score/pinned")
    assert "score_baselibs" in pinned
    assert "9.9.9" in pinned
    assert "0123456" in pinned
    assert "no release" in pinned
    assert "Only repositories in this overview are searched." in used_by
