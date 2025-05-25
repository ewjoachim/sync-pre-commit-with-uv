from __future__ import annotations

import pathlib

import pytest

from sync_pre_commit_with_uv import exceptions, sync

from . import factories


def test_sync_config__update_revision_prefix():
    # Test that revision is updated when locked_package exists
    repo_config = factories.RepoConfigFactory(
        username="foo",
        project_name="bar",
        version="1.0.0",
        locked_package__version="2.0.0",
    )

    result = list(sync.sync_config([repo_config], uv_export=lambda params: []))

    assert result == [sync.UpdateRev(repo="https://github.com/foo/bar", value="v2.0.0")]


def test_sync_config__update_revision_no_prefix():
    # Test that revision is updated when locked_package exists
    repo_config = factories.RepoConfigFactory(
        username="foo",
        project_name="bar",
        version="1.0.0",
        pre_commit__rev="1.0.0",
        locked_package__version="2.0.0",
    )

    result = list(sync.sync_config([repo_config], uv_export=lambda params: []))

    assert result == [sync.UpdateRev(repo="https://github.com/foo/bar", value="2.0.0")]


def test_sync_config_no_sync_revision():
    # Test that revision is not updated when sync_revision is False
    repo_config = factories.RepoConfigFactory(
        version="1.0.0",
        locked_package__version="2.0.0",
        pyproject__sync_revision=False,
    )

    result = list(sync.sync_config([repo_config], uv_export=lambda params: []))

    assert result == []


def test_sync_config_raises_when_package_not_found():
    # Test that exception is raised when locked_package doesn't exist and fail_if_not_found is True
    repo_config = factories.RepoConfigFactory(
        locked_package=None,
    )

    with pytest.raises(exceptions.PackageNotFound):
        list(sync.sync_config([repo_config], uv_export=lambda params: []))


def test_sync_config_no_raise_when_fail_if_not_found_false():
    # Test that no exception is raised when locked_package doesn't exist but fail_if_not_found is False

    repo_config = factories.RepoConfigFactory(
        pyproject__fail_if_not_found=False,
        locked_package=None,
    )

    # This should not raise an exception
    list(sync.sync_config([repo_config], uv_export=lambda params: []))


def test_sync_config_with_list_params():
    # Test that dependencies are updated when additional_dependencies_uv_params is a list
    repo_config = factories.RepoConfigFactory(
        username="foo",
        project_name="bar",
        pyproject__additional_dependencies_uv_params=[
            "--requirement",
            "requirements.txt",
        ],
    )

    def fake_uv_export(params: list[str]) -> list[str]:
        if params == ["--requirement", "requirements.txt"]:
            return ["package1==1.0.0", "package2==2.0.0"]
        return []

    result = list(sync.sync_config([repo_config], uv_export=fake_uv_export))

    assert result == [
        sync.UpdateAdditionalDependencies(
            repo="https://github.com/foo/bar",
            hook_id="bar",
            value=["package1==1.0.0", "package2==2.0.0"],
        )
    ]


def test_sync_config_with_dict_params():
    # Test that dependencies are updated only for hooks whose IDs are in the dict
    repo_config = factories.RepoConfigFactory(
        username="foo",
        project_name="bar",
        pyproject__additional_dependencies_uv_params={
            "hook1": ["--requirement", "requirements.txt"],
            "hook2": ["--requirement", "other-requirements.txt"],
        },
        pre_commit__hooks=[
            factories.PreCommitHookConfigFactory(id="hook1"),
            factories.PreCommitHookConfigFactory(id="hook2"),
        ],
    )

    def fake_uv_export(params: list[str]) -> list[str]:
        if params == ["--requirement", "requirements.txt"]:
            return ["package1==1.0.0", "package2==2.0.0"]
        elif params == ["--requirement", "other-requirements.txt"]:
            return ["package3==3.0.0"]
        return []

    result = list(sync.sync_config([repo_config], uv_export=fake_uv_export))

    assert result == [
        sync.UpdateAdditionalDependencies(
            repo="https://github.com/foo/bar",
            hook_id="hook1",
            value=["package1==1.0.0", "package2==2.0.0"],
        ),
        sync.UpdateAdditionalDependencies(
            repo="https://github.com/foo/bar",
            hook_id="hook2",
            value=["package3==3.0.0"],
        ),
    ]


def test_sync_config_with_dict_params_skip_undefined_hook():
    # Test that hooks not defined in additional_dependencies_uv_params are skipped
    repo_config = factories.RepoConfigFactory(
        username="foo",
        project_name="bar",
        pyproject__additional_dependencies_uv_params={
            "hook1": ["--requirement", "requirements.txt"],
        },
        pre_commit__hooks=[
            factories.PreCommitHookConfigFactory(id="hook1"),
            factories.PreCommitHookConfigFactory(id="hook2"),  # Not in params dict
        ],
    )

    def fake_uv_export(params: list[str]) -> list[str]:
        if params == ["--requirement", "requirements.txt"]:
            return ["package1==1.0.0"]
        return []  # Should never be called for hook2

    result = list(sync.sync_config([repo_config], uv_export=fake_uv_export))

    assert result == [
        sync.UpdateAdditionalDependencies(
            repo="https://github.com/foo/bar",
            hook_id="hook1",
            value=["package1==1.0.0"],
        ),
    ]


@pytest.mark.parametrize(
    ("repo_name", "pypi_package_name", "expected"),
    [
        ("my-repo", None, "my-repo"),
        ("pre-commit-hooks", None, "hooks"),
        ("mirrors-mypy", None, "mypy"),
        ("black-pre-commit", None, "black"),
        ("pre-commit-mirrors-prettier", None, "prettier"),
        ("custom-name", "specific-package", "specific-package"),
    ],
)
def test_final_pypi_package_name(repo_name, pypi_package_name, expected):
    config = factories.PyProjectRepoConfigFactory(
        repo_name=repo_name,
        pypi_package_name=pypi_package_name,
    )
    assert config.final_pypi_package_name == expected


@pytest.mark.parametrize(
    ("pyproject_config", "expected_configs"),
    [
        (
            {"tool": {"sync-pre-commit-with-uv": {"black": {}}}},
            [sync.PyProjectRepoConfig(repo_name="black")],
        ),
        (
            {
                "tool": {
                    "sync-pre-commit-with-uv": {
                        "black": {"pypi_package_name": "black"},
                        "ruff": {"sync_revision": False},
                    }
                }
            },
            [
                sync.PyProjectRepoConfig(repo_name="black", pypi_package_name="black"),
                sync.PyProjectRepoConfig(repo_name="ruff", sync_revision=False),
            ],
        ),
        ({"tool": {}}, []),
        ({}, []),
    ],
)
def test_from_pyproject_config(pyproject_config, expected_configs):
    configs = list(sync.PyProjectRepoConfig.from_pyproject_config(pyproject_config))
    assert configs == expected_configs


def test_from_pyproject_config_validation_error():
    pyproject_config = {
        "tool": {
            "sync-pre-commit-with-uv": {
                "invalid-repo": {"pypi_package_name": 123},
            }
        }
    }
    with pytest.raises(exceptions.PyProjectConfigurationError):
        list(sync.PyProjectRepoConfig.from_pyproject_config(pyproject_config))


@pytest.mark.parametrize(
    ("pre_commit_config", "expected_configs"),
    [
        (
            {
                "repos": [
                    {"repo": "https://github.com/psf/black", "hooks": [{"id": "black"}]}
                ]
            },
            [
                sync.PreCommitRepoConfig(
                    repo="https://github.com/psf/black",
                    hooks=[sync.PreCommitHookConfig(id="black")],
                    mutable_config={
                        "repo": "https://github.com/psf/black",
                        "hooks": [{"id": "black"}],
                    },
                )
            ],
        ),
        (
            {
                "repos": [
                    {
                        "repo": "https://github.com/pre-commit/mirrors-mypy",
                        "rev": "v1.0.0",
                        "hooks": [{"id": "mypy"}],
                    },
                    {
                        "repo": "https://github.com/astral-sh/ruff-pre-commit",
                        "hooks": [{"id": "ruff"}, {"id": "ruff-format"}],
                    },
                ]
            },
            [
                sync.PreCommitRepoConfig(
                    repo="https://github.com/pre-commit/mirrors-mypy",
                    rev="v1.0.0",
                    hooks=[sync.PreCommitHookConfig(id="mypy")],
                    mutable_config={
                        "repo": "https://github.com/pre-commit/mirrors-mypy",
                        "rev": "v1.0.0",
                        "hooks": [{"id": "mypy"}],
                    },
                ),
                sync.PreCommitRepoConfig(
                    repo="https://github.com/astral-sh/ruff-pre-commit",
                    hooks=[
                        sync.PreCommitHookConfig(id="ruff"),
                        sync.PreCommitHookConfig(id="ruff-format"),
                    ],
                    mutable_config={
                        "repo": "https://github.com/astral-sh/ruff-pre-commit",
                        "hooks": [{"id": "ruff"}, {"id": "ruff-format"}],
                    },
                ),
            ],
        ),
        (
            {},  # Empty config
            [],
        ),
    ],
)
def test_from_pre_commit_config(pre_commit_config, expected_configs):
    configs = list(sync.PreCommitRepoConfig.from_pre_commit_config(pre_commit_config))
    assert configs == expected_configs


@pytest.mark.parametrize(
    ("pre_commit_config"),
    [
        ({"repos": [{}]}),  # Missing required repo field
        ({"repos": [{"repo": "https://example.com"}]}),  # Missing hooks field
    ],
)
def test_from_pre_commit_config_validation_error(pre_commit_config):
    with pytest.raises(exceptions.PreCommitConfigurationError):
        list(sync.PreCommitRepoConfig.from_pre_commit_config(pre_commit_config))


@pytest.mark.parametrize(
    ("uv_lock_config", "expected_configs"),
    [
        (
            {"package": [{"name": "black", "version": "23.12.1"}]},
            [sync.UvLockPackageConfig(name="black", version="23.12.1")],
        ),
        (
            {
                "package": [
                    {"name": "black", "version": "23.12.1"},
                    {"name": "ruff", "version": "0.1.9"},
                ]
            },
            [
                sync.UvLockPackageConfig(name="black", version="23.12.1"),
                sync.UvLockPackageConfig(name="ruff", version="0.1.9"),
            ],
        ),
        (
            {},  # Empty config
            [],
        ),
        (
            {"package": []},  # Empty package list
            [],
        ),
    ],
)
def test_from_uv_lock_config(uv_lock_config, expected_configs):
    configs = list(sync.UvLockPackageConfig.from_uv_lock_config(uv_lock_config))
    assert configs == expected_configs


def test_map_repos_to_config_simple():
    expected_repo_config = factories.RepoConfigFactory()

    configs = list(
        sync.map_repos_to_config(
            pre_commit_config_objs=[expected_repo_config.pre_commit],
            pyproject_config_objs=[expected_repo_config.pyproject],
            uv_lock_config_objs=[expected_repo_config.locked_package],
        )
    )

    assert list(configs) == [expected_repo_config]


def test_map_repos_to_config_missing_pyproject():
    expected_repo_config = factories.RepoConfigFactory()

    configs = list(
        sync.map_repos_to_config(
            pre_commit_config_objs=[expected_repo_config.pre_commit],
            pyproject_config_objs=[],
            uv_lock_config_objs=[expected_repo_config.locked_package],
        )
    )

    assert configs == [
        sync.RepoConfig(
            pre_commit=expected_repo_config.pre_commit,
            pyproject=sync.PyProjectRepoConfig(
                repo_name=expected_repo_config.locked_package.name,
                fail_if_not_found=False,
            ),
            locked_package=expected_repo_config.locked_package,
        )
    ]


def test_map_repos_to_config_missing_lock():
    expected_repo_config = factories.RepoConfigFactory()
    configs = list(
        sync.map_repos_to_config(
            pre_commit_config_objs=[expected_repo_config.pre_commit],
            pyproject_config_objs=[expected_repo_config.pyproject],
            uv_lock_config_objs=[],
        )
    )

    assert configs == [
        sync.RepoConfig(
            pre_commit=expected_repo_config.pre_commit,
            pyproject=expected_repo_config.pyproject,
            locked_package=None,
        )
    ]


def test_yaml_roundtrip(tmp_path: pathlib.Path):
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("""repos:
  - repo: https://example.com

    hooks:  # foo
      - id: hook1
""")

    with sync.yaml_roundtrip(yaml_file) as config:
        config["repos"][0]["hooks"][0]["id"] = "hook2"

    assert (
        yaml_file.read_text()
        == """repos:
  - repo: https://example.com

    hooks:  # foo
      - id: hook2
"""
    )


def test_yaml_roundtrip_no_changes(tmp_path: pathlib.Path):
    yaml_file = tmp_path / "test.yaml"
    original_content = """repos:
  - repo: https://example.com
    hooks:
      - id: hook1
"""
    yaml_file.write_text(original_content)

    with sync.yaml_roundtrip(yaml_file):
        pass

    assert yaml_file.read_text() == original_content


def test_update_rev__apply():
    config = {
        "repos": [
            {
                "repo": "https://github.com/foo/bar",
                "rev": "v1.0.0",
            }
        ]
    }
    sync.UpdateRev(
        repo="https://github.com/foo/bar",
        value="v2.0.0",
    ).apply(config)

    assert config == {
        "repos": [
            {
                "repo": "https://github.com/foo/bar",
                "rev": "v2.0.0",
            }
        ]
    }


def test_update_addditional_dependencies__apply():
    config = {
        "repos": [
            {
                "repo": "https://github.com/foo/bar",
                "hooks": [
                    {
                        "id": "hook1",
                    }
                ],
            }
        ]
    }
    sync.UpdateAdditionalDependencies(
        repo="https://github.com/foo/bar",
        hook_id="hook1",
        value=["package1==1.0.0", "package2==2.0.0"],
    ).apply(config)
    assert config == {
        "repos": [
            {
                "repo": "https://github.com/foo/bar",
                "hooks": [
                    {
                        "id": "hook1",
                        "additional_dependencies": [
                            "package1==1.0.0",
                            "package2==2.0.0",
                        ],
                    }
                ],
            }
        ]
    }


def test_sync(tmp_path: pathlib.Path):
    pre_commit_file = tmp_path / ".pre-commit-config.yaml"
    pyproject_file = tmp_path / "pyproject.toml"
    uv_lock_file = tmp_path / "uv.lock"

    # Initial content
    pre_commit_file.write_text("""repos:
  - repo: https://github.com/psf/black
    rev: v1.0.0
    hooks:
      - id: black
""")

    pyproject_file.write_text("""[tool.sync-pre-commit-with-uv.black]
pypi_package_name = "black"
""")

    uv_lock_file.write_text("""[project]
name = "test"
version = "0.1.0"

[[package]]
name = "black"
version = "23.12.1"
""")

    sync.sync(
        pre_commit_path=pre_commit_file,
        pyproject_path=pyproject_file,
        uv_lock_path=uv_lock_file,
        uv_export=lambda params: [],
    )

    # Check that the pre-commit config was updated
    assert """repos:
  - repo: https://github.com/psf/black
    rev: v23.12.1
    hooks:
      - id: black
""" == pre_commit_file.read_text()


def test_export_uv_config(fp):
    fp.register(
        [
            "uv",
            "export",
            "--no-hashes",
            "--no-header",
            "--no-emit-project",
            "--no-emit-workspace",
            "--no-annotate",
            "--group=dev",
        ],
        stdout="""package1==1.0.0\npackage2==2.0.0\n""",
    )
    assert sync.uv_export(["--group=dev"]) == ["package1==1.0.0", "package2==2.0.0"]
