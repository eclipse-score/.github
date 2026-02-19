# *******************************************************************************
# Copyright (c) 2025 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

#!/usr/bin/env python3
"""
Update the Descriptions and Status column (✅ / 🕓 / 💤) in profile/README.md.
"""

import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

ORG = "eclipse-score"
NOW = datetime.now(timezone.utc)

OTTERDOG_CONFIG_URL = (
    "https://raw.githubusercontent.com/eclipse-score/.eclipsefdn/main/otterdog/eclipse-score.jsonnet"
)


def _parse_otterdog_alias_map(jsonnet_text: str) -> dict[str, str]:
    """Extract alias -> canonical repo name mappings from the Otterdog jsonnet.

    The config contains repo declarations like:
      newScoreRepo("nlohmann_json", true) { aliases: ["inc_nlohmann_json"], ... }

    This function uses a lightweight brace-depth scan (not a full Jsonnet parser)
    so we don't need additional dependencies.
    """

    repo_start = re.compile(
        r"(?:orgs\.newRepo|newScoreRepo|newModuleRepo|newInfrastructureTeamRepo)\(\s*(['\"])"
        r"(?P<name>[^'\"]+)\1"
    )
    aliases_field = re.compile(r"\baliases\+?\s*:\s*\[(?P<body>.*?)\]", re.DOTALL)
    quoted_string = re.compile(r"['\"]([^'\"]+)['\"]")

    alias_map: dict[str, str] = {}

    current_repo: str | None = None
    brace_depth = 0
    started = False
    block_lines: list[str] = []

    for line in jsonnet_text.splitlines():
        if current_repo is None:
            m = repo_start.search(line)
            if not m:
                continue
            current_repo = m.group("name")
            block_lines = [line]
            brace_depth = line.count("{") - line.count("}")
            started = "{" in line
            if started and brace_depth == 0:
                block_text = "\n".join(block_lines)
                am = aliases_field.search(block_text)
                if am:
                    for alias in quoted_string.findall(am.group("body")):
                        alias_map[alias] = current_repo
                current_repo = None
                block_lines = []
                started = False
            continue

        block_lines.append(line)
        if "{" in line or "}" in line:
            started = started or ("{" in line)
            brace_depth += line.count("{") - line.count("}")

        if started and brace_depth == 0:
            block_text = "\n".join(block_lines)
            am = aliases_field.search(block_text)
            if am:
                for alias in quoted_string.findall(am.group("body")):
                    alias_map[alias] = current_repo
            current_repo = None
            block_lines = []
            started = False

    return alias_map


def load_otterdog_alias_map(url: str = OTTERDOG_CONFIG_URL) -> dict[str, str]:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "text/plain, */*",
                "User-Agent": "eclipse-score-readme-updater",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            status_code = getattr(resp, "status", 200)
            body = resp.read().decode("utf-8")
    except Exception as exc:
        print(f"⚠️ Could not fetch Otterdog config for aliases: {exc}")
        return {}

    if status_code != 200:
        print(
            "⚠️ Could not fetch Otterdog config for aliases: "
            f"HTTP {status_code}"
        )
        return {}

    try:
        return _parse_otterdog_alias_map(body)
    except Exception as exc:
        print(f"⚠️ Could not parse Otterdog config for aliases: {exc}")
        return {}


def calc_state(pushed_at: datetime) -> str:
    # TODO: use e.g. last 3 commits, instead of only one last commit

    DAYS_STALE = 30
    DAYS_OBSOLETE = 90

    cut1 = NOW - timedelta(days=DAYS_STALE)
    cut2 = NOW - timedelta(days=DAYS_OBSOLETE)

    if pushed_at <= cut2:
        return "💤 obsolete"
    if pushed_at <= cut1:
        return "🕓 stale"
    return "✅ active"


def get_last_commit(repo):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}

    query = """
    query($owner: String!, $name: String!, $branchCount: Int!) {
      repository(owner: $owner, name: $name) {
        refs(refPrefix: "refs/heads/", first: $branchCount, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
          nodes {
            name
            target {
              ... on Commit {
                committedDate
                author {
                  user {
                    login
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    variables = {
        "owner": repo.owner.login,
        "name": repo.name,
        "branchCount": 100
    }

    url = "https://api.github.com/graphql"
    payload = {"query": query, "variables": variables}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            **headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status_code = getattr(resp, "status", 200)
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"⚠️ GraphQL request failed for {repo.name}: {exc}")
        return None

    if status_code != 200:
        print(f"⚠️ GraphQL request failed for {repo.name}: {status_code} {body}")
        return None

    data = json.loads(body)
    if "errors" in data:
        print(f"⚠️ GraphQL error for {repo.name}: {data['errors']}")
        return None

    branches = data.get("data", {}).get("repository", {}).get("refs", {}).get("nodes", [])
    latest = None

    for branch in branches:
        commit = branch.get("target")
        if not commit:
            continue
        author = commit.get("author", {}).get("user")
        if not author:
            continue
        login = author.get("login", "").lower()
        if login.endswith("[bot]") or "bot" in login:
            continue
        dt = datetime.fromisoformat(commit["committedDate"].replace("Z", "+00:00"))
        if latest is None or dt > latest:
            latest = dt

    return latest


@dataclass
class RepoData:
    name: str
    description: str
    status: str


def query_github_org_for_repo_data(gh, org: str):
    # TODO: pagination once we hit 100 repos
    repos = gh.get_organization(org).get_repos()
    data = {}

    for repo in repos:
        print(f"🔍 Checking {repo.name} ...")
        last_commit = get_last_commit(repo)
        if last_commit:
            status = calc_state(last_commit)
        else:
            status = "💤 obsolete"

        data[repo.name] = RepoData(
            name=repo.name,
            description=repo.description or "(no description)",
            status=status,
        )
        time.sleep(1)  # small sleep to avoid hitting rate limits
    return data



def update_line(
    line: str,
    repo_data: dict[str, RepoData],
    alias_map: dict[str, str],
    missing_repos_in_api: set[str],
    renamed_repos: list[tuple[str, str]],
) -> str:
    # Change lines starting with "| [repo]"
    m = re.match(r"^\| \[([^\]]+)\]", line)
    if not m:
        return line

    repo: str = m.group(1).strip()

    # Fast path: exact match.
    data = repo_data.pop(repo, None)
    resolved_repo = repo

    # Handle renames/aliases (old name in README -> canonical name in API),
    # sourced from the Otterdog configuration.
    if data is None and repo in alias_map:
        canonical = alias_map[repo]
        data = repo_data.pop(canonical, None)
        if data is not None:
            resolved_repo = canonical
            renamed_repos.append((repo, canonical))
    if data is None:
        # Keep the original line unchanged if the repo isn't visible via the API
        # (e.g., private repo or insufficient token permissions).
        missing_repos_in_api.add(repo)
        return line

    # If we resolved via rename, update the displayed repo name/link to the
    # current name (the one we matched in repo_data).
    return f"| [{resolved_repo}](https://github.com/eclipse-score/{resolved_repo}) | {data.description} | {data.status} |"


def update_readme(
    original: str,
    repo_data: dict[str, RepoData],
    alias_map: dict[str, str],
) -> str:
    missing_repos_in_api: set[str] = set()
    renamed_repos: list[tuple[str, str]] = []
    updated_lines: list[str] = []

    for line in original.splitlines():
        updated_lines.append(
            update_line(line, repo_data, alias_map, missing_repos_in_api, renamed_repos)
        )

    if renamed_repos:
        rename_list = ", ".join(
            f"{old}→{new}" for old, new in sorted(renamed_repos, key=lambda x: x[0].lower())
        )
        print(f"ℹ️ Applied repo renames: {rename_list}")

    if missing_repos_in_api:
        missing_list = ", ".join(sorted(missing_repos_in_api, key=str.lower))
        print(
            "⚠️ Repos referenced in profile/README.md but not returned by the GitHub API "
            f"({len(missing_repos_in_api)}): {missing_list}"
        )

    return "\n".join(updated_lines)


if __name__ == "__main__":
    alias_map = load_otterdog_alias_map()
    if alias_map:
        print(f"ℹ️ Loaded {len(alias_map)} repo aliases from Otterdog")

    try:
        from github import Github
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency 'PyGithub'. Install requirements.txt before running this script."
        ) from exc

    gh = Github(os.getenv("GITHUB_TOKEN"))

    repo_data = query_github_org_for_repo_data(gh, ORG)

    MD_FILE = pathlib.Path("profile/README.md")

    original = MD_FILE.read_text()
    updated = update_readme(original, repo_data, alias_map)

    for repo in repo_data:
        print(
            f"Extra repo (not listed in profile/README.md): {repo} - {repo_data[repo].description} ({repo_data[repo].status})"
        )

    if updated != original:
        _ = MD_FILE.write_text(updated)
        print("README updated.")
    else:
        print("No update.")
