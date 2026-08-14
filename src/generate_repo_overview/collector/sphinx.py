from __future__ import annotations

import re
from typing import TYPE_CHECKING

from generate_repo_overview.models import SphinxItem

if TYPE_CHECKING:
    from collections.abc import Iterator

_LITERAL_DIRECTIVE = re.compile(
    r"^\.\.\s+(?:code|code-block|sourcecode|parsed-literal)::(?:\s|$)"
)


def parse_sphinx_directives(
    text: str | None,
    directive: str,
    *,
    path: str,
    source_repo: str = "",
) -> tuple[SphinxItem, ...]:
    if not text:
        return ()
    pattern = re.compile(rf"^\s*\.\.\s+{re.escape(directive)}::\s*(.*?)\s*$")
    lines = text.splitlines()
    result: list[SphinxItem] = []
    for index, line in _iter_rst_content_lines(lines):
        match = pattern.match(line)
        if match is None:
            continue
        title = match.group(1).strip()
        identifier = ""
        for option_line in lines[index + 1 :]:
            stripped = option_line.strip()
            if not stripped:
                if identifier:
                    break
                continue
            if stripped.startswith(":id:"):
                identifier = stripped.removeprefix(":id:").strip()
                continue
            if not stripped.startswith(":"):
                break
        result.append(
            SphinxItem(
                path=path,
                title=title,
                identifier=identifier,
                source_repo=source_repo,
            )
        )
    return tuple(result)


def _iter_rst_content_lines(lines: list[str]) -> Iterator[tuple[int, str]]:
    pending_literal_indent: int | None = None
    literal_indent: int | None = None
    for index, line in enumerate(lines):
        expanded_line = line.expandtabs(8)
        stripped = expanded_line.strip()
        if not stripped:
            continue
        indent = len(expanded_line) - len(expanded_line.lstrip())

        if literal_indent is not None:
            if indent > literal_indent:
                continue
            literal_indent = None
        if pending_literal_indent is not None:
            if indent > pending_literal_indent:
                literal_indent = pending_literal_indent
                continue
            pending_literal_indent = None
        if _LITERAL_DIRECTIVE.match(stripped) or (
            not stripped.startswith(".. ") and stripped.endswith("::")
        ):
            pending_literal_indent = indent
            continue
        yield index, line
