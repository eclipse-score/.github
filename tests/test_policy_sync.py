from __future__ import annotations

import base64
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

import generate_repo_overview.cli as cli
from generate_repo_overview._html_index import render_index_page
from generate_repo_overview.collector import write_snapshot
from generate_repo_overview.models import SNAPSHOT_SCHEMA_VERSION, RepoSnapshot
from generate_repo_overview.org_config import (
    OrgConfig,
    PolicyReportConfig,
    load_org_config,
)
from generate_repo_overview.policy_sync import (
    PolicySyncChange,
    PolicySyncOutcome,
    PolicySyncReport,
    PolicySyncSummary,
    fetch_policy_report,
    load_policy_descriptions,
    load_policy_sync_report,
    parse_policy_sync_report,
)


def _report_payload() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "summary": {
            "repositories": 2,
            "synchronized": 2,
            "sync_failures": 0,
            "skipped": 0,
            "evaluations": 2,
            "compliant": 1,
            "drifted": 1,
            "not_applicable": 0,
            "evaluation_failures": 0,
            "pull_requests_created": 0,
            "pull_requests_updated": 0,
            "pull_requests_open": 1,
            "pull_requests_recreated": 0,
            "pull_requests_closed": 0,
            "duration_seconds": 1.5,
        },
        "outcomes": [
            {
                "policy_id": "minimum-bazel-version",
                "repository": "tools",
                "applicable": "yes (live)",
                "status": "changes-required",
                "changes": [
                    {
                        "path": "MODULE.bazel",
                        "description": "update Bazel",
                        "rationale": "central policy",
                    }
                ],
                "pull_request_url": "https://github.com/eclipse-score/tools/pull/1",
                "policy_pr_status": "open",
                "warnings": ["warning text"],
                "error": None,
            },
            {
                "policy_id": "minimum-bazel-version",
                "repository": "score",
                "applicable": "yes (live)",
                "status": "compliant",
                "changes": [],
                "pull_request_url": None,
                "policy_pr_status": "none",
                "warnings": [],
                "error": None,
            },
        ],
    }


def _minimal_snapshot() -> RepoSnapshot:
    return RepoSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        org_name="eclipse-score",
        generated_at="2026-08-30T12:00:00+00:00",
        repos=(),
    )


def test_policy_report_config_defaults_and_loading(tmp_path: Path) -> None:
    default = OrgConfig(org_name="test").policy_report
    assert default.enabled is False
    assert default.filename == "repo-policy-sync-report.json"
    assert default.cache_path == Path(".cache/repo-policy-sync-report.json")
    assert default.definitions_path == "repo_policy_sync/policies"
    assert default.descriptions_cache_path == Path(
        ".cache/repo-policy-sync-descriptions.json"
    )

    config_path = tmp_path / "org.toml"
    config_path.write_text(
        """org_name = 'eclipse-score'

[policy_report]
source_repo = 'eclipse-score/tools'
workflow = 'repo-policy-sync.yml'
artifact = 'repo-policy-sync-report'
filename = 'report.json'
cache_path = '.cache/report.json'
definitions_path = 'repo_policy_sync/policies'
descriptions_cache_path = '.cache/descriptions.json'
""",
        encoding="utf-8",
    )
    config = load_org_config(config_path)
    assert config.policy_report == PolicyReportConfig(
        source_repo="eclipse-score/tools",
        workflow="repo-policy-sync.yml",
        artifact="repo-policy-sync-report",
        filename="report.json",
        cache_path=Path(".cache/report.json"),
        definitions_path="repo_policy_sync/policies",
        descriptions_cache_path=Path(".cache/descriptions.json"),
    )


@pytest.mark.parametrize(
    ("setting", "message"),
    [
        ("source_repo = 'tools'", "org/repo"),
        ("workflow = 'repo-policy-sync.txt'", "workflow filename"),
        ("artifact = 'policy report'", "whitespace"),
        ("filename = 'report.txt'", "JSON filename"),
        ("cache_path = '../report.json'", "without '..'"),
        ("definitions_path = '../policies'", "relative path"),
        ("descriptions_cache_path = '../descriptions.json'", "without '..'"),
    ],
)
def test_policy_report_config_rejects_invalid_values(
    tmp_path: Path, setting: str, message: str
) -> None:
    path = tmp_path / "org.toml"
    setting_key = setting.split(" ", 1)[0]
    settings = {
        "source_repo": "source_repo = 'org/tools'",
        "workflow": "workflow = 'repo-policy-sync.yml'",
        "artifact": "artifact = 'report'",
        "filename": "filename = 'report.json'",
        "cache_path": "cache_path = '.cache/report.json'",
        "definitions_path": "definitions_path = 'repo_policy_sync/policies'",
        "descriptions_cache_path": "descriptions_cache_path = '.cache/descriptions.json'",
    }
    lines = ["org_name = 'test'", "[policy_report]"]
    lines.extend(
        value for key, value in settings.items() if key != setting_key
    )
    lines.append(setting)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_org_config(path)


def test_policy_report_config_rejects_duplicate_aliases(tmp_path: Path) -> None:
    path = tmp_path / "org.toml"
    path.write_text(
        """org_name = 'test'
[policy_report]
source_repo = 'org/tools'
source_repository = 'org/tools'
workflow = 'repo-policy-sync.yml'
artifact = 'report'
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source repository"):
        load_org_config(path)


def test_fetch_policy_report_downloads_latest_completed_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    report_path = tmp_path / "report.json"
    config = PolicyReportConfig(
        source_repo="org/tools",
        workflow="repo-policy-sync.yml",
        artifact="policy-report",
        filename="report.json",
        cache_path=report_path,
        definitions_path="policies",
        descriptions_cache_path=tmp_path / "descriptions.json",
    )
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("nested/report.json", json.dumps(_report_payload()))

    responses = {
        "/actions/workflows/repo-policy-sync.yml/runs": {
            "workflow_runs": [
                {"id": 10, "status": "completed", "created_at": "2026-08-29"},
                {"id": 11, "status": "completed", "created_at": "2026-08-30"},
            ]
        },
        "/actions/runs/11/artifacts": {
            "artifacts": [{"id": 22, "name": "policy-report", "expired": False}]
        },
    }
    definition = {
        "encoding": "base64",
        "content": base64.b64encode(
            b"description: |\n  Use Bazel 8.6.0 or newer.\n"
        ).decode(),
    }

    def fake_urlopen(request: Any, *, timeout: int) -> Any:
        del timeout
        url = request.full_url
        if url.endswith("/zip"):
            payload = archive_buffer.getvalue()
        elif url.endswith("/policy.yml"):
            payload = json.dumps(definition).encode()
        else:
            path = url.split("/repos/org/tools", 1)[1].split("?", 1)[0]
            payload = json.dumps(responses[path]).encode()
        return _FakeResponse(payload)

    assert fetch_policy_report(config, urlopen=fake_urlopen) is True
    assert json.loads(report_path.read_text(encoding="utf-8")) == _report_payload()
    assert json.loads(config.descriptions_cache_path.read_text(encoding="utf-8")) == {
        "minimum-bazel-version": "Use Bazel 8.6.0 or newer."
    }


def test_fetch_policy_report_is_non_fatal_when_no_run_exists(tmp_path: Path) -> None:
    config = PolicyReportConfig(
        source_repo="org/tools",
        workflow="repo-policy-sync.yml",
        artifact="policy-report",
        cache_path=tmp_path / "report.json",
    )

    def fake_urlopen(request: Any, *, timeout: int) -> Any:
        del request, timeout
        return _FakeResponse(b'{"workflow_runs": []}')

    assert fetch_policy_report(config, token="secret", urlopen=fake_urlopen) is False
    assert not config.cache_path.exists()


def test_policy_report_parser_handles_missing_malformed_and_unsupported_reports(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.json"
    assert load_policy_sync_report(missing) is None

    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json", encoding="utf-8")
    assert load_policy_sync_report(malformed) is None

    assert parse_policy_sync_report({"schema_version": 1}) is None
    assert parse_policy_sync_report(_report_payload()) is not None

    descriptions = tmp_path / "descriptions.json"
    descriptions.write_text(
        json.dumps({"minimum-bazel-version": "Use Bazel 8.6.0 or newer."}),
        encoding="utf-8",
    )
    assert load_policy_descriptions(descriptions) == {
        "minimum-bazel-version": "Use Bazel 8.6.0 or newer."
    }


def test_policy_sync_tab_renders_details_links_and_escaped_values() -> None:
    report = PolicySyncReport(
        schema_version=2,
        summary=PolicySyncSummary(repositories=1, evaluations=1, drifted=1),
        outcomes=(
            PolicySyncOutcome(
                policy_id="<policy>",
                repository="<repo>",
                applicable="yes",
                status="changes-required",
                changes=(PolicySyncChange("<path>", "<description>", "<rationale>"),),
                pull_request_url="https://github.com/org/repo/pull/1",
                policy_pr_status="open",
                warnings=("<warning>",),
                error="<error>",
            ),
        ),
    )
    page = render_index_page(
        _minimal_snapshot(),
        report,
        policy_descriptions={"<policy>": "<policy description>"},
    )

    assert 'data-tab="policy-sync">Policy Sync</button>' in page
    assert "Compliance Matrix" in page
    assert "Changes, Warnings, Errors &amp; Pull Requests" not in page
    assert 'class="policy-matrix-cell"' in page
    assert 'tabindex="0"' in page
    assert "&lt;repo&gt;" in page
    assert "&lt;description&gt;" in page
    assert "&lt;warning&gt;" in page
    assert "&lt;error&gt;" in page
    assert 'data-tooltip="&lt;policy description&gt;"' in page
    assert "<description>" not in page
    assert "<details" not in page
    assert 'href="https://github.com/org/repo/pull/1"' in page
    assert 'href="repo-policy-sync-report.json"' in page


def test_render_details_discovers_configured_report_and_publishes_raw_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    write_snapshot(_minimal_snapshot(), tmp_path / "snapshot.json")
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache" / "report.json").write_text(
        json.dumps(_report_payload()), encoding="utf-8"
    )
    (tmp_path / ".cache" / "descriptions.json").write_text(
        json.dumps({"minimum-bazel-version": "Use Bazel 8.6.0 or newer."}),
        encoding="utf-8",
    )
    (tmp_path / "org.toml").write_text(
        """org_name = 'eclipse-score'
[policy_report]
source_repo = 'org/tools'
workflow = 'repo-policy-sync.yml'
artifact = 'policy-report'
filename = 'report.json'
cache_path = '.cache/report.json'
descriptions_cache_path = '.cache/descriptions.json'
""",
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
    index = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "2" in index
    assert 'data-tooltip="Use Bazel 8.6.0 or newer."' in index
    assert 'href="report.json"' in index
    assert (tmp_path / "site" / "report.json").exists()


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload
