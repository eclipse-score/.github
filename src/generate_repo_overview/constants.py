from __future__ import annotations

from pathlib import Path

from repo_cache import default_cache_directory

DEFAULT_OUTPUT = Path("profile/README.md")
DEFAULT_METRICS_HTML_OUTPUT = Path("_site")
DEFAULT_CACHE = Path(".cache/repo_overview.json")
DEFAULT_ORG_CONFIG = Path("org_config.toml")
DEFAULT_TOKEN_ENV = "GITHUB_TOKEN"

DEFAULT_POLICY_REPORT_FILENAME = "repo-policy-sync-report.json"
DEFAULT_POLICY_REPORT_CACHE = Path(".cache/repo-policy-sync-report.json")

DEFAULT_REPOSITORY_CHECKOUTS = default_cache_directory()
