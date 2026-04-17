from __future__ import annotations

import json
from pathlib import Path

from generate_repo_overview.models import RepoSnapshot


def load_snapshot(path: Path) -> RepoSnapshot:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Snapshot file must contain a JSON object.")
    return RepoSnapshot.from_dict(raw)


def load_snapshot_if_present(path: Path) -> RepoSnapshot | None:
    if not path.exists():
        return None
    try:
        return load_snapshot(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def write_snapshot(snapshot: RepoSnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot.to_dict()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
