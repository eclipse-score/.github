from types import SimpleNamespace

import pytest
from _pytest.monkeypatch import MonkeyPatch

import profile_readme_generator.generator as generator
from profile_readme_generator.generator import (
    RepoEntry,
    build_repo_entry,
    get_gh_auth_token,
    group_repositories,
    normalize_group_name,
    print_status,
    render_readme,
    resolve_github_token,
)


def test_normalize_group_name_uses_fallback_for_empty_values() -> None:
    assert normalize_group_name(None, "Fallback") == "Fallback"
    assert normalize_group_name("", "Fallback") == "Fallback"
    assert normalize_group_name([], "Fallback") == "Fallback"


def test_normalize_group_name_joins_multi_select_values() -> None:
    assert (
        normalize_group_name(["Tooling", "Automation"], "Fallback")
        == "Tooling, Automation"
    )


def test_group_repositories_sorts_everything_case_insensitively() -> None:
    repos = [
        RepoEntry("zeta", "desc", "infra", "beta"),
        RepoEntry("Alpha", "desc", "Apps", "alpha"),
        RepoEntry("beta", "desc", "apps", "Alpha"),
    ]

    grouped = group_repositories(repos)

    assert list(grouped) == ["Apps", "apps", "infra"]
    assert list(grouped["apps"]) == ["Alpha"]
    assert [entry.name for entry in grouped["apps"]["Alpha"]] == ["beta"]


def test_build_repo_entry_uses_custom_properties_and_description_fallback() -> None:
    entry = build_repo_entry(
        repository_name="tools",
        description=None,
        custom_properties={"category": "Infrastructure", "subcategory": None},
    )

    assert entry == RepoEntry(
        name="tools",
        description="(no description)",
        category="Infrastructure",
        subcategory="General",
    )


def test_render_readme_uses_simple_markdown_sections() -> None:
    template = """# Title

{{ repo_sections }}
"""

    markdown = render_readme(
        [
            RepoEntry("tools", "Tooling repo", "Infrastructure", "Tooling"),
            RepoEntry("score", "(no description)", "Modules", "Core"),
        ],
        template=template,
    )

    assert "# Title" in markdown
    assert "### Infrastructure" in markdown
    assert "#### Tooling" in markdown
    assert (
        "| [tools](https://github.com/eclipse-score/tools) | Tooling repo |" in markdown
    )
    assert markdown.endswith("\n")


def test_resolve_github_token_prefers_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_GITHUB_TOKEN", "env-token")
    monkeypatch.setattr(generator, "get_gh_auth_token", lambda: "gh-token")

    assert resolve_github_token("TEST_GITHUB_TOKEN") == "env-token"


def test_get_gh_auth_token_returns_trimmed_stdout(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        generator.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="gh-token\n"),
    )

    assert get_gh_auth_token() == "gh-token"


def test_get_gh_auth_token_returns_none_on_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    def raise_called_process_error(*args: object, **kwargs: object) -> None:
        raise generator.subprocess.CalledProcessError(1, ["gh", "auth", "token"])

    monkeypatch.setattr(generator.subprocess, "run", raise_called_process_error)

    assert get_gh_auth_token() is None


def test_print_status_writes_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    print_status("Loading repos")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == "[generate-profile-readme] Loading repos\n"
