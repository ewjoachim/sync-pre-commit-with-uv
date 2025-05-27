# `sync-pre-commit-with-uv`: a pre-commit hook to sync pre-commit versions with `uv.lock`

[![GitHub Repository](https://img.shields.io/github/stars/ewjoachim/sync-pre-commit-with-uv?style=flat&logo=github&color=brightgreen)](https://github.com/ewjoachim/sync-pre-commit-with-uv/)
[![Continuous Integration](https://img.shields.io/github/actions/workflow/status/ewjoachim/sync-pre-commit-with-uv/ci.yml?logo=github&branch=main)](https://github.com/ewjoachim/sync-pre-commit-with-uv/actions?workflow=CI)
[![Coverage badge](https://raw.githubusercontent.com/ewjoachim/sync-pre-commit-with-uv/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/ewjoachim/sync-pre-commit-with-uv/blob/python-coverage-comment-action-data/htmlcov/index.html)
[![MIT License](https://img.shields.io/github/license/ewjoachim/sync-pre-commit-with-uv?logo=open-source-initiative&logoColor=white)](https://github.com/ewjoachim/sync-pre-commit-with-uv/blob/main/LICENSE.md)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v1.4%20adopted-ff69b4.svg)](https://github.com/ewjoachim/sync-pre-commit-with-uv/blob/main/CODE_OF_CONDUCT.md)

`sync-pre-commit-with-uv` is a [pre-commit](https://pre-commit.com/) hook that does 2 things:

- Ensures that the different `rev` keys in your
  `.pre-commit-config.yaml` are in sync with the versions of corresponding packages in your
  `pyproject.toml`.
- Map specific hooks with uv groups. It will ensure that all the dependencies of
  your uv group will be added as `additional_dependencies` in the corresponding
  pre-commit hook. This is mainly useful for hooks that need a complete environment to
  run, like static type checkers (`mypy`, `pyright`, etc.).

## What?

If your `.pre-commit-config.yaml` file looks like this:
```yaml
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.11
    hooks:
      - id: ruff
```
but your `uv.lock` says you're using ruff at version `0.12.0`, then the hook will change
`.pre-commit-config.yaml` to:
```diff
    - repo: https://github.com/astral-sh/ruff-pre-commit
-     rev: v0.11.11
+     rev: v0.12.0
      hooks:
        - id: ruff
```

And if it looks like this:
```yaml
  - repo: https://github.com/RobertCraigie/pyright-python
    rev: v1.1.400
    hooks:
      - id: pyright
        additional_dependencies:
          - django-stubs==5.1.3
```
And you've added configuration in `pyproject.toml` to synchronize the
`additional_dependencies` with the uv dependency group named `types`:
```toml
[tool.sync-pre-commit-with-uv.pyright-python]
pypi_package_name = "pyright"
additional_dependencies_uv_params = ["--group", "types"]
```
Then when uv upgrades `django-stubs` to 5.1.4, the hook will upgrade
`.pre-commit-config.yaml` to:
```diff
    - repo: https://github.com/RobertCraigie/pyright-python
      rev: v1.1.400
      hooks:
        - id: pyright
          additional_dependencies:
-           - django-stubs==5.1.3
+           - django-stubs==5.1.4
```


## Installation & Usage

```yaml
# .pre-commit-config.yaml
repos:
  # ...
  - repo: https://github.com/ewjoachim/sync-pre-commit-with-uv
    rev: "<current release>"
    hooks:
      # Use this hook to ensure that the versions of the repos are synced
      - id: sync
```

```toml
# pyproject.toml
# ...
[tool.sync-pre-commit-with-uv.pyright-python]
pypi_package_name = "pyright"
additional_dependencies_uv_params = ["--group", "pyright"]

[[tool.sync-pre-commit-with-uv."ruff-pre-commit"]]
pypi_package_name = "ruff"
```

## How it works

This hook:

- Look for all the `repo` keys in your `.pre-commit-config.yaml`
- By default, the tool will try a simple heuristic to match repository URLs with pypi
  names, but you can explicitly provide the mapping by providing entries in your
  `pyproject.toml` configuration (see below for details of the heuristic and supported
  configuration attributes)
- From the list of pypi package names, the hook will extract the corresponding version
  in `uv.lock`. If it detects that the version is different from what you have,
  it will replace the value in `.pre-commit-config.yaml`.
- In case you define `additional_dependencies_uv_params`, it will run `uv export`
  with your supplied parameters (letting you select/unselect any group/extra) and
  will add all resulting values in the `additional_dependencies` object for the
  corresponding hook.

## Configuration

Here's the anatomy of the entries in your `pyproject.toml`:

```
[tool.sync-pre-commit-with-uv.repo_name]
pypi_package_name = "..."
skipped = true
additional_dependencies_uv_params = ["..."]
# or
additional_dependencies_uv_params = { hook_id = ["..."] }
```

- `repo_name`: the name of the repository, the part after the last `/` in the URL,
  omitting potential `.git` suffix.
- `pypi_package_name`: optional string matching the name of the repository (it will be
  normalized). If not provided, it will be assumed to be the normalized `repo_name`,
  removing potential `mirrors-` or `pre-commit-` prefixes and `-pre-commit` suffix.
- `skipped`: optional boolean, defaults to `false`. If set to `true`, the hook will not
  try to synchronize the version of the repository with the one in `uv.lock`.
- `additional_dependencies_uv_params`: optional list of strings, which will be passed to
  `uv export` to get the dependencies that should be added to the
  `additional_dependencies` key of the hook. Can also be set to a dict: in that case the
  key will be understood as a `hook_id`, and that configuration will only apply to this
  specific hook. Can be set to `[]` if you don't need any `uv export` parameters.

If a repository in `.pre-commit-config.yaml` does not have a corresponding entry in
`pyproject.toml`, all the attributes will be set to their default values, if the
corresponding pypi package isn't found, it will be ignored.

> [!NOTE]
> It's perfectly possible that you could end up without any specific
> configuration in your `pyproject.toml` file. You only need to write configuration for
> the projects where the default configuration doesn't work, or if you want to sync
> additional dependencies.

## Credit where it's due

This project is heavily inspired by
[poetry-to-pre-commit](https://github.com/ewjoachim/poetry-to-pre-commit), itself
inspired by [sync_with_poetry](https://github.com/floatingpurr/sync_with_poetry).
