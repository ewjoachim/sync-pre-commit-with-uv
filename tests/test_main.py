from __future__ import annotations

import argparse
import pathlib

import pytest

from sync_pre_commit_with_uv import __main__ as main
from sync_pre_commit_with_uv import exceptions


def test_existing_path(tmp_path: pathlib.Path):
    """Test the existing_path function."""
    file = tmp_path / "test.txt"
    file.touch()

    assert main.existing_path(str(file)) == file


def test_existing_path__not_existing(tmp_path: pathlib.Path):
    with pytest.raises(argparse.ArgumentTypeError):
        main.existing_path(str(tmp_path / "non_existing.txt"))


def test_default_path(tmp_path: pathlib.Path):
    """Test the default_path function."""
    file_1 = tmp_path / "test.txt"
    file_1.touch()
    file_2 = tmp_path / "test2.txt"
    file_2.touch()

    assert main.default_path(sibling=file_1, name="test2.txt") == file_2


def test_default_path__not_default(tmp_path: pathlib.Path):
    file_1 = tmp_path / "test.txt"
    file_1.touch()
    with pytest.raises(exceptions.PathDoesNotExist):
        main.default_path(sibling=file_1, name="test2.txt")


def test_get_parser(tmp_path: pathlib.Path):
    """Test the get_parser function."""
    parser = main.get_parser()

    (tmp_path / "pyproject.toml").touch()
    (tmp_path / ".pre-commit-config.yaml").touch()
    (tmp_path / "uv.lock").touch()

    # Check default values
    args = parser.parse_args([])
    assert args.pyproject_config == pathlib.Path("pyproject.toml")
    assert args.pre_commit_config is None
    assert args.uv_lock is None

    # Check that files argument is optional
    assert args.files == []


def test_parse_cli(tmp_path: pathlib.Path):
    pyproject_config = tmp_path / "pyproject.toml"
    pyproject_config.touch()
    pre_commit_config = tmp_path / ".pre-commit-config.yaml"
    pre_commit_config.touch()
    uv_lock = tmp_path / "uv.lock"
    uv_lock.touch()

    args = main.parse_cli(
        [
            "--pyproject-config",
            str(tmp_path / "pyproject.toml"),
        ]
    )
    assert args == main.CliArgs(
        pyproject_config=pyproject_config,
        pre_commit_config=pre_commit_config,
        uv_lock=uv_lock,
    )


def test_parse_cli__all_provided(tmp_path: pathlib.Path):
    pyproject_config = tmp_path / "pyproject.toml"
    pyproject_config.touch()
    pre_commit_config = tmp_path / ".pre-commit-config.yaml"
    pre_commit_config.touch()
    uv_lock = tmp_path / "uv.lock"
    uv_lock.touch()

    args = main.parse_cli(
        [
            "--pyproject-config",
            str(tmp_path / "pyproject.toml"),
            "--pre-commit-config",
            str(tmp_path / ".pre-commit-config.yaml"),
            "--uv-lock",
            str(tmp_path / "uv.lock"),
        ]
    )
    assert args == main.CliArgs(
        pyproject_config=pyproject_config,
        pre_commit_config=pre_commit_config,
        uv_lock=uv_lock,
    )


def test_cli__error(tmp_path: pathlib.Path):
    """Test the CLI error handling."""
    pyproject_config = tmp_path / "pyproject.toml"
    pyproject_config.touch()
    with pytest.raises(SystemExit):
        main.cli(["--pyproject-config", str(pyproject_config)])
