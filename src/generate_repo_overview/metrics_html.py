from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ._html_detail import render_detail_page
from ._html_index import render_index_page
from .metrics_report import get_latest_tracked_dep_version, get_max_bazel_version
from .policy_sync import POLICY_REPORT_FILENAME, render_policy_sync_report_json

if TYPE_CHECKING:
    from .models import RepoSnapshot
    from .policy_sync import PolicySyncReport

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_all_pages(
    snapshot: RepoSnapshot,
    policy_report: PolicySyncReport | None = None,
    *,
    policy_report_json: str | None = None,
    policy_report_filename: str = POLICY_REPORT_FILENAME,
) -> dict[str, str]:
    repos = sorted(snapshot.repos, key=lambda r: r.name.casefold())
    max_bazel = get_max_bazel_version(list(repos))
    latest_dep_versions = {
        dep.module_name: get_latest_tracked_dep_version(list(repos), dep)
        for dep in snapshot.tracked_deps
    }

    pages: dict[str, str] = {
        "index.html": render_index_page(
            snapshot,
            policy_report,
            raw_json_available=policy_report_json is not None,
            raw_json_filename=policy_report_filename,
        ),
        "data.json": json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n",
        "bazel_logo.svg": (_TEMPLATE_DIR / "bazel_logo.svg").read_text(encoding="utf-8"),
    }
    if policy_report_json is None and policy_report is not None:
        policy_report_json = render_policy_sync_report_json(policy_report)
    if policy_report_json is not None:
        pages[policy_report_filename] = policy_report_json
    for entry in repos:
        pages[f"{entry.name}/index.html"] = render_detail_page(
            entry, snapshot, max_bazel, latest_dep_versions
        )
    return pages
