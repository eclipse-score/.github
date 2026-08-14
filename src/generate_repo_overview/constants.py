from __future__ import annotations

import os
from pathlib import Path

DEFAULT_OUTPUT = Path("profile/README.md")
DEFAULT_METRICS_HTML_OUTPUT = Path("_site")
DEFAULT_CACHE = Path(".cache/repo_overview.json")
DEFAULT_TOKEN_ENV = "GITHUB_TOKEN"


def default_repository_checkout_cache() -> Path:
    """Return the shared SCORE checkout cache without creating it."""

    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    cache_home = Path(xdg_cache_home) if xdg_cache_home else Path.home() / ".cache"
    return cache_home / "repo-cache"


DEFAULT_REPOSITORY_CHECKOUTS = default_repository_checkout_cache()
