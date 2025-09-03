#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contributors report (last N days) driven by groups.yaml, using GitHub Insights (/stats/contributors).
- Highlights CODEOWNERS per repo (uses the rule whose pattern is exactly '*').
- Falls back to GitHub CLI (`gh auth token`) if no env token is present.
- Adds logging + JSON disk caching for Insights stats and CODEOWNERS.

Python: 3.13+
Deps : PyGithub, PyYAML
Auth : GITHUB_TOKEN / GH_TOKEN env vars, or `gh auth login`
Output: GitHub-flavored Markdown
"""

import argparse
import json
import logging as log
import os
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml  # PyYAML
from github import Github, GithubException
from github.ContentFile import ContentFile
from github.NamedUser import NamedUser
from github.Repository import Repository

# ---------- Defaults (overridable by YAML & CLI) ----------
DEFAULT_ORG = "eclipse-score"
DEFAULT_INCLUDE_BOTS = False
DEFAULT_SKIP_FORKS = True
DEFAULT_SKIP_ARCHIVED = True
DEFAULT_CONFIG_FILE = "contrib_report.yaml"
DEFAULT_OUTPUT_MD = "contributors_groups.md"
DEFAULT_CACHE_DIR = ".cache"
DEFAULT_CACHE_TTL_SECONDS = 24 * 3600
# ---------------------------------------------------------


@dataclass(frozen=True)
class Row:
    login: str   # "@login" or "anonymous"
    uid: int     # 0 for anonymous
    commits: int


def configure_logging(level: str) -> None:
    level_map = {
        "DEBUG": log.DEBUG,
        "INFO": log.INFO,
        "WARN": log.WARN,
        "WARNING": log.WARN,
        "ERROR": log.ERROR,
    }
    log.basicConfig(
        level=level_map.get(level.upper(), log.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_github_token() -> str | None:
    """Find a token via env or gh CLI."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        log.debug("Using token from environment.")
        return token
    try:
        out = subprocess.check_output(
            ["gh", "auth", "token"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out:
            log.debug("Using token from `gh auth token`.")
            return out
    except (FileNotFoundError, subprocess.CalledProcessError):
        log.debug("`gh` CLI not available or not authenticated.")
    return None


def is_bot(user: NamedUser | None, login: str) -> bool:
    if user and getattr(user, "type", "") == "Bot":
        return True
    return login.endswith("[bot]")


def load_config_yaml(path: Path) -> tuple[str, bool, bool, bool, dict[str, list[str]]] | None:
    if not path.exists():
        return None

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    org = str(data.get("org") or DEFAULT_ORG)

    opts = data.get("options") or {}
    include_bots = bool(opts.get("include_bots", DEFAULT_INCLUDE_BOTS))
    skip_forks = bool(opts.get("skip_forks", DEFAULT_SKIP_FORKS))
    skip_archived = bool(opts.get("skip_archived", DEFAULT_SKIP_ARCHIVED))

    groups_raw = data.get("groups") or {}
    groups: dict[str, list[str]] = {}
    for gname, repos in groups_raw.items():
        if not isinstance(repos, list):
            continue
        groups[gname] = [str(r).strip() for r in repos if str(r).strip()]

    return org, include_bots, skip_forks, skip_archived, groups


def fetch_org_repos(g: Github, org_name: str, skip_forks: bool, skip_archived: bool) -> list[Repository]:
    org = g.get_organization(org_name)
    repos = list(org.get_repos())
    out: list[Repository] = []
    for r in repos:
        if skip_forks and r.fork:
            continue
        if skip_archived and r.archived:
            continue
        out.append(r)
    log.info("Discovered %d repos in org %s (%d before filters).", len(out), org_name, len(repos))
    return out


# -------------------- CACHING HELPERS --------------------

def cache_path(cache_dir: Path, namespace: str, id: str) -> Path:
    safe_ns = namespace.replace("/", "__")
    safe_id = id.replace("/", "__")
    return cache_dir / safe_ns / f"{safe_id}.json"


def cache_load(cache_dir: Path, namespace: str, id: str, ttl_seconds: int) -> str | None:
    """Loads certain data identified by id, stored under a namespace from the config."""

    path = cache_path(cache_dir, namespace, id)
    if not path.exists():
        return None
    # TODO: can we use mtime? ctime? encode inside file?
    age = time.time() - path.stat().st_mtime
    if age > ttl_seconds:
        path.unlink(missing_ok=True)
        log.debug("Cache expired: %s / %s (age %.0fs > %ss). File cleaned up.", namespace, id, age, ttl_seconds)
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    log.debug("Cache hit: %s -> %s", path, type(data))
    return data


def cache_save(cache_dir: Path, namespace: str, id: str, payload: dict[object, object] | str):
    path = cache_path(cache_dir, namespace, id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, dict):
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        data = payload
    path.write_text(data, encoding="utf-8")
    log.debug("Cache saved: %s", path)


# ----------------- CODEOWNERS (with cache) ----------------

def cacheable(id: str, ttl_seconds: int):
    """
    Decorator to cache function results based on namespace (repo.full_name).
    The decorated function must accept (repo: Repository, cache_dir: Path, *args, **kwargs).
    """
    def decorator(func):
        def wrapper(repo: Repository, cache_dir: Path, *args, **kwargs):
            namespace = repo.full_name
            if cached := cache_load(cache_dir, namespace, id, ttl_seconds):
                return cached
            result = func(repo, cache_dir, *args, **kwargs)
            cache_save(cache_dir, namespace, id, result)
            return result
        return wrapper
    return decorator

@cacheable("codeowners", ttl_seconds=DEFAULT_CACHE_TTL_SECONDS)
def get_codeowner_file(repo: Repository, cache_dir: Path) -> str | None:
    candidates = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]
    for path in candidates:
        try:
            file = repo.get_contents(path)
            if isinstance(file, ContentFile):
                log.debug("Found CODEOWNERS at %s:%s", repo.full_name, path)
                return file.content
        except GithubException as e:
            if getattr(e, "status", None) != 404:
                raise
    return None

def get_codeowners(repo: Repository, cache_dir: Path) -> list[str] | None:
    """
    Return owners from the CODEOWNERS rule whose pattern is exactly '*'.
    Returns None if no file or no '*' rule. Last '*' rule wins.
    """
    codeowners_file = get_codeowner_file(repo, cache_dir)
    if not codeowners_file:
        return None

    for line in codeowners_file.splitlines():
        line = line.partition("#")[0].strip()
        if not line:
            continue
        parts = line.split()
        if parts and parts[0] == "*":
            return parts[1:]

    return None


# ------------- INSIGHTS (/stats/contributors) + cache -------------

@cacheable("stats", ttl_seconds=DEFAULT_CACHE_TTL_SECONDS)
def fetch_insights_stats(
    repo: Repository,
    poll_seconds: int,
    cache_dir: Path | None,
    ttl_seconds: int,
    use_cache: bool,
) -> tuple[list[dict], bool]:
    """
    Returns (normalized_stats, pending).
    normalized_stats: list of dicts: { "user": {"login": str|None, "id": int|None, "type": str|None}, "weeks": [{"w": int, "c": int}] }
    pending=True means GitHub returned 202 and we didn't wait long enough.
    """
    deadline = time.monotonic() + max(0, poll_seconds)
    while True:
        stats = repo.get_stats_contributors()  # None => 202 computing
        if stats is not None:
            break
        if time.monotonic() >= deadline:
            log.info("Insights pending for %s (202).", repo.full_name)
            return ([], True)
        time.sleep(5)

    # Normalize to JSON-serializable
    norm: list[dict] = []
    for s in stats:
        user = None
        if s.author:
            user = {
                "login": s.author.login or None,
                "id": s.author.id or None,
                "type": getattr(s.author, "type", None),
            }
        weeks = [{"w": int(w.w), "c": int(w.c or 0)} for w in s.weeks]
        norm.append({"user": user, "weeks": weeks})

    return norm, False


def sum_last_ndays_from_norm_stats(
    norm_stats: list[dict],
    days: int,
    include_bots: bool,
) -> list[Row]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows: list[Row] = []

    for s in norm_stats:
        u = s.get("user")
        if u is not None:
            login = u.get("login") or ""
            uid = int(u.get("id") or 0)
            utype = u.get("type") or ""
            if not include_bots and (utype == "Bot" or login.endswith("[bot]")):
                continue
            who = f"@{login}" if login else "user"
        else:
            who = "anonymous"
            uid = 0

        commits = 0
        for w in s.get("weeks", []):
            week_start = datetime.fromtimestamp(int(w.get("w", 0)), tz=timezone.utc)
            if week_start >= cutoff:
                commits += int(w.get("c", 0))

        if commits > 0:
            rows.append(Row(who, uid, commits))

    rows.sort(key=lambda r: (-r.commits, r.login.lower()))
    return rows


# ----------------------- MARKDOWN RENDER -----------------------

def render_markdown(
    out_path: Path,
    days: int,
    generated_at: datetime,
    org: str,
    include_bots: bool,
    skip_forks: bool,
    skip_archived: bool,
    grouped_rows: dict[str, dict[str, tuple[list[Row], list[str] | None]]],  # group -> repo_full -> (rows, owners)
    others_rows: dict[str, tuple[list[Row], list[str] | None]],
    pending: list[str],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# Contributors in the last ~{days} days (Insights API)\n")
    lines.append(f"_Generated: {generated_at.strftime('%Y-%m-%d %H:%M %Z')}_\n")
    lines.append(f"- Org: `{org}`")
    lines.append(f"- Source: `/stats/contributors` (weekly buckets)")
    lines.append(f"- Bots: **{'included' if include_bots else 'excluded'}**")
    lines.append(f"- Forks: **{'skipped' if skip_forks else 'included'}**, Archived: **{'skipped' if skip_archived else 'included'}**\n")

    if pending:
        lines.append("> ⚠️ Insights still computing for:")
        for name in sorted(pending):
            lines.append(f"> - {name}")
        lines.append("")

    # Each group: roll-up + per-repo
    for gname in sorted(grouped_rows.keys()):
        per_repo = grouped_rows[gname]

        # Roll-up
        rollup: dict[str, int] = defaultdict(int)
        for rows, _owners in per_repo.values():
            for r in rows:
                rollup[r.login] += r.commits
        roll = sorted(rollup.items(), key=lambda kv: (-kv[1], kv[0].lower()))

        lines.append(f"## Group: {gname} (roll-up)")
        if roll:
            lines.append("| # | Contributor | Commits |")
            lines.append("|---:|---|---:|")
            for i, (login, commits) in enumerate(roll, start=1):
                lines.append(f"| {i} | {login} | {commits} |")
            lines.append("")
        else:
            lines.append("_No commits for this group in the selected window._\n")

        # Per-repo
        lines.append(f"### {gname} – per repository")
        for repo_full in sorted(per_repo.keys()):
            rows, owners = per_repo[repo_full]
            lines.append(f"#### {repo_full}")
            if owners:
                lines.append(f"**CODEOWNERS** (`*`): {' '.join(owners)}")
            else:
                lines.append("**CODEOWNERS**: _none or file missing_")
            if rows:
                lines.append("")
                lines.append("| # | Contributor | Commits |")
                lines.append("|---:|---|---:|")
                for i, r in enumerate(rows, start=1):
                    lines.append(f"| {i} | {r.login} | {r.commits} |")
                lines.append("")
            else:
                lines.append("\n_No commits in this period (or stats pending)._ \n")

    # Others (ungrouped)
    lines.append("## Others – ungrouped repositories")
    if not others_rows:
        lines.append("_No ungrouped repositories (after filters)._ \n")
    else:
        for repo_full in sorted(others_rows.keys()):
            rows, owners = others_rows[repo_full]
            lines.append(f"### {repo_full}")
            if owners:
                lines.append(f"**CODEOWNERS** (`*`): {' '.join(owners)}")
            else:
                lines.append("**CODEOWNERS**: _none or file missing_")
            if rows:
                lines.append("")
                lines.append("| # | Contributor | Commits |")
                lines.append("|---:|---|---:|")
                for i, r in enumerate(rows, start=1):
                    lines.append(f"| {i} | {r.login} | {r.commits} |")
                lines.append("")
            else:
                lines.append("\n_No commits in this period (or stats pending)._ \n")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ----------------------------- MAIN -----------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Contributors report driven by groups.yaml (Insights API) with caching + logging.")
    ap.add_argument("--days", type=int, default=180, help="Lookback window (default: 180).")
    ap.add_argument("--groups", type=str, default=DEFAULT_CONFIG_FILE, help="Path to groups YAML.")
    ap.add_argument("--out", type=str, default=DEFAULT_OUTPUT_MD, help="Output Markdown path.")
    ap.add_argument("--poll-seconds", type=int, default=0,
                    help="If >0, poll for up to N seconds when stats are computing (HTTP 202).")
    ap.add_argument("--log-level", type=str, default="INFO", help="Logging level: DEBUG, INFO, WARN, ERROR.")
    ap.add_argument("--cache-dir", type=str, default=DEFAULT_CACHE_DIR, help="Cache directory.")
    ap.add_argument("--cache-ttl-seconds", type=int, default=DEFAULT_CACHE_TTL_SECONDS, help="Cache TTL in seconds.")
    ap.add_argument("--no-cache", action="store_true", help="Disable reading/writing cache.")
    args = ap.parse_args()

    configure_logging(args.log_level)

    token = get_github_token()
    if not token:
        sys.exit("❌ No GitHub token found. Set GITHUB_TOKEN/GH_TOKEN or run `gh auth login`.")
    g = Github(login_or_token=token, per_page=100)

    groups_path = Path(args.groups)
    org, include_bots, skip_forks, skip_archived, groups_cfg = load_config_yaml(groups_path)
    log.info("Org=%s, include_bots=%s, skip_forks=%s, skip_archived=%s", org, include_bots, skip_forks, skip_archived)

    now = datetime.now(timezone.utc)

    # Discover org repos (for short names + "others")
    org_repos = fetch_org_repos(g, org, skip_forks, skip_archived)
    by_name: dict[str, Repository] = {r.name: r for r in org_repos}
    by_full: dict[str, Repository] = {r.full_name: r for r in org_repos}

    grouped_rows: dict[str, dict[str, tuple[list[Row], list[str] | None]]] = {}
    seen_full_names: set[str] = set()
    pending: list[str] = []

    cache_dir = Path(args.cache_dir) if not args.no_cache else None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    # Groups
    for gname, repo_specs in groups_cfg.items():
        per_repo: dict[str, tuple[list[Row], list[str] | None]] = {}
        for spec in repo_specs:
            if "/" in spec:
                r = by_full.get(spec)
                full = spec
            else:
                r = by_name.get(spec)
                full = f"{org}/{spec}"
            if not r:
                try:
                    r = g.get_repo(full)
                except Exception:
                    log.warning("Repo not found or filtered: %s", full)
                    continue

            # Stats (cached)
            norm_stats, is_pending = fetch_insights_stats(
                r, args.poll_seconds, cache_dir, args.cache_ttl_seconds, not args.no_cache
            )
            if is_pending:
                pending.append(r.full_name)
            rows = sum_last_ndays_from_norm_stats(norm_stats, args.days, include_bots)

            # CODEOWNERS (cached)
            owners = get_codeowners(r, cache_dir, args.cache_ttl_seconds, not args.no_cache)

            per_repo[r.full_name] = (rows, owners)
            seen_full_names.add(r.full_name)
            log.info("Repo %-40s commits=%-6d %s", r.full_name, sum(rr.commits for rr in rows),
                     "(pending)" if is_pending else "")
        grouped_rows[gname] = per_repo

    # Others
    others_rows: dict[str, tuple[list[Row], list[str] | None]] = {}
    for r in org_repos:
        if r.full_name in seen_full_names:
            continue

        norm_stats, is_pending = fetch_insights_stats(
            r, args.poll_seconds, cache_dir, args.cache_ttl_seconds, not args.no_cache
        )
        if is_pending:
            pending.append(r.full_name)
        rows = sum_last_ndays_from_norm_stats(norm_stats, args.days, include_bots)
        owners = get_codeowners(r, cache_dir, args.cache_ttl_seconds, not args.no_cache)
        others_rows[r.full_name] = (rows, owners)
        log.info("Repo %-40s commits=%-6d %s", r.full_name, sum(rr.commits for rr in rows),
                 "(pending)" if is_pending else "")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    render_markdown(out_path, args.days, now, org, include_bots, skip_forks, skip_archived, grouped_rows, others_rows, pending)
    log.info("Wrote %s", out_path)
