from pathlib import Path

import generate_repo_overview.cli as cli
from generate_repo_overview.collector import write_snapshot
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    RepoEntry,
    RepoSnapshot,
    SphinxItem,
    TraceabilityTypeMetrics,
    TrackedDep,
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
            RepoEntry(
                name="logging",
                description="Logging module",
                category="Modules",
                subcategory="General",
                content=DeepContentSignals(
                    is_bazel_repo=True,
                    has_bazel_module=True,
                    bazel_module_name="score_logging",
                    sphinx_features=(
                        SphinxItem(
                            path="docs/features/log_trace/logging",
                            title="Logging",
                            identifier="feat__logging",
                            source_repo="eclipse-score/score",
                        ),
                    ),
                    sphinx_modules=(
                        SphinxItem(
                            path="docs/modules/logging",
                            title="Logging",
                            identifier="mod__logging",
                            source_repo="eclipse-score/score",
                        ),
                    ),
                    docs_feature_paths=("docs/features/logging", "docs/features"),
                    repo_sphinx_features=(
                        SphinxItem(
                            path="docs/features/logging/architecture/index.rst",
                            title="Logging",
                            identifier="feat__logging_repo",
                        ),
                    ),
                    repo_sphinx_modules=(
                        SphinxItem(
                            path="docs/module/index.rst",
                            title="Logging",
                            identifier="mod__logging_repo",
                        ),
                    ),
                    sphinx_project_name="S-CORE Logging",
                    sphinx_project_prefix="LOGGING_",
                ),
            ),
            RepoEntry(
                name="score",
                description="Platform documentation",
                category="General",
                subcategory="General",
                content=DeepContentSignals(
                    is_bazel_repo=True,
                    bazel_module_name="score_platform",
                    docs_feature_paths=("docs/features/should-not-show",),
                    repo_sphinx_features=(
                        SphinxItem(
                            path="docs/features/should-not-show/architecture/index.rst",
                            title="Platform-only Feature",
                            identifier="feat__should_not_show",
                        ),
                    ),
                ),
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

    bazel_icon = output_dir / "bazel_logo.svg"
    assert bazel_icon.exists()


def test_render_detail_page_shows_tracked_dep_versions(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "repo_overview.json"
    output_dir = tmp_path / "_site"
    write_snapshot(_make_snapshot_with_dac(), snapshot_path)

    cli.main(
        [
            "render-details",
            "--input",
            str(snapshot_path),
            "--output",
            str(output_dir),
        ]
    )

    detail = output_dir / "my-dac-repo" / "index.html"
    assert detail.exists()
    detail_content = detail.read_text(encoding="utf-8")
    assert "Docs As Code Version" in detail_content
    assert 'href="https://eclipse-score.github.io/my-dac-repo"' in detail_content

    plain_detail_content = (output_dir / "plain-repo" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'href="https://eclipse-score.github.io/plain-repo"' not in plain_detail_content

    index_content = (output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="https://eclipse-score.github.io/my-dac-repo"' in index_content
    assert 'href="https://eclipse-score.github.io/plain-repo"' not in index_content


def _make_snapshot_with_dac() -> RepoSnapshot:
    return RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-04-13T12:00:00+00:00",
        tracked_deps=(
            TrackedDep(
                repo="eclipse-score/docs-as-code", module_name="score_docs_as_code"
            ),
        ),
        repos=(
            RepoEntry(
                name="my-dac-repo",
                description="A repo with docs-as-code",
                category="Components",
                subcategory="General",
                content=DeepContentSignals(
                    bazel_deps=(("score_docs_as_code", "4.0.1"),),
                ),
                traceability=(
                    TraceabilityTypeMetrics(
                        type_name="feature",
                        req_total=10,
                        req_with_code_link=8,
                        req_with_test_link=6,
                        req_fully_linked=5,
                        tests_total=20,
                        tests_linked=15,
                    ),
                ),
            ),
            RepoEntry(
                name="plain-repo",
                description="No docs-as-code",
                category="Infrastructure",
                subcategory="General",
            ),
        ),
    )


def test_render_details_traceability_tab(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "repo_overview.json"
    output_dir = tmp_path / "_site"
    write_snapshot(_make_snapshot_with_dac(), snapshot_path)

    cli.main(
        [
            "render-details",
            "--input",
            str(snapshot_path),
            "--output",
            str(output_dir),
        ]
    )

    content = (output_dir / "index.html").read_text(encoding="utf-8")
    assert 'data-tab="traceability"' in content
    assert "Traceability" in content
    assert 'data-repo="my-dac-repo"' in content
    assert 'data-repo="plain-repo"' not in content
    # Server-rendered metrics values
    assert "Feature" in content
    assert ">10<" in content  # req_total
    assert "1 / 1" in content  # repos loaded summary
    # No client-side fetch variables
    assert "traceabilityRepos" not in content
    assert "orgName" not in content


def test_render_details_naming_tab_includes_all_bazel_repositories(
    tmp_path: Path,
) -> None:
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

    content = (output_dir / "index.html").read_text(encoding="utf-8")
    assert 'data-tab="naming">Naming</button>' in content
    assert "if (h === 'modules') return 'naming';" in content
    assert "Platform Feature Path" in content
    assert "Platform Docs" in content
    assert "eclipse-score/score" in content
    assert "log_trace/logging" in content
    assert "feat__logging" in content
    assert "score_logging" in content
    assert "mod__logging" in content
    assert "Repo Feature Path" in content
    assert "docs/features/logging" in content
    assert "Sphinx Feature" in content
    assert "feat__logging_repo" in content
    assert "Sphinx Module" in content
    assert "mod__logging_repo" in content
    assert content.count('class="mapping-warning"') == 2
    assert "Feature declarations belong in the platform documentation." in content
    assert "Module declarations belong in the module repository." in content
    assert "Sphinx Config" in content
    assert "S-CORE Logging" in content
    assert "LOGGING_" in content
    assert (
        '<span class="name-match exact" '
        'title="The module-template single-feature layout derives the feature name '
        'from the repository or module name.">'
        "(single-feature layout; no folder name)</span>"
    ) in content
    assert '<code class="mono">docs/features</code>' not in content
    assert 'class="name-match exact"' in content
    assert 'data-tooltip="Bazel repository name.' in content
    naming_content = content.split(
        '<div class="section naming-section hidden" data-tab="naming"',
        maxsplit=1,
    )[1].split(
        '<div class="section hidden" data-tab="traceability">',
        maxsplit=1,
    )[0]
    assert naming_content.count('data-tab="naming"') == 2
    assert naming_content.count('<table class="naming-table">') == 3
    assert naming_content.count("<th ") == 24
    assert naming_content.count("data-tooltip=") == 24
    assert 'data-category="Infrastructure"' in naming_content
    assert "tools" in naming_content
    assert "Platform-only Feature" not in naming_content
    assert "docs/features/should-not-show" not in naming_content
    assert (
        naming_content.count(
            'title="Not applicable to a platform documentation repository."'
        )
        == 2
    )


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
    assert 'href="tools/index.html"' in index_content
