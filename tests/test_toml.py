from __future__ import annotations

import pathlib

from sync_pre_commit_with_uv import toml


def test_toml(tmp_path: pathlib.Path) -> None:
    """Test the toml module."""
    file = tmp_path / "test.toml"
    file.write_text(
        """
        [tool.sync_pre_commit_with_uv]
        pre_commit_config = "tests/fixtures/pre-commit-config.yaml"
        uv_config = "tests/fixtures/uv_config.yaml"
        """,
        encoding="utf-8",
    )
    assert toml.read_toml(file) == {
        "tool": {
            "sync_pre_commit_with_uv": {
                "pre_commit_config": "tests/fixtures/pre-commit-config.yaml",
                "uv_config": "tests/fixtures/uv_config.yaml",
            }
        }
    }
