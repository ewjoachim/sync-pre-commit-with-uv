# Contributing

Contributions are welcome! The project is quite small so feel free to
familiarize yourself with the codebase and open an issue or a pull request.
Before doing anything important, feel free to open an issue to discuss it.

All interactions are required to follow the
[Code of Conduct](CODE_OF_CONDUCT.md) which sets rules for the community.

## Development

Development of this project leverages:

- [uv](https://docs.astral.sh/uv/)
- [ruff](https://docs.astral.sh/ruff/)
- [prek](https://prek.j178.dev/)
- [pytest](https://docs.pytest.org/en/stable/)
- [basedpyright](https://docs.basedpyright.com/latest/)

```console
$ uv sync --all-groups
$ uv run prek install
$ uv run prek --all-files
$ uv run pytest
```

If you have any questions, feel free to ask them in the issues.

# Internal documentation

## Releasing

Create a GitHub Release with the appropriate tag.
