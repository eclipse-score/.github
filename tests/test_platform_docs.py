from pathlib import Path

from generate_repo_overview.collector.platform_docs import (
    associate_sphinx_items,
    enrich_repositories_from_platform_docs,
    parse_sphinx_directive,
)
from generate_repo_overview.collector.sphinx import parse_sphinx_directives
from generate_repo_overview.models import DeepContentSignals, RepoEntry, SphinxItem


def test_parse_sphinx_directive_reads_title_and_id() -> None:
    assert parse_sphinx_directive(
        """
.. feat:: Logging
   :id: feat__logging
   :status: valid
""",
        "feat",
        path="docs/features/log_trace/logging",
    ) == SphinxItem(
        path="docs/features/log_trace/logging",
        title="Logging",
        identifier="feat__logging",
    )


def test_parse_sphinx_directives_ignores_literal_examples() -> None:
    text = """
Example:

.. code-block:: rst

   .. feat:: Template Feature
      :id: feat__template

Literal syntax::

   .. feat:: Another Template Feature

.. feat:: Logging
   :id: feat__logging
"""

    assert parse_sphinx_directives(
        text,
        "feat",
        path="docs/features/logging",
    ) == (
        SphinxItem(
            path="docs/features/logging",
            title="Logging",
            identifier="feat__logging",
        ),
    )


def test_enrich_repositories_discovers_and_associates_platform_docs(
    tmp_path: Path,
) -> None:
    contents = {
        "docs/features/log_trace/logging/index.rst": "Logging\n#######\n",
        "docs/features/log_trace/logging/architecture/index.rst": (
            ".. feat:: Logging\n   :id: feat__logging\n"
        ),
        "docs/features/orchestration/index.rst": "Orchestration\n#############\n",
        "docs/features/orchestration/architecture/index.rst": (
            ".. feat:: Orchestration\n   :id: feat__orchestration\n"
        ),
        "docs/features/configuration/config_mgmt/index.rst": (
            "Configuration Management\n########################\n"
        ),
        "docs/features/configuration/config_mgmt/architecture/index.rst": (
            ".. feat:: Configuration Management\n   :id: feat__config_mgmt\n"
        ),
        "docs/features/communication/some_ip_gateway/index.rst": (
            ".. document:: SOME/IP-Gateway\n   :id: doc__some_ip_gateway\n"
        ),
        "docs/features/communication/some_ip_gateway/architecture/index.rst": (
            "SOME/IP Gateway Architecture\n============================\n"
        ),
        "docs/modules/logging/docs/index.rst": (
            ".. mod:: Logging\n   :id: mod__logging\n"
        ),
        "docs/modules/orchestrator/docs/index.rst": (
            ".. mod:: Orchestrator\n   :id: mod__orchestrator\n"
        ),
    }

    _write_contents(tmp_path, contents)

    repos = [
        _module_repo("logging", "score_logging"),
        _module_repo("orchestrator", "score_orchestrator"),
        _module_repo("config_management", "score_config_management"),
        _module_repo("inc_someip_gateway", "score_someip_gateway"),
        _module_repo("communication", "score_communication"),
        RepoEntry("tools", "Tools", "Infrastructure", "General"),
    ]

    enriched = enrich_repositories_from_platform_docs(
        repos,
        checkout_path=tmp_path,
        source_repo="eclipse-score/score",
    )
    by_name = {entry.name: entry for entry in enriched}

    assert by_name["logging"].content.sphinx_features == (
        SphinxItem(
            path="docs/features/log_trace/logging",
            title="Logging",
            identifier="feat__logging",
            source_repo="eclipse-score/score",
        ),
    )
    assert by_name["logging"].content.sphinx_modules == (
        SphinxItem(
            path="docs/modules/logging",
            title="Logging",
            identifier="mod__logging",
            source_repo="eclipse-score/score",
        ),
    )
    assert by_name["orchestrator"].content.sphinx_features[0].identifier == (
        "feat__orchestration"
    )
    assert by_name["config_management"].content.sphinx_features[0].identifier == (
        "feat__config_mgmt"
    )
    assert by_name["inc_someip_gateway"].content.sphinx_features[0].identifier == (
        "doc__some_ip_gateway"
    )
    assert by_name["tools"].content.sphinx_features == ()


def test_enrichment_keeps_same_feature_from_public_and_private_sources(
    tmp_path: Path,
) -> None:
    contents = {
        "docs/features/logging/index.rst": "Logging\n#######\n",
        "docs/features/logging/architecture/index.rst": (
            ".. feat:: Logging\n   :id: feat__logging\n"
        ),
    }

    _write_contents(tmp_path, contents)

    repos = [_module_repo("logging", "score_logging")]
    public = enrich_repositories_from_platform_docs(
        repos,
        checkout_path=tmp_path,
        source_repo="eclipse-score/score",
    )
    combined = enrich_repositories_from_platform_docs(
        public,
        checkout_path=tmp_path,
        source_repo="example/private-features",
    )

    assert tuple(item.source_repo for item in combined[0].content.sphinx_features) == (
        "eclipse-score/score",
        "example/private-features",
    )


def test_enrichment_associates_platform_docs_without_modules_category(
    tmp_path: Path,
) -> None:
    contents = {
        "docs/features/logging/architecture/index.rst": (
            ".. feat:: Logging\n   :id: feat__logging\n"
        ),
    }
    _write_contents(tmp_path, contents)

    repo = RepoEntry(
        name="logging",
        description="logging",
        category="COM",
        subcategory="General",
        content=DeepContentSignals(bazel_module_name="score_logging"),
    )

    enriched = enrich_repositories_from_platform_docs(
        [repo],
        checkout_path=tmp_path,
        source_repo="eclipse-score/score",
    )

    assert enriched[0].content.sphinx_features == (
        SphinxItem(
            path="docs/features/logging",
            title="Logging",
            identifier="feat__logging",
            source_repo="eclipse-score/score",
        ),
    )


def test_association_skips_ambiguous_matches() -> None:
    item = SphinxItem(
        path="docs/features/logging",
        title="Logging",
        identifier="feat__logging",
    )
    repos = [
        _module_repo("logging", "score_logging"),
        _module_repo("inc_logging", "score_inc_logging"),
    ]

    assert associate_sphinx_items((item,), repos) == {}


def test_association_uses_sphinx_project_prefix() -> None:
    item = SphinxItem(
        path="docs/features/logging",
        title="Logging",
        identifier="feat__logging",
    )
    repo = _module_repo(
        "unrelated",
        "score_unrelated",
        sphinx_project_prefix="LOGGING_",
    )

    assert associate_sphinx_items((item,), [repo]) == {
        "unrelated": (item,),
    }


def test_association_skips_items_without_a_match() -> None:
    item = SphinxItem(
        path="docs/features/logging",
        title="Logging",
        identifier="feat__logging",
    )

    assert (
        associate_sphinx_items(
            (item,),
            [_module_repo("orchestrator", "score_orchestrator")],
        )
        == {}
    )


def _module_repo(
    name: str,
    bazel_module_name: str,
    *,
    sphinx_project_prefix: str | None = None,
) -> RepoEntry:
    return RepoEntry(
        name=name,
        description=name,
        category="Modules",
        subcategory="General",
        content=DeepContentSignals(
            bazel_module_name=bazel_module_name,
            sphinx_project_prefix=sphinx_project_prefix,
        ),
    )


def _write_contents(root: Path, contents: dict[str, str]) -> None:
    for relative_path, content in contents.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
