from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import pytest

from generate_repo_overview.models import GroupingLevel, TrackedDep, WorkflowSignal
from generate_repo_overview.org_config import (
    OrgConfig,
    OverviewConfig,
    load_org_config,
)

MINIMAL_ORG = "[organizations.test]\nrun_repository_tools = false\n"


def _load(tmp_path: Path, content: str) -> OverviewConfig:
    toml_path = tmp_path / "org.toml"
    toml_path.write_text(dedent(content), encoding="utf-8")
    return load_org_config(toml_path)


class TestOrgConfigDefaults:
    def test_org_name_is_required(self) -> None:
        with pytest.raises(TypeError):
            OrgConfig()  # type: ignore[call-arg]

    def test_signal_defaults_are_empty(self) -> None:
        config = OrgConfig(org_name="my-org")
        assert config.repo_include_patterns == ()
        assert config.tracked_deps == ()
        assert config.workflow_signals == ()
        assert config.reference_integration_repo == ""
        assert config.registry_repo == ""
        assert config.grouping_levels == ()

    def test_repository_tools_are_disabled_by_default(self) -> None:
        assert OrgConfig(org_name="my-org").run_repository_tools is False


class TestLoadOrgConfig:
    def test_load_minimal_toml(self, tmp_path: Path) -> None:
        config = _load(tmp_path, MINIMAL_ORG)
        assert config.primary == OrgConfig(org_name="test")
        assert config.organizations == (config.primary,)
        assert config.platform_repos == ()
        assert not config.policy_report.enabled

    @pytest.mark.parametrize("content", ["", "[organizations]\n"])
    def test_an_organization_is_required(self, tmp_path: Path, content: str) -> None:
        with pytest.raises(ValueError, match=r"at least one \[organizations"):
            _load(tmp_path, content)

    def test_load_full_toml(self, tmp_path: Path) -> None:
        config = _load(
            tmp_path,
            """\
            [organizations.other-org]
            run_repository_tools = true
            repo_include_patterns = ["lib-*", "tool-*"]
            reference_integration_repo = "other-org/ref-int"
            registry_repo = "other-org/my_registry"

            [[organizations.other-org.grouping_levels]]
            property = "team"
            default = "Unassigned"

            [[organizations.other-org.tracked_deps]]
            repo = "other-org/my-docs"
            module_name = "my_docs_dep"

            [[organizations.other-org.workflow_signals]]
            label = "Nightly"
            reference = "other-org/my-cicd/.github/workflows/nightly.yml@"

            [signals]
            platform_repos = [
              "other-org/public-platform",
              "other-org/private-platform",
            ]
            """,
        )
        tracked_deps = (
            TrackedDep(repo="other-org/my-docs", module_name="my_docs_dep"),
        )
        workflow_signals = (
            WorkflowSignal(
                label="Nightly",
                reference="other-org/my-cicd/.github/workflows/nightly.yml@",
            ),
        )
        assert config.primary == OrgConfig(
            org_name="other-org",
            repo_include_patterns=("lib-*", "tool-*"),
            tracked_deps=tracked_deps,
            workflow_signals=workflow_signals,
            reference_integration_repo="other-org/ref-int",
            registry_repo="other-org/my_registry",
            grouping_levels=(GroupingLevel(property="team", default="Unassigned"),),
            run_repository_tools=True,
        )
        assert config.platform_repos == (
            "other-org/public-platform",
            "other-org/private-platform",
        )


class TestMultipleOrganizations:
    def test_organizations_keep_their_order_and_do_not_inherit(
        self, tmp_path: Path
    ) -> None:
        config = _load(
            tmp_path,
            """\
            [organizations.second]
            run_repository_tools = false
            repo_include_patterns = ["b-*"]

            [organizations.first]
            run_repository_tools = true
            registry_repo = "first/registry"
            reference_integration_repo = "first/integration"
            grouping_levels = [{ property = "team", default = "Unassigned" }]

            [[organizations.first.workflow_signals]]
            label = "Nightly"
            reference = "first/cicd/.github/workflows/nightly.yml@"
            """,
        )
        second, first = config.organizations
        assert config.primary is second
        assert second.org_name == "second"
        assert second.run_repository_tools is False
        assert second.registry_repo == ""
        assert second.reference_integration_repo == ""
        assert second.grouping_levels == ()
        assert second.workflow_signals == ()
        assert first.run_repository_tools is True
        assert [signal.label for signal in first.workflow_signals] == ["Nightly"]

    def test_run_repository_tools_is_required(self, tmp_path: Path) -> None:
        with pytest.raises(
            ValueError, match=r"organizations\.second\.run_repository_tools is required"
        ):
            _load(
                tmp_path,
                MINIMAL_ORG + "[organizations.second]\nregistry_repo = 'a/b'\n",
            )

    def test_run_repository_tools_must_be_a_boolean(self, tmp_path: Path) -> None:
        with pytest.raises(
            ValueError, match="run_repository_tools must be true or false"
        ):
            _load(tmp_path, '[organizations.test]\nrun_repository_tools = "no"\n')

    def test_duplicate_organization_differing_in_case_errors(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="Duplicate GitHub organization"):
            _load(
                tmp_path,
                MINIMAL_ORG + "[organizations.Test]\nrun_repository_tools = false\n",
            )

    def test_invalid_organization_name_errors(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid GitHub organization name"):
            _load(
                tmp_path, '[organizations."not valid"]\nrun_repository_tools = false\n'
            )


class TestRepoMatchesFilter:
    def test_empty_patterns_matches_all(self) -> None:
        config = OrgConfig(org_name="x", repo_include_patterns=())
        assert config.repo_matches_filter("anything") is True
        assert config.repo_matches_filter("lib-foo") is True

    def test_glob_patterns(self) -> None:
        config = OrgConfig(org_name="x", repo_include_patterns=("lib-*", "tool-*"))
        assert config.repo_matches_filter("lib-a") is True
        assert config.repo_matches_filter("lib-module-a") is True
        assert config.repo_matches_filter("tool-cli") is True
        assert config.repo_matches_filter("other-repo") is False
        assert config.repo_matches_filter("my-lib-thing") is False

    def test_exact_name_pattern(self) -> None:
        config = OrgConfig(org_name="x", repo_include_patterns=("specific-repo",))
        assert config.repo_matches_filter("specific-repo") is True
        assert config.repo_matches_filter("specific-repo-2") is False

    def test_question_mark_glob(self) -> None:
        config = OrgConfig(org_name="x", repo_include_patterns=("lib-?",))
        assert config.repo_matches_filter("lib-a") is True
        assert config.repo_matches_filter("lib-ab") is False


class TestConfigValidation:
    def test_repo_include_patterns_string_instead_of_list_errors(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="Expected a list"):
            _load(tmp_path, MINIMAL_ORG + 'repo_include_patterns = "single-pattern"\n')

    def test_whitespace_stripped_from_patterns(self, tmp_path: Path) -> None:
        config = _load(
            tmp_path,
            MINIMAL_ORG + 'repo_include_patterns = [" lib-* ", "  tool-*  "]\n',
        )
        assert config.primary.repo_include_patterns == ("lib-*", "tool-*")

    @pytest.mark.parametrize("key", ["reference_integration_repo", "registry_repo"])
    @pytest.mark.parametrize(
        "value",
        [
            "",
            "just-a-name",
            "../etc",
            "/tmp/registry",
            "C:/registry",
            "org/../registry",
        ],
    )
    def test_repository_setting_must_be_an_org_repo_path(
        self, tmp_path: Path, key: str, value: str
    ) -> None:
        with pytest.raises(ValueError, match=rf"organizations\.test\.{key} .*org/repo"):
            _load(tmp_path, MINIMAL_ORG + f"{key} = '{value}'\n")

    def test_backslash_registry_path_errors(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="org/repo"):
            _load(tmp_path, MINIMAL_ORG + r"registry_repo = 'org\..\registry'" + "\n")

    def test_platform_repo_without_slash_errors(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="org/repo"):
            _load(
                tmp_path,
                MINIMAL_ORG
                + '[signals]\nplatform_repos = ["valid/public", "invalid"]\n',
            )

    def test_malformed_tracked_deps_entries_are_skipped(self, tmp_path: Path) -> None:
        config = _load(
            tmp_path,
            MINIMAL_ORG
            + dedent("""\
                [[organizations.test.tracked_deps]]
                repo = "org/valid"
                module_name = "valid_mod"
                [[organizations.test.tracked_deps]]
                repo = "org/missing-module"
                [[organizations.test.tracked_deps]]
                module_name = "missing-repo"
            """),
        )
        assert config.primary.tracked_deps == (TrackedDep("org/valid", "valid_mod"),)

    def test_malformed_workflow_signals_entries_are_skipped(
        self, tmp_path: Path
    ) -> None:
        config = _load(
            tmp_path,
            MINIMAL_ORG
            + dedent("""\
                [[organizations.test.workflow_signals]]
                label = "Valid"
                reference = "org/ref@"
                [[organizations.test.workflow_signals]]
                label = "Missing Reference"
                [[organizations.test.workflow_signals]]
                reference = "org/no-label@"
            """),
        )
        assert config.primary.workflow_signals == (WorkflowSignal("Valid", "org/ref@"),)


def _grouping(tmp_path: Path, levels: str) -> tuple[GroupingLevel, ...]:
    return _load(tmp_path, MINIMAL_ORG + dedent(levels)).primary.grouping_levels


class TestGroupingLevels:
    def test_absent_grouping_levels_return_empty_tuple(self, tmp_path: Path) -> None:
        assert _grouping(tmp_path, "") == ()

    def test_empty_levels_list_returns_empty_tuple(self, tmp_path: Path) -> None:
        assert _grouping(tmp_path, "grouping_levels = []\n") == ()

    def test_one_grouping_level(self, tmp_path: Path) -> None:
        levels = """\
            [[organizations.test.grouping_levels]]
            property = "area"
            default = "Unknown"
        """
        assert _grouping(tmp_path, levels) == (
            GroupingLevel(property="area", default="Unknown"),
        )

    def test_two_grouping_levels_eclipse_score_style(self, tmp_path: Path) -> None:
        levels = """\
            [[organizations.test.grouping_levels]]
            property = "category"
            default = "Uncategorized"

            [[organizations.test.grouping_levels]]
            property = "subcategory"
            default = "General"
        """
        assert _grouping(tmp_path, levels) == (
            GroupingLevel(property="category", default="Uncategorized"),
            GroupingLevel(property="subcategory", default="General"),
        )

    def test_three_grouping_levels_raises(self, tmp_path: Path) -> None:
        levels = """\
            grouping_levels = [
              { property = "a", default = "A" },
              { property = "b", default = "B" },
              { property = "c", default = "C" },
            ]
        """
        with pytest.raises(ValueError, match="at most 2"):
            _grouping(tmp_path, levels)

    @pytest.mark.parametrize(
        "invalid_entry",
        [
            '{ default = "Fallback" }',
            '{ property = "area" }',
            '{ property = "area", default = "   " }',
        ],
    )
    def test_incomplete_entry_is_skipped(
        self, tmp_path: Path, invalid_entry: str
    ) -> None:
        levels = (
            f"grouping_levels = [{invalid_entry}, "
            '{ property = "team", default = "Common" }]\n'
        )
        assert _grouping(tmp_path, levels) == (
            GroupingLevel(property="team", default="Common"),
        )

    def test_property_and_default_are_stripped(self, tmp_path: Path) -> None:
        levels = (
            'grouping_levels = [{ property = "  area  ", default = "  Unknown  " }]\n'
        )
        assert _grouping(tmp_path, levels) == (
            GroupingLevel(property="area", default="Unknown"),
        )

    def test_grouping_levels_as_scalar_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="grouping_levels must be a list"):
            _grouping(tmp_path, 'grouping_levels = "not-a-list"\n')


class TestReferenceIntegrationOrgName:
    def test_parse_github_remote_with_custom_org(self) -> None:
        from generate_repo_overview.collector.reference_integration import (
            parse_github_remote_repository_name,
        )

        result = parse_github_remote_repository_name(
            "https://github.com/other-org/my-repo.git",
            org_name="other-org",
        )
        assert result == "my-repo"

    def test_parse_github_remote_rejects_wrong_org(self) -> None:
        from generate_repo_overview.collector.reference_integration import (
            parse_github_remote_repository_name,
        )

        result = parse_github_remote_repository_name(
            "https://github.com/other-org/my-repo.git",
            org_name="wrong-org",
        )
        assert result is None


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (
            'repo_include_pattern = ["a"]',
            "Unknown top-level setting(s): repo_include_pattern",
        ),
        (
            '[signals]\nregistry = "org/registry"',
            "Unknown signals setting(s): registry",
        ),
        (
            '[signals]\nregistry_repo = "org/registry"',
            "Unknown signals setting(s): registry_repo",
        ),
        (
            '[[signals.workflow_signals]]\nlabel = "Daily"\nreference = "org/ref@"',
            "Unknown signals setting(s): workflow_signals",
        ),
        (
            "[organizations.second]\nrun_repo_tools = true",
            "Unknown organizations.second setting(s): run_repo_tools",
        ),
    ],
)
def test_misspelled_setting_is_rejected(
    tmp_path: Path, config: str, message: str
) -> None:
    # Top-level keys must precede the first table.
    content = (
        f"{config}\n{MINIMAL_ORG}"
        if config.startswith("repo_")
        else f"{MINIMAL_ORG}{config}\n"
    )
    with pytest.raises(ValueError, match=re.escape(message)):
        _load(tmp_path, content)


def test_previous_config_format_is_rejected(tmp_path: Path) -> None:
    content = """\
        org_name = "test"

        [[grouping.levels]]
        property = "team"
        default = "Unassigned"
    """
    with pytest.raises(
        ValueError, match=re.escape("Unknown top-level setting(s): grouping, org_name")
    ):
        _load(tmp_path, content)


def test_shipped_org_config_is_accepted() -> None:
    # Tests run in an empty working directory, so load the file explicitly.
    config = load_org_config(Path(__file__).parents[1] / "org_config.toml")

    assert [org.org_name for org in config.organizations] == ["eclipse-score"]
    assert config.primary.run_repository_tools is True
    assert config.primary.registry_repo == "eclipse-score/bazel_registry"
    assert config.primary.workflow_signals
    assert config.policy_report.enabled
