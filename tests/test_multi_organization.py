from pathlib import Path

import pytest

import generate_repo_overview.cli as cli
import generate_repo_overview.collector as collector
from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.metrics_report import (
    get_latest_tracked_dep_version,
    render_metrics_report,
)
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    RepoEntry,
    RepoSnapshot,
    TrackedDep,
)
from generate_repo_overview.profile_readme import render_repo_row


@pytest.mark.parametrize(
    ("primary_org", "owner", "name"),
    [
        ("primary-org", "invalid owner", "tools"),
        ("primary-org", "first-org", "invalid name"),
        ("invalid primary", "", "tools"),
    ],
)
def test_render_details_rejects_invalid_snapshot_path_segments(
    tmp_path: Path, primary_org: str, owner: str, name: str
) -> None:
    path = tmp_path / "snapshot.json"
    collector.write_snapshot(
        RepoSnapshot(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            org_name=primary_org,
            generated_at="2026-01-01T00:00:00+00:00",
            repos=(
                RepoEntry(
                    name=name,
                    owner=owner,
                    description="Tools",
                    category="Infrastructure",
                    subcategory="General",
                ),
            ),
        ),
        path,
    )
    output = tmp_path / "site"
    with pytest.raises(ValueError, match="Invalid repository name in snapshot"):
        cli.main(
            [
                "render-details",
                "--input",
                str(path),
                "--output",
                str(output),
                "--org-config",
                str(tmp_path / "unused.toml"),
            ]
        )
    assert not output.exists()


def test_render_details_reserves_secondary_org_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="first-org",
        additional_org_names=("second-org",),
        generated_at="2026-01-01T00:00:00+00:00",
        repos=(
            RepoEntry("second-org", "", "Primary", "General", owner="first-org"),
            RepoEntry("index.html", "", "Secondary", "General", owner="second-org"),
            RepoEntry("second-org", "", "Secondary", "General", owner="second-org"),
        ),
    )
    collector.write_snapshot(snapshot, Path("snapshot.json"))
    Path("org.toml").write_text('org_name = "first-org"\n', encoding="utf-8")

    assert (
        cli.main(
            [
                "render-details",
                "--input",
                "snapshot.json",
                "--output",
                "site",
                "--org-config",
                "org.toml",
            ]
        )
        == 0
    )
    site = Path("site")
    assert (site / "second-org/index.html").is_file()
    assert (site / "@orgs/second-org/index.html/index.html").is_file()
    assert (site / "@orgs/second-org/second-org/index.html").is_file()


def test_schema_30_single_org_snapshot_can_be_read_and_written_as_schema_31() -> None:
    snapshot = RepoSnapshot.from_dict(
        {
            "schema_version": 30,
            "org_name": "first-org",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "repos": [
                {"name": "tools", "volatile": {"latest_release_version": "v1.2.3"}}
            ],
        }
    )
    assert snapshot.organization_names == ("first-org",)
    assert snapshot.to_dict()["schema_version"] == 31
    assert snapshot.repos[0].full_name == "first-org/tools"
    repos = list(snapshot.repos)
    assert (
        get_latest_tracked_dep_version(repos, TrackedDep("first-org/tools", "tools"))
        == "1.2.3"
    )
    assert (
        get_latest_tracked_dep_version(repos, TrackedDep("second-org/tools", "tools"))
        is None
    )
    assert (
        'href="https://github.com/first-org/tools"'
        in render_all_pages(snapshot)["tools/index.html"]
    )


def test_markdown_qualifies_secondary_repository_names_in_each_table() -> None:
    primary = RepoEntry("tools", "", "Tools", "General", owner="first-org")
    secondary = RepoEntry("tools", "", "Tools", "General", owner="second-org")
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="first-org",
        generated_at="2026-01-01T00:00:00+00:00",
        repos=(primary, secondary),
        additional_org_names=("second-org",),
    )
    primary_link = "[tools](https://github.com/first-org/tools)"
    secondary_link = "[second-org/tools](https://github.com/second-org/tools)"
    markdown = render_metrics_report(snapshot)
    assert markdown.count(primary_link) == 3
    assert markdown.count(secondary_link) == 3
    assert secondary_link in render_repo_row(secondary, "first-org")


def test_markdown_rejects_an_invalid_owner_instead_of_interpreting_it_as_markup() -> (
    None
):
    entry = RepoEntry("tools", "", "Tools", "General", owner="invalid]owner")
    snapshot = RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="first-org",
        generated_at="2026-01-01T00:00:00+00:00",
        repos=(entry,),
    )
    with pytest.raises(ValueError, match="Invalid repository name in snapshot"):
        render_repo_row(entry, "first-org")
    with pytest.raises(ValueError, match="Invalid repository name in snapshot"):
        render_metrics_report(snapshot)
