from __future__ import annotations

import pathlib
import subprocess

from sync_pre_commit_with_uv import __main__ as cli


def test_full_integration(tmp_path: pathlib.Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pre_commit_file = tmp_path / ".pre-commit-config.yaml"
    pyproject_file = tmp_path / "pyproject.toml"

    # Initialize uv project first
    subprocess.run(["uv", "init"], check=True)
    subprocess.run(["uv", "add", "black==23.12.1"], check=True)
    subprocess.run(["uv", "add", "pyright==1.1.335"], check=True)
    subprocess.run(
        [
            "uv",
            "add",
            "--group=types",
            "types-requests==2.31.0.20240125",
            "urllib3==2.4.0",
        ],
        check=True,
    )

    # Then write config files
    pre_commit_file.write_text("""repos:
  - repo: https://github.com/psf/black
    rev: v0.0.0
    hooks:
      - id: black
  - repo: https://github.com/microsoft/pyright-python
    rev: v0.0.0
    hooks:
      - id: pyright
""")

    # Append our tool config to the pyproject.toml created by uv init
    with open(pyproject_file, "a") as f:
        f.write("""

[tool.sync-pre-commit-with-uv.black]
pypi_package_name = "black"

[tool.sync-pre-commit-with-uv.pyright-python]
pypi_package_name = "pyright"
additional_dependencies_uv_params = { pyright = ["--only-group", "types"] }
""")

    # Run the CLI
    cli.cli(["--pre-commit-config", str(pre_commit_file)])

    # Verify the final state
    assert """repos:
  - repo: https://github.com/psf/black
    rev: v23.12.1
    hooks:
      - id: black
  - repo: https://github.com/microsoft/pyright-python
    rev: v1.1.335
    hooks:
      - id: pyright
        additional_dependencies:
          - types-requests==2.31.0.20240125
          - urllib3==2.4.0
""" == pre_commit_file.read_text()
