from __future__ import annotations

from typing import TYPE_CHECKING

from ._html_detail import render_detail_page
from ._html_index import render_index_page
from .metrics_report import get_latest_docs_as_code_release, get_max_bazel_version

if TYPE_CHECKING:
    from .models import RepoSnapshot


def render_metrics_html(snapshot: RepoSnapshot) -> str:
    return render_index_page(snapshot)


def render_all_pages(snapshot: RepoSnapshot) -> dict[str, str]:
    repos = sorted(snapshot.repos, key=lambda r: r.name.casefold())
    max_bazel = get_max_bazel_version(list(repos))
    latest_dac = get_latest_docs_as_code_release(list(repos))

    pages: dict[str, str] = {
        "index.html": render_index_page(snapshot),
    }
    for entry in repos:
        pages[f"{entry.name}/index.html"] = render_detail_page(
            entry, snapshot.org_name, snapshot, max_bazel, latest_dac
        )
    return pages
