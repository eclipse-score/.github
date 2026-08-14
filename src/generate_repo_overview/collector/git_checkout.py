from __future__ import annotations

import base64
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def sync_repository_checkout(
    *,
    clone_url: str,
    default_branch: str,
    github_token: str | None,
    checkout_path: Path,
) -> Path | None:
    authenticated_url = build_authenticated_clone_url(clone_url, github_token)
    checkout_path.parent.mkdir(parents=True, exist_ok=True)

    if update_existing_checkout(
        checkout_path,
        default_branch,
        github_token=github_token,
    ):
        return checkout_path

    if not clone_fresh_checkout(
        authenticated_url=authenticated_url,
        default_branch=default_branch,
        checkout_path=checkout_path,
        github_token=github_token,
    ):
        return None

    return checkout_path


def update_existing_checkout(
    checkout_path: Path,
    default_branch: str,
    *,
    github_token: str | None = None,
) -> bool:
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
        ],
        github_token=github_token,
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
    github_token: str | None = None,
) -> bool:
    shutil.rmtree(checkout_path, ignore_errors=True)
    return run_git_command(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--single-branch",
            "--no-tags",
            "--branch",
            default_branch,
            authenticated_url,
            str(checkout_path),
        ],
        github_token=github_token,
    )


def get_checkout_head_sha(checkout_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(checkout_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def get_checkout_head_date(checkout_path: Path) -> str | None:
    timestamp = _run_git_for_text(
        ["git", "-C", str(checkout_path), "log", "-1", "--format=%cI"]
    )
    return timestamp[:10] if timestamp else None


def remote_repository_has_refs(
    clone_url: str,
    *,
    github_token: str | None,
) -> bool | None:
    try:
        result = subprocess.run(
            ["git", "ls-remote", clone_url],
            check=False,
            capture_output=True,
            text=True,
            env=_git_environment(github_token),
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())


def fetch_repository_ref(
    checkout_path: Path,
    ref: str,
    *,
    github_token: str | None,
) -> str | None:
    if not run_git_command(
        [
            "git",
            "-C",
            str(checkout_path),
            "fetch",
            "--depth",
            "1",
            "--no-tags",
            "origin",
            ref,
        ],
        github_token=github_token,
    ):
        return None
    return _run_git_for_text(
        ["git", "-C", str(checkout_path), "rev-parse", "FETCH_HEAD"]
    )


def list_repository_paths(checkout_path: Path) -> set[str]:
    output = _run_git_for_text(["git", "-C", str(checkout_path), "ls-files", "-z"])
    if output is None:
        return {
            path.relative_to(checkout_path).as_posix()
            for path in checkout_path.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(checkout_path).parts
        }
    return {path for path in output.split("\0") if path}


def read_repository_text(checkout_path: Path, path: str) -> str | None:
    try:
        return (checkout_path / path).read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return None


def read_repository_text_at_ref(
    checkout_path: Path,
    ref: str,
    path: str,
) -> str | None:
    return _run_git_for_text(["git", "-C", str(checkout_path), "show", f"{ref}:{path}"])


def run_git_command(
    command: list[str],
    *,
    github_token: str | None = None,
) -> bool:
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=_git_environment(github_token),
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def build_authenticated_clone_url(clone_url: str, github_token: str | None) -> str:
    return clone_url


def _run_git_for_text(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _git_environment(github_token: str | None) -> dict[str, str]:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    if github_token is None:
        return environment

    credential = base64.b64encode(f"x-access-token:{github_token}".encode()).decode()
    environment.update(
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credential}",
        }
    )
    return environment
