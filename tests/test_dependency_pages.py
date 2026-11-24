import re
from dataclasses import replace

from generate_repo_overview.collector.bazel_modules import parse_dependencies
from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.metrics_report import render_versions_section
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    DependencyDeclaration,
    DependencyOverride,
    DependencyPinKind,
    DependencyResolution,
    RepoEntry,
    RepoSnapshot,
    TrackedDep,
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
            "eclipse-score": {
                "score_baselibs": BASELIBS,
                "score_unknown": BASELIBS,
                "external": "other-org/external",
            },
        },
        dependency_resolutions=(
            DependencyResolution(
                "other-org/external",
                "2.0.0",
                consumer_org="eclipse-score",
                module="external",
            ),
            DependencyResolution(
                BASELIBS,
                "1.1.0",
                "b" * 40,
                "v1.1.0",
                0,
                0,
                1,
                consumer_org="eclipse-score",
                module="score_baselibs",
            ),
            DependencyResolution(
                BASELIBS,
                "1.0.0",
                "a" * 40,
                "v1.1.0",
                2,
                0,
                3,
                consumer_org="eclipse-score",
                module="score_baselibs",
            ),
            DependencyResolution(
                BASELIBS,
                PIN,
                PIN,
                "v1.1.0",
                None,
                1,
                3,
                DependencyPinKind.COMMIT,
                consumer_org="eclipse-score",
                module="score_baselibs",
            ),
            DependencyResolution(
                BASELIBS,
                "9.9.9",
                latest_release="v1.1.0",
                consumer_org="eclipse-score",
                module="score_unknown",
            ),
        ),
    )


def _row(page: str, label: str) -> str:
    match = re.search(rf"<tr><td>(?:(?!</tr>).)*{re.escape(label)}.*?</tr>", page, re.S)
    assert match, f"no row for {label}"
    return match.group(0)


def test_detail_page_shows_release_and_default_branch_freshness_separately() -> None:
    pages = render_all_pages(_snapshot())

    assert "Bazel may select a different version" in pages["current/index.html"]
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
    assert "Declared direct dependencies only." in used_by


def test_tracked_git_pin_label_stays_neutral_in_version_summaries() -> None:
    snapshot = _snapshot()
    base, _, pinned = snapshot.repos
    tag = "1.1.0"
    fork_pin = DependencyDeclaration(
        "score_baselibs",
        override=DependencyOverride.GIT,
        remote="https://github.com/example-fork/baselibs",
        revision=tag,
        pin_kind=DependencyPinKind.TAG,
    )
    consumer = replace(pinned, content=DeepContentSignals(bazel_deps=(fork_pin,)))
    snapshot = replace(
        snapshot,
        repos=(base, consumer),
        tracked_deps=(TrackedDep(BASELIBS, "score_baselibs"),),
    )
    pages = render_all_pages(snapshot)
    assert '<span class="badge muted">1.1.0</span>' in pages["pinned/index.html"]
    assert pages["index.html"].count('<span class="badge muted">1.1.0</span>') == 2
    markdown = render_versions_section(list(snapshot.repos), snapshot=snapshot)
    assert any("⚪ 1.1.0" in line for line in markdown)


def test_detail_page_marks_changed_archive_and_local_path_overrides() -> None:
    def declarations(suffix: str) -> tuple[DependencyDeclaration, ...]:
        return parse_dependencies(
            [
                f"""
bazel_dep(name = "archive", version = "1.0.0")
bazel_dep(name = "vendored", version = "1.0.0")
URLS = ["https://example.com/archive-{suffix}.tar.gz"]
archive_override(module_name = "archive", urls = URLS)
local_path_override(module_name = "vendored", path = "vendor/{suffix}")
"""
            ]
        )

    consumer = _repo(
        "consumer",
        content=DeepContentSignals(bazel_deps=declarations("head")),
        volatile=VolatileMetricsSnapshot(
            latest_release_version="v1",
            release_bazel_deps=declarations("release"),
        ),
    )
    snapshot = replace(_snapshot(), repos=(consumer,))
    round_tripped = RepoSnapshot.from_dict(snapshot.to_dict())
    page = render_all_pages(round_tripped)["consumer/index.html"]
    assert '<span class="badge yellow">changed</span>' in _row(page, ">archive</span>")
    assert '<span class="badge yellow">changed</span>' in _row(page, ">vendored</span>")
