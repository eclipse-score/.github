from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import RepoEntry


def escape_markdown_table_cell(text: str) -> str:
    normalized = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return normalized.replace("|", r"\|")


def render_repository_link(entry: RepoEntry, primary_org: str) -> str:
    entry.validate_path_segments(primary_org)
    owner = entry.owner or primary_org
    label = (
        entry.full_name if owner.casefold() != primary_org.casefold() else entry.name
    )
    return f"[{label}](https://github.com/{owner}/{entry.name})"
