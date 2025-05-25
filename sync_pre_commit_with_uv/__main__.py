from __future__ import annotations

import argparse
import pathlib
import sys
from typing import NamedTuple

from . import exceptions, sync


def existing_path(value: str) -> pathlib.Path:
    """Convert a string to a pathlib.Path and check if it exists."""
    path = pathlib.Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Path '{value}' does not exist.")
    return path


def get_parser():
    """Get the argument parser."""
    parser = argparse.ArgumentParser(
        description="Sync pre-commit configuration with uv configuration."
    )
    parser.add_argument(
        "--pyproject-config",
        type=existing_path,
        default=pathlib.Path("pyproject.toml"),
        help="Path to the pyproject.toml file. Defaults to 'pyproject.toml' in the current directory.",
    )
    parser.add_argument(
        "--pre-commit-config",
        type=existing_path,
        default=None,
        help="Path to the pre-commit configuration file. Defaults to '.pre-commit-config.yaml' in the same directory as pyproject.toml.",
    )
    parser.add_argument(
        "--uv-lock",
        type=existing_path,
        default=None,
        help="Path to the uv.lock file. Defaults to 'uv.lock' in the same directory as pyproject.toml.",
    )
    # Actually useless but pre-commit will provide it.
    parser.add_argument("files", nargs="*")
    return parser


class CliArgs(NamedTuple):
    pyproject_config: pathlib.Path
    pre_commit_config: pathlib.Path
    uv_lock: pathlib.Path


def default_path(sibling: pathlib.Path, name: str) -> pathlib.Path:
    """Return a default path based on a sibling file."""

    path = sibling.parent / name
    if not path.exists():
        raise exceptions.PathDoesNotExist(path=path)
    return path


def parse_cli(argv: list[str]) -> CliArgs:
    parser = get_parser()
    args = parser.parse_args(argv)

    if not args.pre_commit_config:
        args.pre_commit_config = default_path(
            sibling=args.pyproject_config, name=".pre-commit-config.yaml"
        )

    if not args.uv_lock:
        args.uv_lock = default_path(sibling=args.pyproject_config, name="uv.lock")

    return CliArgs(
        pyproject_config=args.pyproject_config,
        pre_commit_config=args.pre_commit_config,
        uv_lock=args.uv_lock,
    )


def cli(argv: list[str] | None = None) -> None:
    """Main entry point for the CLI."""
    argv = sys.argv[1:] if argv is None else argv
    try:
        pyproject_config, pre_commit_config, uv_lock = parse_cli(argv)
        sync.sync(
            pyproject_path=pyproject_config,
            pre_commit_path=pre_commit_config,
            uv_lock_path=uv_lock,
        )
    except exceptions.SyncPreCommitWithUvException as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    cli()
