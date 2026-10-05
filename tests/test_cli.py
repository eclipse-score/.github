from types import SimpleNamespace

import pytest

import generate_repo_overview.cli as cli


def test_main_without_command_prints_help_and_succeeds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main([])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Quick start:" in captured.out
    assert "collect" in captured.out
    assert "render-overview" in captured.out
    assert "render-details" in captured.out
    assert "generate-profile-readme" not in captured.out
    assert "generate-metrics" not in captured.out
    assert captured.err == ""


def test_collect_help_does_not_expose_refresh_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["collect", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "--refresh" not in captured.out
    assert "--deep" not in captured.out
    assert "--clean" in captured.out


def test_render_overview_help_shows_expected_args(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["render-overview", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "--input" in captured.out
    assert "--output" in captured.out
    assert "--template" in captured.out
    assert "--config" in captured.out
    assert "--dry-run" not in captured.out
    assert "--refresh" not in captured.out


def test_render_details_help_shows_expected_args(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["render-details", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "--input" in captured.out
    assert "--output" in captured.out
    assert "--dry-run" not in captured.out
    assert "--refresh" not in captured.out


@pytest.mark.parametrize(
    ("fetch_result", "expected_exit_code"),
    [(False, 1), (True, 0)],
)
def test_fetch_policy_report_exit_status_matches_fetch_result(
    monkeypatch: pytest.MonkeyPatch,
    fetch_result: bool,
    expected_exit_code: int,
) -> None:
    policy_report = object()
    monkeypatch.setattr(
        cli,
        "load_org_config",
        lambda _path: SimpleNamespace(policy_report=policy_report),
    )

    def fake_fetch_policy_report(
        report_config: object,
        *,
        token_env: str,
        status_prefix: str,
    ) -> bool:
        assert report_config is policy_report
        assert token_env == "GITHUB_TOKEN"
        assert status_prefix == "repo-overview"
        return fetch_result

    monkeypatch.setattr(cli, "fetch_policy_report", fake_fetch_policy_report)

    assert cli.main(["fetch-policy-report"]) == expected_exit_code
