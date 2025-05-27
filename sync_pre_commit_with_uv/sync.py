from __future__ import annotations

import contextlib
import copy
import pathlib
import subprocess
from collections.abc import Generator, Iterable
from typing import Any, NamedTuple, Protocol, cast

import packaging.utils
import pydantic
import ruamel.yaml

from . import exceptions, toml


class PyProjectRepoConfig(pydantic.BaseModel):
    repo_name: str
    pypi_package_name: str | None = None
    sync_revision: bool = True
    fail_if_not_found: bool = True
    additional_dependencies_uv_params: dict[str, list[str]] | list[str] | None = None

    @classmethod
    def from_pyproject_config(
        cls, pyproject_config: dict[str, Any]
    ) -> Iterable[PyProjectRepoConfig]:
        """
        Create PyProjectRepoConfig instances from the 'tool.sync-pre-commit-with-uv' section
        of a pyproject.toml file.
        """
        for key, value in (
            pyproject_config.get("tool", {}).get("sync-pre-commit-with-uv", {}).items()
        ):
            try:
                yield cls(repo_name=key, **value)
            except pydantic.ValidationError as exc:
                raise exceptions.PyProjectConfigurationError(error=str(exc)) from exc

    @property
    def final_pypi_package_name(self):
        """
        Returns the final PyPI package name, either from the pypi_package_name field
        or derived from the repo_name.
        """
        if self.pypi_package_name:
            return self.pypi_package_name
        return packaging.utils.canonicalize_name(
            self.repo_name.removeprefix("pre-commit-")
            .removeprefix("mirrors-")
            .removesuffix("-pre-commit"),
        )


class UpdateProtocol(Protocol):
    def apply(self, pre_commit_config: dict[str, Any]) -> None: ...


class UpdateRev(pydantic.BaseModel):
    repo: str
    value: str

    def apply(self, pre_commit_config: dict[str, Any]) -> None:
        repo = next(
            iter(r for r in pre_commit_config["repos"] if r["repo"] == self.repo)
        )
        repo["rev"] = self.value


class UpdateAdditionalDependencies(pydantic.BaseModel):
    repo: str
    hook_id: str
    value: list[str]

    def apply(self, pre_commit_config: dict[str, Any]) -> None:
        hook = next(
            iter(
                h
                for r in pre_commit_config["repos"]
                if r["repo"] == self.repo
                for h in r["hooks"]
                if h["id"] == self.hook_id
            )
        )
        hook["additional_dependencies"] = self.value


class PreCommitHookConfig(pydantic.BaseModel):
    id: str


class PreCommitRepoConfig(pydantic.BaseModel):
    repo: str
    rev: str = ""
    hooks: list[PreCommitHookConfig]

    @classmethod
    def from_pre_commit_config(
        cls, config: dict[str, Any]
    ) -> Iterable[PreCommitRepoConfig]:
        """
        Create PreCommitRepoConfig instances from the 'repos' section of a
        pre-commit configuration file."""
        for repo in config.get("repos", []):
            try:
                yield cls(**repo)
            except pydantic.ValidationError as exc:
                raise exceptions.PreCommitConfigurationError(
                    error=f"Missing required key: {exc}"
                ) from exc


class UvLockPackageConfig(pydantic.BaseModel):
    name: str
    version: str

    @classmethod
    def from_uv_lock_config(
        cls, config: dict[str, Any]
    ) -> Iterable[UvLockPackageConfig]:
        """
        Create UvLockPackageConfig instances from the 'package' section of a
        uv.lock file.
        """
        for package in config.get("package", []):
            try:
                yield cls(name=package["name"], version=package["version"])
            except KeyError:
                continue


class RepoConfig(NamedTuple):
    pre_commit: PreCommitRepoConfig
    pyproject: PyProjectRepoConfig
    locked_package: UvLockPackageConfig | None = None


def map_repos_to_config(
    pre_commit_config_objs: list[PreCommitRepoConfig],
    pyproject_config_objs: list[PyProjectRepoConfig],
    uv_lock_config_objs: list[UvLockPackageConfig],
) -> Iterable[RepoConfig]:
    """
    Map pre-commit repositories to their corresponding PyProject and locked package
    configurations. Returns a dictionary: repo_name to RepoConfig instances.
    """
    pyproject_configs_by_name = {
        config.repo_name: config for config in pyproject_config_objs
    }
    uv_lock_configs_by_name = {config.name: config for config in uv_lock_config_objs}
    for pre_commit_config in pre_commit_config_objs:
        repo_name = get_repo_name(pre_commit_config.repo)
        try:
            pyproject_config = pyproject_configs_by_name[repo_name]
        except KeyError:
            pyproject_config = PyProjectRepoConfig(
                repo_name=repo_name, fail_if_not_found=False
            )

        pypi_name = pyproject_config.final_pypi_package_name
        try:
            locked_package = uv_lock_configs_by_name[pypi_name]
        except KeyError:
            locked_package = None

        yield RepoConfig(
            pre_commit=pre_commit_config,
            pyproject=pyproject_config,
            locked_package=locked_package,
        )


def get_repo_name(repo_url: str):
    """
    Extract the repository name from a given URL.
    """
    return repo_url.rstrip("/").split("/")[-1].removesuffix(".git")


@contextlib.contextmanager
def yaml_roundtrip(
    path: pathlib.Path,
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager for reading and writing YAML files with round-trip preservation.
    """
    yaml = ruamel.yaml.YAML()
    config = cast("dict[str, Any]", yaml.load(path.read_text()))
    old_config = copy.deepcopy(config)
    yield config
    if config != old_config:
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.dump(config, path)


class UvExportProtocol(Protocol):
    def __call__(self, params: list[str]) -> list[str]: ...


def uv_export(params: list[str]) -> list[str]:
    """
    Export the list of packages from uv using the provided parameters.
    """
    base_export_args = [
        "uv",
        "export",
        "--no-hashes",
        "--no-header",
        "--no-emit-project",
        "--no-emit-workspace",
        "--no-annotate",
    ]
    packages = (
        subprocess.check_output([*base_export_args, *params], text=True)
        .strip()
        .split("\n")
    )
    return packages


def sync_revision(
    *,
    repo_config: RepoConfig,
) -> Iterable[UpdateProtocol]:
    """
    Synchronize the revision of a pre-commit repository with the locked package version.
    """
    if not repo_config.locked_package:
        if repo_config.pyproject.fail_if_not_found:
            raise exceptions.PackageNotFound(
                pypi_name=repo_config.pyproject.final_pypi_package_name
            )
    else:
        prefix = "v" if repo_config.pre_commit.rev.startswith("v") else ""
        new_rev = f"{prefix}{repo_config.locked_package.version}"
        if repo_config.pre_commit.rev != new_rev:
            yield UpdateRev(repo=repo_config.pre_commit.repo, value=new_rev)


def sync_additional_dependencies(
    *,
    repo_config: RepoConfig,
    uv_export: UvExportProtocol,
) -> Iterable[UpdateProtocol]:
    """
    Synchronize the additional dependencies of a pre-commit hook with the locked package version.
    """
    uv_params = repo_config.pyproject.additional_dependencies_uv_params
    for hook in repo_config.pre_commit.hooks:
        if isinstance(uv_params, dict):
            params_for_hook = uv_params.get(hook.id, None)
        else:
            params_for_hook = uv_params

        if params_for_hook is None:
            continue

        dependencies = uv_export(params_for_hook)
        yield UpdateAdditionalDependencies(
            repo=repo_config.pre_commit.repo,
            hook_id=hook.id,
            value=dependencies,
        )


def sync_config(
    mapping: Iterable[RepoConfig], uv_export: UvExportProtocol
) -> Iterable[UpdateProtocol]:
    """
    Update the pre-commit configuration dictionary based on the provided mapping.
    """
    for repo_config in mapping:
        if repo_config.pyproject.sync_revision:
            yield from sync_revision(
                repo_config=repo_config,
            )

        if repo_config.pyproject.additional_dependencies_uv_params is not None:
            yield from sync_additional_dependencies(
                repo_config=repo_config,
                uv_export=uv_export,
            )


def sync(
    *,
    pyproject_path: pathlib.Path,
    pre_commit_path: pathlib.Path,
    uv_lock_path: pathlib.Path,
    uv_export: UvExportProtocol = uv_export,
):
    """
    Main entry point.
    Reads the pyproject.toml, pre-commit configuration file, and uv.lock file,
    maps the repositories to their configurations, and updates the pre-commit
    configuration file.

    This function mainly does the parsing and delegates the actual syncing
    to the sync_configs function.
    """
    with yaml_roundtrip(pre_commit_path) as pre_commit_dict:
        pyproject_config = PyProjectRepoConfig.from_pyproject_config(
            toml.read_toml(pyproject_path)
        )
        pre_commit_config = PreCommitRepoConfig.from_pre_commit_config(pre_commit_dict)

        uv_lock_config = UvLockPackageConfig.from_uv_lock_config(
            toml.read_toml(uv_lock_path)
        )

        mapping = map_repos_to_config(
            pre_commit_config_objs=list(pre_commit_config),
            pyproject_config_objs=list(pyproject_config),
            uv_lock_config_objs=list(uv_lock_config),
        )
        for update in sync_config(mapping=mapping, uv_export=uv_export):
            update.apply(pre_commit_dict)
