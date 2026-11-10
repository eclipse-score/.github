"""Release context must follow workflow sources independently of consumer caches."""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from generate_repo_overview.collector.workflow_versions import (
    fetch_workflow_ref_resolutions,
)
from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    RepoEntry,
    RepoSnapshot,
    WorkflowRefResolution,
    WorkflowSignal,
)

SOURCE = "example/workflows"
DAILY = f"{SOURCE}/.github/workflows/daily.yml@"
DOCS = f"{SOURCE}/.github/workflows/docs.yml@"
SHA = "a" * 40
NEXT_SHA = "b" * 40


def _repo(*references: str) -> RepoEntry:
    return RepoEntry(
        name="consumer",
        description="Consumer",
        category="Modules",
        subcategory="General",
        default_branch="main",
        default_branch_sha="consumer-sha",
        content=DeepContentSignals(
            workflow_refs=tuple(("Daily", ref) for ref in references),
        ),
    )


def _source(*tags: tuple[str, str], release: str | None = "v2.0.0") -> Mock:
    source = Mock()
    source.get_tags.return_value = [
        SimpleNamespace(name=name, commit=SimpleNamespace(sha=sha))
        for name, sha in tags
    ]
    if release:
        source.get_latest_release.return_value = SimpleNamespace(tag_name=release)
    else:
        source.get_latest_release.side_effect = RuntimeError("No published release")
    source.get_commit.return_value = Mock(sha=SHA)
    source.compare.return_value = SimpleNamespace(ahead_by=0, behind_by=0)
    return source


def test_shared_pins_fetch_source_metadata_and_comparisons_only_once() -> None:
    """Repeated consumers and workflow paths must not multiply API traffic."""
    source = _source(("v1.0.0", SHA))
    source.compare.return_value = SimpleNamespace(ahead_by=2, behind_by=7)
    github = Mock()
    github.get_repo.return_value = source
    repos = [_repo(DAILY + SHA, DOCS + SHA), _repo(DAILY + SHA)]

    results = fetch_workflow_ref_resolutions(repos, github=github)

    assert len(results) == 2
    assert all(r.version_tag == "v1.0.0" for r in results)
    assert all((r.ahead_by, r.behind_by) == (2, 7) for r in results)
    github.get_repo.assert_called_once_with(SOURCE)
    source.get_tags.assert_called_once_with()
    source.get_latest_release.assert_called_once_with()
    source.get_commit.assert_not_called()
    source.compare.assert_called_once_with("v2.0.0", SHA)


@pytest.mark.parametrize("pin", ["main", SHA[:12]])
def test_branch_and_short_sha_are_completed_before_tag_matching(pin: str) -> None:
    source = _source(("v2.0.0", SHA))
    github = Mock()
    github.get_repo.return_value = source

    (result,) = fetch_workflow_ref_resolutions([_repo(DAILY + pin)], github=github)

    assert result.version_tag == "v2.0.0"
    assert result.resolved_sha == SHA
    source.get_commit.assert_called_once_with(pin)
    source.get_commit.return_value.complete.assert_called_once_with()


def test_matching_workflow_tag_takes_precedence_over_global_and_unrelated_tags() -> (
    None
):
    """Tags from another workflow at the same commit cannot name this pin."""
    source = _source(
        ("v2.0.0", SHA),
        ("daily/v1.0.0", SHA),
        ("docs/v9.0.0", SHA),
        ("latest", SHA),
    )
    github = Mock()
    github.get_repo.return_value = source

    daily, docs = fetch_workflow_ref_resolutions(
        [_repo(DAILY + SHA, DOCS + SHA)], github=github
    )

    assert daily.version_tag == "daily/v1.0.0"
    assert docs.version_tag == "docs/v9.0.0"
    assert daily.latest_release == "v2.0.0"


def test_new_tags_releases_and_moved_branches_refresh_without_consumer_changes() -> (
    None
):
    """The same cached consumer refs can gain new release context on each collect."""
    source = _source()
    source.compare.return_value = SimpleNamespace(ahead_by=3, behind_by=0)
    github = Mock()
    github.get_repo.return_value = source
    cached_repos = [_repo(DAILY + "main")]
    (before,) = fetch_workflow_ref_resolutions(cached_repos, github=github)

    source.get_tags.return_value = [
        SimpleNamespace(name="v3.0.0", commit=SimpleNamespace(sha=NEXT_SHA))
    ]
    source.get_latest_release.return_value = SimpleNamespace(tag_name="v3.0.0")
    source.get_commit.return_value = Mock(sha=NEXT_SHA)
    source.compare.return_value = SimpleNamespace(ahead_by=0, behind_by=0)
    (after,) = fetch_workflow_ref_resolutions(cached_repos, github=github)

    assert before.version_tag is None
    assert before.resolved_sha == SHA
    assert before.ahead_by == 3
    assert after.version_tag == "v3.0.0"
    assert after.latest_release == "v3.0.0"
    assert after.resolved_sha == NEXT_SHA
    assert (after.ahead_by, after.behind_by) == (0, 0)


def test_tag_pin_does_not_need_a_commit_request_or_a_published_release() -> None:
    source = _source(("v1.0.0", SHA), release=None)
    github = Mock()
    github.get_repo.return_value = source

    (result,) = fetch_workflow_ref_resolutions([_repo(DAILY + "v1.0.0")], github=github)

    assert result.version_tag == "v1.0.0"
    assert result.latest_release is None
    assert result.ahead_by is None
    source.get_commit.assert_not_called()
    source.compare.assert_not_called()


@pytest.mark.parametrize("tag", ["v1", "v1.2", "1.2.3", "v1.2.3-rc.1"])
def test_version_tag_formats_resolve_sha_pins(tag: str) -> None:
    source = _source((tag, SHA), release=None)
    github = Mock()
    github.get_repo.return_value = source

    (result,) = fetch_workflow_ref_resolutions([_repo(DAILY + SHA)], github=github)

    assert result.version_tag == tag


def test_partial_api_failures_preserve_available_context_and_other_sources() -> None:
    broken = _source()
    broken.get_tags.side_effect = RuntimeError("Cannot list tags")
    broken.get_commit.return_value.complete.side_effect = RuntimeError("Invalid ref")
    broken.compare.side_effect = RuntimeError("Comparison unavailable")
    healthy = _source(("v1.0.0", SHA))
    github = Mock()
    github.get_repo.side_effect = [broken, healthy]

    results = fetch_workflow_ref_resolutions(
        [
            _repo(
                DAILY + "missing",
                DAILY + SHA,
                "other/workflows/.github/workflows/ci.yml@" + SHA,
            )
        ],
        github=github,
    )

    assert len(results) == 3
    missing = next(r for r in results if r.reference == DAILY + "missing")
    assert missing.resolved_sha is None
    assert missing.latest_release == "v2.0.0"
    assert missing.ahead_by is None
    healthy_result = next(r for r in results if r.reference.startswith("other/"))
    assert healthy_result.version_tag == "v1.0.0"
    assert healthy_result.ahead_by == 0


def test_unavailable_repository_is_attempted_once_and_does_not_abort_collection() -> (
    None
):
    github = Mock()
    github.get_repo.side_effect = RuntimeError("Access denied")

    assert (
        fetch_workflow_ref_resolutions([_repo(DAILY + SHA, DOCS + SHA)], github=github)
        == ()
    )
    github.get_repo.assert_called_once_with(SOURCE)


@pytest.mark.parametrize(
    ("ahead", "behind", "expected"),
    [
        (0, 0, None),
        (3, 0, "↑3"),
        (0, 7, "↓7"),
        (2, 21, "↓21"),
        (None, None, "?</span>"),
    ],
)
def test_resolved_pins_roundtrip_and_render_in_both_views_without_losing_original_link(
    ahead: int | None, behind: int | None, expected: str | None
) -> None:
    resolution = WorkflowRefResolution(
        reference=DAILY + SHA,
        resolved_sha=SHA,
        version_tag="v1.0.0",
        latest_release="v2.0.0",
        ahead_by=ahead,
        behind_by=behind,
    )
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="example",
        generated_at="2026-11-10T12:00:00+00:00",
        repos=(_repo(DAILY + SHA),),
        workflow_signals=(WorkflowSignal("Daily", DAILY),),
        workflow_ref_resolutions=(resolution,),
    )
    restored = RepoSnapshot.from_dict(json.loads(json.dumps(snapshot.to_dict())))
    assert restored == snapshot
    pages = render_all_pages(restored)
    for filename in ("index.html", "consumer/index.html"):
        page = pages[filename]
        assert ">v1.0.0</a>" in page
        assert f"/blob/{SHA}/.github/workflows/daily.yml" in page
        assert DAILY + SHA in page
        assert 'class="badge green mono"' in page
        if expected:
            assert "vs v2.0.0" in page
            assert expected in page
        else:
            assert "vs v2.0.0" not in page
        if ahead and behind:
            assert "↑2" in page
            assert "↓21" in page
            assert "git-ref-count large" in page

    # A failed lookup still shows the original SHA and keeps the source link.
    unresolved = render_all_pages(replace(snapshot, workflow_ref_resolutions=()))
    assert f">{SHA[:12]}</a>" in unresolved["index.html"]
    assert "vs v2.0.0" not in unresolved["index.html"]


def test_release_context_is_escaped_in_version_labels_and_tooltips() -> None:
    from generate_repo_overview._html_common import workflow_ref_badges

    html = workflow_ref_badges(
        _repo(DAILY + SHA),
        "Daily",
        (
            WorkflowRefResolution(
                reference=DAILY + SHA,
                version_tag='<script data-tag="tag">',
                latest_release='<script data-tag="release">',
                ahead_by=1,
                behind_by=0,
            ),
        ),
    )
    assert "<script" not in html
    assert "&lt;script" in html
    assert "&quot;release&quot;" in html


def test_collect_snapshot_refreshes_workflow_releases_while_reusing_consumer_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Top-level collection must enrich cached refs again after a source release."""
    import sys

    import generate_repo_overview.collector as collector
    from generate_repo_overview.org_config import OrgConfig

    source = _source()
    source.compare.return_value = SimpleNamespace(ahead_by=1, behind_by=0)
    github = Mock()
    github.get_repo.return_value = source
    monkeypatch.setitem(
        sys.modules,
        "github",
        SimpleNamespace(
            Auth=SimpleNamespace(Token=lambda token: token),
            Github=lambda **kwargs: github,
        ),
    )
    monkeypatch.setattr(collector, "resolve_github_token", lambda _: "token")
    monkeypatch.setattr(
        collector, "print_rest_api_rate_limit", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        collector.traceability,
        "fetch_all_traceability_metrics",
        lambda *args, **kwargs: {},
    )
    cached_inputs = []

    def cached_consumers(*args, existing_snapshot=None, **kwargs):
        cached_inputs.append(existing_snapshot)
        return (
            list(existing_snapshot.repos) if existing_snapshot else [_repo(DAILY + SHA)]
        )

    monkeypatch.setattr(collector, "fetch_repositories", cached_consumers)
    cache_path = tmp_path / "snapshot.json"
    config = OrgConfig(
        org_name="example", workflow_signals=(WorkflowSignal("Daily", DAILY),)
    )
    first = collector.collect_snapshot(config=config, cache_path=cache_path)
    source.get_tags.return_value = [
        SimpleNamespace(name="v3.0.0", commit=SimpleNamespace(sha=SHA))
    ]
    source.get_latest_release.return_value = SimpleNamespace(tag_name="v3.0.0")
    source.compare.return_value = SimpleNamespace(ahead_by=0, behind_by=0)
    second = collector.collect_snapshot(config=config, cache_path=cache_path)

    assert cached_inputs == [None, first]
    assert second.repos == first.repos
    assert first.workflow_ref_resolutions[0].version_tag is None
    assert second.workflow_ref_resolutions[0].version_tag == "v3.0.0"
    assert second.workflow_ref_resolutions[0].ahead_by == 0
    assert RepoSnapshot.from_dict(json.loads(cache_path.read_text())) == second


@pytest.mark.parametrize("pin_type", ["sha", "tag"])
@pytest.mark.parametrize(
    ("tag", "release", "show_difference"),
    [
        ("v0.0.3", "v0.0.3", False),
        ("v0.0.1", "v0.0.3", True),
        ("on-pr/v0.0.0", "v0.0.3", False),
        ("on-pr/v0.0.0", "on-pr/v0.0.1", True),
        ("on-pr/v0.0.0", "docs/v0.0.3", False),
    ],
)
def test_green_version_labels_compare_only_differing_releases_in_the_same_series(
    pin_type: str, tag: str, release: str, show_difference: bool
) -> None:
    """Both direct tags and SHA pins resolved to tags follow the same display rules."""
    from generate_repo_overview._html_common import workflow_ref_badges

    pin = SHA if pin_type == "sha" else tag
    reference = DAILY + pin
    html = workflow_ref_badges(
        _repo(reference),
        "Daily",
        (
            WorkflowRefResolution(
                reference=reference,
                version_tag=tag,
                latest_release=release,
                ahead_by=0,
                behind_by=73,
            ),
        ),
    )

    assert 'class="badge green mono"' in html
    assert f">{tag}</a>" in html
    assert (f"vs {release}" in html) == show_difference
    assert ("↓73" in html) == show_difference
    assert f"/blob/{pin.replace('/', '%2F')}/" in html
