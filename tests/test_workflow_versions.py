"""Tracked workflow pins survive collection and appear in their own dashboard tab."""

import json
from dataclasses import replace

import pytest

from generate_repo_overview.collector import signal_detection
from generate_repo_overview.collector.repo_entry import cached_signals_for_repository
from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    RepoEntry,
    RepoSnapshot,
    WorkflowSignal,
)

REFERENCE = "example/workflows/.github/workflows/daily.yml@"
SIGNALS = (WorkflowSignal(label="Daily <CI>", reference=REFERENCE),)
SHA = "0123456789abcdef" * 2 + "01234567"


def test_collect_only_job_calls_and_preserve_distinct_pins() -> None:
    """Comments, actions, and shell snippets must not create false adoption."""
    workflows = {
        ".github/workflows/a.yml": f"""
# uses: {REFERENCE}comment
jobs:
  tag:
    uses: '{REFERENCE}v2.3.0' # release
  commit: {{uses: "{REFERENCE}{SHA}"}}
  local:
    uses: ./.github/workflows/local.yml
  regular:
    steps:
      - uses: {REFERENCE}step
      - run: |
          uses: {REFERENCE}shell
""",
        ".github/workflows/b.yaml": f"jobs:\n  duplicate:\n    uses: {REFERENCE}v2.3.0\n",
        "docs/example.yml": f"jobs:\n  example:\n    uses: {REFERENCE}docs\n",
        ".github/workflows/broken.yml": "jobs: [invalid",
    }
    # Exercise the same inspection path as the checkout collector without Git.
    payload = signal_detection._inspect_repository_content(
        set(workflows),
        workflows.get,
        workflow_signals=SIGNALS,
        top_languages=(),
    )
    assert payload["matched_workflow_signals"] == ("Daily <CI>",)
    assert payload["workflow_refs"] == (
        ("Daily <CI>", REFERENCE + SHA),
        ("Daily <CI>", REFERENCE + "v2.3.0"),
    )


@pytest.mark.parametrize(
    "content", ["", "[]", "jobs: []", "jobs: {invalid: null}", "jobs: ["]
)
def test_unusable_workflow_has_no_pins(content: str) -> None:
    assert (
        signal_detection.detect_workflow_refs(
            tree_paths={".github/workflows/ci.yml"},
            read_text=lambda _: content,
            workflow_signals=SIGNALS,
        )
        == ()
    )


def test_workflow_pins_survive_json_roundtrip_and_content_cache() -> None:
    content = DeepContentSignals(
        matched_workflow_signals=("Daily <CI>",),
        workflow_refs=(
            ("Daily <CI>", REFERENCE + "v2"),
            ("Daily <CI>", REFERENCE + SHA),
        ),
    )
    snapshot = _snapshot(content)
    restored = RepoSnapshot.from_dict(json.loads(json.dumps(snapshot.to_dict())))
    assert restored.repos[0].content == content
    cached = cached_signals_for_repository(
        restored.repos[0],
        default_branch="main",
        default_branch_sha="abc",
    )
    assert cached is not None
    assert cached["workflow_refs"] == content.workflow_refs


def _snapshot(content: DeepContentSignals) -> RepoSnapshot:
    return RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="example",
        generated_at="2026-11-10T12:00:00+00:00",
        workflow_signals=SIGNALS,
        repos=(
            RepoEntry(
                name="consumer",
                description="Consumer",
                category="Modules",
                subcategory="General",
                default_branch="main",
                default_branch_sha="abc",
                content=content,
            ),
        ),
    )


def test_workflow_tab_has_linked_pins_and_leaves_tech_stack() -> None:
    content = DeepContentSignals(
        workflow_refs=(
            ("Daily <CI>", REFERENCE + "v2.3.0"),
            ("Daily <CI>", REFERENCE + SHA),
            ("Daily <CI>", REFERENCE + "feature/docs"),
        ),
    )
    snapshot = replace(
        _snapshot(content),
        workflow_signals=(*SIGNALS, WorkflowSignal("Unused", "other/ref@")),
    )
    pages = render_all_pages(snapshot)
    index = pages["index.html"]
    assert 'data-tab="workflows">Workflows</button>' in index
    workflow_section = index.split(
        '<div class="section hidden" data-tab="workflows"', 1
    )[1].split('<div class="section hidden" data-tab="tech-stack"', 1)[0]
    assert "Daily &lt;CI&gt;" in workflow_section
    assert f"/blob/{SHA}/.github/workflows/daily.yml" in workflow_section
    assert f">{SHA[:12]}</a>" in workflow_section
    assert "/blob/v2.3.0/.github/workflows/daily.yml" in workflow_section
    assert "/blob/feature%2Fdocs/.github/workflows/daily.yml" in workflow_section
    assert '<span class="text-muted">—</span>' in workflow_section
    assert "data-repo-filter" in workflow_section
    tech_stack = index.split('<div class="section hidden" data-tab="tech-stack"', 1)[
        1
    ].split('<div class="section', 1)[0]
    assert "Daily &lt;CI&gt;" not in tech_stack
    assert "Daily &lt;CI&gt;" in pages["consumer/index.html"]
    assert ">v2.3.0</a>" in pages["consumer/index.html"]


def test_workflows_tab_absent_without_configuration() -> None:
    snapshot = replace(_snapshot(DeepContentSignals()), workflow_signals=())
    pages = render_all_pages(snapshot)
    assert 'data-tab="workflows"' not in pages["index.html"]
    assert ">Workflows<" not in pages["consumer/index.html"]
    # Hash validation uses rendered tabs, so a stale #workflows bookmark falls back.
    assert (
        "const TAB_IDS = Array.from(document.querySelectorAll('.tab-btn')"
        in pages["index.html"]
    )


def test_workflows_tab_present_when_configured_but_unused() -> None:
    pages = render_all_pages(_snapshot(DeepContentSignals()))
    assert 'data-tab="workflows">Workflows</button>' in pages["index.html"]
    assert "Daily &lt;CI&gt;" in pages["index.html"]
