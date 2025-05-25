from __future__ import annotations


class SyncPreCommitWithUvException(Exception):
    """sync-pre-commit-with-uv generic error."""

    def __init__(self, message: str = "", **kwargs: object) -> None:
        message = message or type(self).__doc__ or ""
        message = message.format(**kwargs)

        super().__init__(message)


class PyProjectConfigurationError(SyncPreCommitWithUvException):
    """pyproject.toml configuration error: {error}"""


class PreCommitConfigurationError(SyncPreCommitWithUvException):
    """.pre-commit-config.yaml configuration error: {error}"""


class PackageNotFound(SyncPreCommitWithUvException):
    """Package {pypi_name} referenced in pyproject.toml but not found in uv.lock"""


class PathDoesNotExist(SyncPreCommitWithUvException):
    """Path '{path}' does not exist."""
