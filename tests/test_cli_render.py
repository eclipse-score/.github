from pathlib import Path

import generate_repo_overview.cli as cli
from generate_repo_overview.collector import write_snapshot
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    RepoEntry,
    RepoSnapshot,
    VolatileMetricsSnapshot,
)


def _make_snapshot() -> RepoSnapshot:
    return RepoSnapshot(
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


def test_render_overview_writes_readme(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "repo_overview.json"
    readme_output = tmp_path / "README.md"
    write_snapshot(_make_snapshot(), snapshot_path)

    exit_code = cli.main(
        [
            "render-overview",
            "--input",
            str(snapshot_path),
            "--output",
            str(readme_output),
        ]
    )

    assert exit_code == 0
    assert readme_output.exists()
    assert "### Infrastructure" in readme_output.read_text(encoding="utf-8")


def test_render_details_writes_html(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "repo_overview.json"
    output_dir = tmp_path / "_site"
    write_snapshot(_make_snapshot(), snapshot_path)

    exit_code = cli.main(
        [
            "render-details",
            "--input",
            str(snapshot_path),
            "--output",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    index = output_dir / "index.html"
    assert index.exists()
    content = index.read_text(encoding="utf-8")
    assert "Cross-Repo Metrics" in content
    assert "<!DOCTYPE html>" in content


def test_render_details_writes_repo_detail_pages(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "repo_overview.json"
    output_dir = tmp_path / "_site"
    write_snapshot(_make_snapshot(), snapshot_path)

    cli.main(
        [
            "render-details",
            "--input",
            str(snapshot_path),
            "--output",
            str(output_dir),
        ]
    )

    detail = output_dir / "tools" / "index.html"
    assert detail.exists()
    detail_content = detail.read_text(encoding="utf-8")
    assert "tools" in detail_content
    assert "../" in detail_content
    assert "<!DOCTYPE html>" in detail_content


def test_render_details_index_links_to_detail_pages(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "repo_overview.json"
    output_dir = tmp_path / "_site"
    write_snapshot(_make_snapshot(), snapshot_path)

    cli.main(
        [
            "render-details",
            "--input",
            str(snapshot_path),
            "--output",
            str(output_dir),
        ]
    )

    index_content = (output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="tools/"' in index_content
