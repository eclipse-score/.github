#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contributors for the last N days (grouped + per-repo) -> GitHub-flavored Markdown.

- Python: 3.13+
- Requires: PyGithub (pip install PyGithub)
- Auth: set GITHUB_TOKEN or GH_TOKEN

Group "infrastructure" is defined inline. Other repos are auto-discovered from the org.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from github import Github
from github.Commit import Commit
from github.NamedUser import NamedUser
from github.Repository import Repository

# -------- Config --------
ORG_NAME = "eclipse-score"

# TODO: move to external file, e.g. yaml, for more teams & repos
INFRA_REPOS: list[str] = [
    "tooling",
    "docs-as-code",
    "bazel_registry",
]

INCLUDE_BOTS = False
SKIP_MERGE_COMMITS = True
SKIP_FORKS = True
SKIP_ARCHIVED = True

OUT_MD = Path("contributors_last6m_groups.md")
# ------------------------


@dataclass(frozen=True)
class AuthorKey:
    user_id: int
    login: str
    display: str  # "@login" or "Name <email>"


def is_bot(user: NamedUser | None, login: str) -> bool:
    if user and getattr(user, "type", "") == "Bot":
        return True
    return login.endswith("[bot]")


def author_key_from_commit(c: Commit) -> AuthorKey | None:
    """Prefer stable GitHub user; fall back to raw author identity. None => filtered (e.g., bot)."""
    user = c.author  # may be None for unlinked emails
    if user:
        login = user.login or ""
        if not INCLUDE_BOTS and is_bot(user, login):
            return None
        return AuthorKey(user.id or 0, login, f"@{login}" if login else (user.name or "User"))

    # Anonymous: use raw commit author fields
    raw = c.commit.author  # type: ignore[attr-defined]
    name = (getattr(raw, "name", None) or "Anonymous").strip()
    email = (getattr(raw, "email", None) or "").strip()
    disp = f"{name} <{email}>" if email else name
    if not INCLUDE_BOTS and disp.endswith("[bot]"):
        return None
    return AuthorKey(0, "", disp)


def iter_commits(repo: Repository, since: datetime, until: datetime):
    return repo.get_commits(since=since, until=until)


def collect_repo_counts(repo: Repository, since: datetime, until: datetime) -> dict[AuthorKey, int]:
    counts: dict[AuthorKey, int] = defaultdict(int)
    for commit in iter_commits(repo, since, until):
        if SKIP_MERGE_COMMITS and (commit.commit.message or "").startswith("Merge"):
            continue
        key = author_key_from_commit(commit)
        if key is None:
            continue
        counts[key] += 1
    return counts


def fetch_org_repos(g: Github, org_name: string) -> list[Repository]:  # type: ignore[name-defined]
    """Use `string` as an example of avoided typing import; in 3.13 this will evaluate at runtime.
    If you prefer strictness, change to `str` and remove the ignore."""
    org = g.get_organization(org_name)
    repos = list(org.get_repos())  # PyGithub handles pagination
    out: list[Repository] = []
    for r in repos:
        if SKIP_FORKS and r.fork:
            continue
        if SKIP_ARCHIVED and r.archived:
            continue
        out.append(r)
    return out


def md_table_rows(items: list[tuple[AuthorKey, int]]) -> list[str]:
    rows = ["| # | Contributor | Commits |", "|---:|---|---:|"]
    for i, (k, n) in enumerate(items, start=1):
        rows.append(f"| {i} | {k.display} | {n} |")
    return rows


def write_markdown(
    out_path: Path,
    days: int,
    generated_at: datetime,
    infra_per_repo: dict[str, dict[AuthorKey, int]],
    others_per_repo: dict[str, dict[AuthorKey, int]],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Infra roll-up
    infra_group: dict[AuthorKey, int] = defaultdict(int)
    for counts in infra_per_repo.values():
        for k, v in counts.items():
            infra_group[k] += v

    lines: list[str] = []
    lines.append(f"# Contributors in the last ~{days} days (grouped + per repo)\n")
    lines.append(f"_Generated: {generated_at.strftime('%Y-%m-%d %H:%M %Z')}_\n")
    lines.append(f"- Org: `{ORG_NAME}`")
    lines.append(f"- Bots: **{'included' if INCLUDE_BOTS else 'excluded'}**")
    lines.append(f"- Merge commits: **{'skipped' if SKIP_MERGE_COMMITS else 'included'}**")
    lines.append(f"- Forks: **{'skipped' if SKIP_FORKS else 'included'}**, Archived: **{'skipped' if SKIP_ARCHIVED else 'included'}**\n")

    # Group summary
    lines.append("## Group: infrastructure (roll-up)")
    if infra_group:
        sorted_infra = sorted(infra_group.items(), key=lambda kv: (-kv[1], kv[0].display.lower()))
        lines.extend(md_table_rows(sorted_infra))
        lines.append("")
    else:
        lines.append("_No commits in the infrastructure group for this window._\n")

    # Infra per-repo
    lines.append("### Infrastructure – per repository")
    for full in sorted(infra_per_repo.keys()):
        counts = infra_per_repo[full]
        lines.append(f"#### {full}")
        if counts:
            rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].display.lower()))
            lines.extend(md_table_rows(rows))
            lines.append("")
        else:
            lines.append("_No commits in this period._\n")

    # Others per-repo
    lines.append("## Other org repositories – per repository")
    if not others_per_repo:
        lines.append("_No other repositories found (after filters)._")
    else:
        for full in sorted(others_per_repo.keys()):
            counts = others_per_repo[full]
            lines.append(f"### {full}")
            if counts:
                rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].display.lower()))
                lines.extend(md_table_rows(rows))
                lines.append("")
            else:
                lines.append("_No commits in this period._\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect contributors for last N days (grouped + per-repo) to GFM.")
    ap.add_argument("--days", type=int, default=180, help="Lookback window (default: 180).")
    ap.add_argument("--org", type=str, default=ORG_NAME, help="GitHub org to scan (default: eclipse-score).")
    ap.add_argument("--out", type=str, default=str(OUT_MD), help="Output Markdown path.")
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        sys.exit("Set GITHUB_TOKEN or GH_TOKEN")
    g = Github(login_or_token=token, per_page=100)

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.days)

    # Discover org repos
    org_repos = fetch_org_repos(g, args.org)

    # Build maps for quick lookup
    by_name: dict[str, Repository] = {r.name: r for r in org_repos}
    by_full: dict[str, Repository] = {r.full_name: r for r in org_repos}

    infra_per_repo: dict[str, dict[AuthorKey, int]] = {}
    others_per_repo: dict[str, dict[AuthorKey, int]] = {}

    # Collect infrastructure group first
    for name in INFRA_REPOS:
        if "/" in name:
            r = by_full.get(name)
            full = name
        else:
            r = by_name.get(name)
            full = f"{args.org}/{name}"
        if not r:
            # maybe filtered out or not in org; try direct fetch
            try:
                r = g.get_repo(full)
            except Exception:
                print(f"[warn] Repo not found or filtered: {full}", file=sys.stderr)
                continue
        counts = collect_repo_counts(r, since, now)
        infra_per_repo[r.full_name] = counts
        print(f"Scanned {r.full_name}: {sum(counts.values())} commits", file=sys.stderr)

    # Collect all other org repos
    infra_names = {r.split("/", 1)[-1] for r in INFRA_REPOS} | set(infra_per_repo.keys())
    for r in org_repos:
        if r.name in infra_names or r.full_name in infra_per_repo:
            continue
        counts = collect_repo_counts(r, since, now)
        others_per_repo[r.full_name] = counts
        print(f"Scanned {r.full_name}: {sum(counts.values())} commits", file=sys.stderr)

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(OUT_MD, args.days, now, infra_per_repo, others_per_repo)
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
