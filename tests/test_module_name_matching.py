from generate_repo_overview.module_name_matching import (
    NameMatch,
    classify_repository_name_match,
)


def test_exact_match_normalizes_score_and_inc_prefixes() -> None:
    assert (
        classify_repository_name_match(
            "inc_daal",
            ("score_inc_daal",),
        )
        == NameMatch.EXACT
    )


def test_close_match_accepts_orchestrator_and_orchestration() -> None:
    assert (
        classify_repository_name_match(
            "orchestrator",
            ("Orchestration",),
        )
        == NameMatch.CLOSE
    )


def test_different_match_flags_unrelated_name() -> None:
    assert (
        classify_repository_name_match(
            "inc_security_crypto",
            ("score_crypto",),
        )
        == NameMatch.DIFFERENT
    )
