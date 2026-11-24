from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_working_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep tests away from the developer's `org_config.toml` and `.cache`.

    Commands resolve their default paths against the working directory. A
    collected snapshot or policy report there would otherwise change results.
    """
    monkeypatch.chdir(tmp_path)
