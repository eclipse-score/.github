from __future__ import annotations

import json
from typing import TYPE_CHECKING

from generate_repo_overview.console import print_status
from generate_repo_overview.models import RepoSnapshot

if TYPE_CHECKING:
    from pathlib import Path


def load_snapshot(path: Path) -> RepoSnapshot:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Snapshot file must contain a JSON object.")
    return RepoSnapshot.from_dict(raw)


def load_snapshot_if_present(path: Path) -> RepoSnapshot | None:
    if not path.exists():
        print_status(f"Snapshot cache {path} is absent; collecting without cached data")
        return None
    try:
        snapshot = load_snapshot(path)
        print_status(
            f"Loaded snapshot cache {path} with {len(snapshot.repos)} repositories"
        )
        return snapshot
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print_status(
            f"Cannot reuse snapshot cache {path}; collecting without cached data: {exc}"
        )
        return None


def write_snapshot(snapshot: RepoSnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot.to_dict()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
