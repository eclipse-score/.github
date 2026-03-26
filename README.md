# eclipse-score .github repository

This repository hosts the start page when you visit the eclipse-score GitHub organization. It contains links to the Eclipse Score website, documentation, and other resources related to the Eclipse Score project.


## Development

Use `uv` to create a virtual environment and install the project dependencies:

```
uv sync --all-groups
```

To generate the organization profile README:

```
uv run generate-profile-readme
```

The generator reads repository custom properties from GitHub and expects `GITHUB_TOKEN` to be set.
If `GITHUB_TOKEN` is not set, it falls back to `gh auth token`.

To run the local checks:

```sh
uv run pre-commit run --all-files
```
