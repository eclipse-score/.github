import json
from pathlib import Path
from types import SimpleNamespace

import github
import pytest

import generate_repo_overview.cli as cli
import generate_repo_overview.collector as collector
from generate_repo_overview.metrics_html import render_all_pages
from generate_repo_overview.metrics_report import render_metrics_report
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DeepContentSignals,
    RepoEntry,
    RepoSnapshot,
    VolatileMetricsSnapshot,
)
from generate_repo_overview.org_config import load_org_config
from generate_repo_overview.profile_readme import render_repo_row


def test_same_repo_name_has_separate_cache_entries_and_detail_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "org.toml"
    config_path.write_text(
        """
org_name = "first-org"
repo_include_patterns = ["shared", "primary-*"]

[organizations.second-org]
repo_include_patterns = ["shared", "secondary-*"]
reference_integration_repo = ""
""",
        encoding="utf-8",
    )
    config = load_org_config(config_path)
    cache_path = tmp_path / "snapshot.json"
    collector.write_snapshot(
        RepoSnapshot(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            org_name="first-org",
            generated_at="2026-01-01T00:00:00+00:00",
            repos=(
                # Older snapshots inferred the owner from the top-level organization.
                RepoEntry(
                    name="shared",
                    description="Primary repo",
                    category="Infrastructure",
                    subcategory="General",
                    volatile=VolatileMetricsSnapshot(latest_release_version="v1.0.0"),
                ),
                RepoEntry(
                    name="shared",
                    owner="second-org",
                    description="Secondary repo",
                    category="Infrastructure",
                    subcategory="General",
                    content=DeepContentSignals(
                        is_bazel_repo=True,
                        reference_integration_module="shared_module",
                        reference_integration_group="Tools",
                        reference_integration_branch="main",
                        reference_integration_version="v1.0.0",
                        reference_integration_hash="abc1234",
                        reference_integration_resolved_hash="abc1234",
                    ),
                    volatile=VolatileMetricsSnapshot(latest_release_version="v2.0.0"),
                ),
            ),
        ),
        cache_path,
    )

    def active_repos(organization: SimpleNamespace, **_kwargs: object) -> dict:
        return {"shared": collector.ActiveRepositoryData(organization, {})}

    def reuse_cached_entry(*, cached_entry: RepoEntry, **_kwargs: object) -> RepoEntry:
        return cached_entry

    monkeypatch.setattr(
        github,
        "Github",
        lambda **kwargs: SimpleNamespace(
            get_organization=lambda name: SimpleNamespace(login=name)
        ),
    )
    monkeypatch.setattr(collector, "resolve_github_token", lambda _: "token")
    monkeypatch.setattr(collector, "print_rest_api_rate_limit", lambda *_, **__: None)
    monkeypatch.setattr(collector, "fetch_active_repositories", active_repos)
    monkeypatch.setattr(
        collector.repo_entry, "collect_repository_entry", reuse_cached_entry
    )
    monkeypatch.setattr(
        collector.traceability, "fetch_all_traceability_metrics", lambda *_, **__: {}
    )

    snapshot = collector.collect_snapshot(config=config, cache_path=cache_path)
    assert snapshot == collector.load_snapshot(cache_path)
    assert snapshot.organization_names == ("first-org", "second-org")
    assert [(repo.full_name, repo.description) for repo in snapshot.repos] == [
        ("first-org/shared", "Primary repo"),
        ("second-org/shared", "Secondary repo"),
    ]
    # Disabling the integration clears the pin even when the repo content is reused.
    assert snapshot.repos[1].content == DeepContentSignals(is_bazel_repo=True)
    assert config.collection_configs()[0].repo_matches_filter("primary-tool")
    assert not config.collection_configs()[1].repo_matches_filter("primary-tool")
    assert config.collection_configs()[1].repo_matches_filter("secondary-tool")

    pages = render_all_pages(snapshot)
    assert '<option value="">All organizations (2)</option>' in pages["index.html"]
    assert '<option value="first-org">first-org (1)</option>' in pages["index.html"]
    assert '<option value="second-org">second-org (1)</option>' in pages["index.html"]
    assert 'data-category="first-org / Infrastructure"' in pages["index.html"]
    assert 'data-category="second-org / Infrastructure"' in pages["index.html"]
    assert 'href="shared/index.html"' in pages["index.html"]
    assert 'href="@orgs/second-org/shared/index.html"' in pages["index.html"]
    assert 'data-repo-filter="first-org/shared"' in pages["index.html"]
    assert 'data-repo-filter="second-org/shared"' in pages["index.html"]
    assert 'href="https://github.com/first-org/shared"' in pages["shared/index.html"]
    secondary = pages["@orgs/second-org/shared/index.html"]
    assert 'href="https://github.com/second-org/shared"' in secondary
    assert 'href="../index.html"' in pages["shared/index.html"]
    assert 'href="../../../index.html"' in secondary
    assert "&rsaquo; second-org/shared" in secondary
    assert 'src="../../../bazel_logo.svg"' in secondary


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
    Path("org.toml").write_text(
        """
org_name = "first-org"
[organizations.second-org]

[policy_report]
source_repo = "first-org/report-generator"
workflow = "policy.yml"
artifact = "report"
cache_path = "policy.json"
repository_owner = "second-org"
""",
        encoding="utf-8",
    )
    Path("policy.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "summary": {},
                "outcomes": [
                    {
                        "policy_id": "lint",
                        "repository": "second-org",
                        "applicable": "yes",
                        "status": "compliant",
                    },
                    {
                        "policy_id": "format",
                        "repository": "Second-Org/Second-Org",
                        "applicable": "yes",
                        "status": "changes-required",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

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
    html = (site / "index.html").read_text()
    assert "Repository policy compliance (report totals)" in html
    policy_markup = html.split('<div class="section hidden" data-tab="policy-sync"', 1)[
        1
    ]
    assert (
        'data-repo-filter="second-org/second-org" data-repository-category="second-org / Secondary"'
        in policy_markup
    )
    assert 'data-repo-filter="first-org/second-org"' not in policy_markup
    policy_rows = [
        row
        for row in policy_markup.split("</tr>")
        if 'data-repo-filter="second-org/second-org"' in row.lower()
    ]
    assert len(policy_rows) == 1
    assert "policy-status compliant" in policy_rows[0]
    assert "policy-status changes-required" in policy_rows[0]


@pytest.mark.parametrize("schema_version", [30, 31, 32, 33, 34])
def test_older_snapshot_renders_but_is_not_reused_for_collection(
    schema_version: int, tmp_path: Path
) -> None:
    cache = tmp_path / "snapshot.json"
    repo = {
        "name": "tools",
        "content": {"bazel_deps": [["rules_python", "1.2.3"]]},
        "volatile": {"latest_release_version": "v1.2.3"},
    }
    source_repo = {
        "name": "rules_python",
        "content": {"bazel_module_name": "rules_python"},
    }
    cache.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "org_name": "first-org",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "repos": [
                    item if schema_version == 30 else dict(item, owner="first-org")
                    for item in (repo, source_repo)
                ],
            }
        )
    )
    snapshot = collector.load_snapshot(cache)
    assert snapshot.organization_names == ("first-org",)
    assert snapshot.to_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert snapshot.repos[0].full_name == "first-org/tools"
    assert snapshot.repos[0].volatile.latest_release_version == "v1.2.3"
    page = render_all_pages(snapshot)["tools/index.html"]
    assert 'href="https://github.com/first-org/tools"' in page
    assert "rules_python" in page
    source_page = render_all_pages(snapshot)["rules_python/index.html"]
    assert "Consumer data unavailable" in source_page
    assert "No direct dependency on this repository was found." not in source_page
    assert not RepoSnapshot.from_dict(snapshot.to_dict()).dependency_sources_available
    # The cached module files need to be parsed again for registry overrides.
    assert collector.load_snapshot_if_present(cache) is None


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
