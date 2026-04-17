from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit


def sync_repository_checkout(
    *,
    clone_url: str,
    default_branch: str,
    github_token: str | None,
    checkout_path: Path,
) -> Path | None:
    authenticated_url = build_authenticated_clone_url(clone_url, github_token)
    checkout_path.parent.mkdir(parents=True, exist_ok=True)

    if update_existing_checkout(checkout_path, default_branch):
        return checkout_path

    if not clone_fresh_checkout(
        authenticated_url=authenticated_url,
        default_branch=default_branch,
        checkout_path=checkout_path,
    ):
        return None

    return checkout_path


def update_existing_checkout(checkout_path: Path, default_branch: str) -> bool:
    git_dir = checkout_path / ".git"
    if not git_dir.exists():
        return False

    fetch_ok = run_git_command(
        [
            "git",
            "-C",
            str(checkout_path),
            "fetch",
            "--depth",
            "1",
            "origin",
            default_branch,
        ]
    )
    checkout_ok = run_git_command(
        [
            "git",
            "-C",
            str(checkout_path),
            "checkout",
            "--force",
            "--detach",
            "FETCH_HEAD",
        ]
    )
    if not (fetch_ok and checkout_ok):
        return False

    run_git_command(["git", "-C", str(checkout_path), "clean", "-fdx"])
    return True


def clone_fresh_checkout(
    *,
    authenticated_url: str,
    default_branch: str,
    checkout_path: Path,
) -> bool:
    shutil.rmtree(checkout_path, ignore_errors=True)
    return run_git_command(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            default_branch,
            authenticated_url,
            str(checkout_path),
        ]
    )


def run_git_command(command: list[str]) -> bool:
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def build_authenticated_clone_url(clone_url: str, github_token: str | None) -> str:
    if github_token is None:
        return clone_url

    parsed = urlsplit(clone_url)
    auth = f"x-access-token:{quote(github_token, safe='')}"
    netloc = f"{auth}@{parsed.netloc}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
