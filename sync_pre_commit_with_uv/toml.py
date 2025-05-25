from __future__ import annotations

import sys
from typing import Any

if sys.version_info < (3, 11):
    import tomli as toml
else:
    import tomllib as toml

import pathlib


def read_toml(file_path: pathlib.Path) -> dict[str, Any]:
    """Read a TOML file and return its content as a dictionary."""
    return toml.loads(file_path.read_text())
