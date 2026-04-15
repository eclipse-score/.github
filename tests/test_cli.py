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
    assert "render" in captured.out
    assert "generate-all" not in captured.out
    assert captured.err == ""


def test_collect_help_does_not_expose_refresh_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["collect", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "--refresh" not in captured.out


def test_render_help_does_not_expose_refresh_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["render", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "--refresh" not in captured.out
