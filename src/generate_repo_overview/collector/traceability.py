from __future__ import annotations

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, cast

from generate_repo_overview.console import print_status
from generate_repo_overview.models import TraceabilityTypeMetrics

if TYPE_CHECKING:
    from generate_repo_overview.models import RepoEntry

_METRICS_TIMEOUT_SECONDS = 10
_DAC_REPO_NAME = "docs-as-code"


def is_docs_as_code_repo(entry: RepoEntry) -> bool:
    return bool(entry.content.docs_as_code_version) or entry.name == _DAC_REPO_NAME


def fetch_traceability_metrics(
    org_name: str,
    repo_name: str,
) -> tuple[TraceabilityTypeMetrics, ...]:
    base = f"https://{org_name}.github.io/{repo_name}"
    for path in ("main/metrics.json", "pr-484/metrics.json"):
        try:
            with urllib.request.urlopen(
                f"{base}/{path}", timeout=_METRICS_TIMEOUT_SECONDS
            ) as resp:
                data = json.loads(resp.read())
            return _parse_metrics_by_type(data)
        except Exception:
            continue
    return ()


def _parse_metrics_by_type(data: Any) -> tuple[TraceabilityTypeMetrics, ...]:
    if not isinstance(data, dict):
        return ()
    metrics_by_type = data.get("metrics_by_type")
    if not isinstance(metrics_by_type, dict):
        return ()

    result: list[TraceabilityTypeMetrics] = []
    for type_key, type_data in cast("dict[str, Any]", metrics_by_type).items():
        if not isinstance(type_data, dict):
            continue
        req = type_data.get("requirements", {})
        tests = type_data.get("tests", {})
        result.append(
            TraceabilityTypeMetrics(
                type_name=type_key,
                req_total=_int(req.get("total")),
                req_with_code_link=_int(req.get("with_code_link")),
                req_with_test_link=_int(req.get("with_test_link")),
                req_fully_linked=_int(req.get("fully_linked")),
                tests_total=_int(tests.get("total")),
                tests_linked=_int(tests.get("linked_to_requirements")),
            )
        )
    return tuple(result)


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def fetch_all_traceability_metrics(
    org_name: str,
    repos: list[RepoEntry],
    *,
    status_prefix: str = "repo-overview",
) -> dict[str, tuple[TraceabilityTypeMetrics, ...]]:
    dac_repos = [r for r in repos if is_docs_as_code_repo(r)]
    if not dac_repos:
        return {}

    print_status(
        f"Fetching traceability metrics for {len(dac_repos)} docs-as-code repositories",
        prefix=status_prefix,
    )

    results: dict[str, tuple[TraceabilityTypeMetrics, ...]] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(dac_repos))) as executor:
        futures = {
            executor.submit(fetch_traceability_metrics, org_name, r.name): r.name
            for r in dac_repos
        }
        for future in as_completed(futures):
            repo_name = futures[future]
            results[repo_name] = future.result()

    loaded = sum(1 for v in results.values() if v)
    print_status(
        f"Loaded traceability metrics for {loaded}/{len(dac_repos)} repositories",
        prefix=status_prefix,
    )
    return results
