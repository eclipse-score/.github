from __future__ import annotations

import re
from difflib import SequenceMatcher
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

MATCH_THRESHOLD = 0.84
MATCH_MARGIN = 0.08


class NameMatch(StrEnum):
    EXACT = "exact"
    CLOSE = "close"
    DIFFERENT = "different"


def classify_repository_name_match(
    repository_name: str,
    candidate_values: Iterable[str],
) -> NameMatch:
    score = alias_match_score(
        normalized_aliases(candidate_values),
        normalized_aliases((repository_name,)),
    )
    if score == 1.0:
        return NameMatch.EXACT
    if score >= MATCH_THRESHOLD:
        return NameMatch.CLOSE
    return NameMatch.DIFFERENT


def alias_match_score(left: set[str], right: set[str]) -> float:
    if left & right:
        return 1.0
    return max(
        (
            SequenceMatcher(None, left_alias, right_alias).ratio()
            for left_alias in left
            for right_alias in right
        ),
        default=0.0,
    )


def normalized_aliases(values: Iterable[str]) -> set[str]:
    aliases: set[str] = set()
    for value in values:
        normalized = normalize_name(value)
        if normalized:
            aliases.add(normalized)
        if "__" in value:
            suffix = normalize_name(value.split("__", maxsplit=1)[1])
            if suffix:
                aliases.add(suffix)
    return aliases


def normalize_name(value: str) -> str:
    normalized = value.casefold().strip()
    normalized = re.sub(r"^(?:(?:score|inc)[_-]+)+", "", normalized)
    normalized = normalized.replace("configuration", "config")
    normalized = normalized.replace("management", "mgmt")
    return re.sub(r"[^a-z0-9]+", "", normalized)
