from __future__ import annotations


def escape_markdown_table_cell(text: str) -> str:
    normalized = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return normalized.replace("|", r"\|")
