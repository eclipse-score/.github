from pathlib import Path

import generate_repo_overview.cli as cli
from generate_repo_overview.collector import write_snapshot
from generate_repo_overview.models import (
    DeepContentSignals,
    SNAPSHOT_SCHEMA_VERSION,
    RepoEntry,
    RepoSnapshot,
    VolatileMetricsSnapshot,
)


def test_render_writes_both_reports_from_cached_snapshot(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "repo_overview.json"
    readme_output = tmp_path / "README.md"
    metrics_output = tmp_path / "metrics.md"
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        repos=(
            RepoEntry(
                name="tools",
                description="Tooling",
                category="Infrastructure",
                subcategory="Tooling",
                content=DeepContentSignals(
                    is_bazel_repo=True,
                    bazel_version="8.4.2",
                    has_lint_config=True,
                    has_ci=True,
                    has_coverage_config=False,
                ),
                volatile=VolatileMetricsSnapshot(
                    last_push_date="2026-04-12",
                    open_issues=2,
                    open_prs=1,
                    open_ready_prs=1,
                    open_draft_prs=0,
                    latest_release_date="2026-04-01",
                ),
                stars=3,
                forks=4,
            ),
        ),
    )
    write_snapshot(snapshot, snapshot_path)

    exit_code = cli.main(
        [
            "render",
            "--input",
            str(snapshot_path),
            "--readme-output",
            str(readme_output),
            "--metrics-output",
            str(metrics_output),
        ]
    )

    assert exit_code == 0
    assert readme_output.exists()
    assert metrics_output.exists()
    assert "### Infrastructure" in readme_output.read_text(encoding="utf-8")
    assert "# Cross-Repo Metrics Report" in metrics_output.read_text(encoding="utf-8")
