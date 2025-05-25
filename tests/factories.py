# It's really hard to type factory boy correctly
from __future__ import annotations

import factory

from sync_pre_commit_with_uv import sync


class PreCommitHookConfigFactory(factory.Factory):
    class Meta:
        model = sync.PreCommitHookConfig

    id = factory.Faker("slug")


class PreCommitRepoConfigFactory(factory.Factory):
    class Meta:
        model = sync.PreCommitRepoConfig

    class Params:
        project_name = factory.Faker("slug")
        username = factory.Faker("user_name")
        version = factory.Faker("numerify", text="%!!.%!!.%!!")

    repo = factory.LazyAttribute(
        lambda x: f"https://github.com/{x.username}/{x.project_name}"
    )
    rev = factory.LazyAttribute(lambda x: f"v{x.version}")
    hooks = factory.List(
        [
            factory.SubFactory(
                PreCommitHookConfigFactory, id=factory.SelfAttribute("...project_name")
            )
        ]
    )

    @factory.lazy_attribute
    def mutable_config(self):
        return {
            "repo": self.repo,
            "rev": self.rev,
            "hooks": [{"id": hook.id} for hook in self.hooks],
        }


class PyProjectRepoConfigFactory(factory.Factory):
    class Meta:
        model = sync.PyProjectRepoConfig

    repo_name = factory.Faker("slug")
    sync_revision = True
    fail_if_not_found = True
    additional_dependencies_uv_params = None


class UvLockPackageConfigFactory(factory.Factory):
    class Meta:
        model = sync.UvLockPackageConfig

    name = factory.Faker("slug")
    version = factory.Faker("numerify", text="%!!.%!!.%!!")


class RepoConfigFactory(factory.Factory):
    class Meta:
        model = sync.RepoConfig

    class Params:
        project_name = factory.Faker("slug")
        username = factory.Faker("user_name")
        version = factory.Faker("numerify", text="%!!.%!!.%!!")

    pre_commit = factory.SubFactory(
        PreCommitRepoConfigFactory,
        project_name=factory.SelfAttribute("..project_name"),
        version=factory.SelfAttribute("..version"),
        username=factory.SelfAttribute("..username"),
    )
    pyproject = factory.SubFactory(
        PyProjectRepoConfigFactory, repo_name=factory.SelfAttribute("..project_name")
    )

    locked_package = factory.SubFactory(
        UvLockPackageConfigFactory,
        name=factory.SelfAttribute("..project_name"),
        version=factory.SelfAttribute("..version"),
    )
