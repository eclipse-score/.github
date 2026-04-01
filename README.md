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

Category order and category descriptions are configured in
`src/profile_readme_generator/profile_readme_config.toml`. Pass
`--config /path/to/file.toml` to use a different config file.

The generator reads repository custom properties from GitHub and expects `GITHUB_TOKEN` to be set.
If `GITHUB_TOKEN` is not set, it falls back to `gh auth token`.

To run the local checks:

```sh
uv run pre-commit run --all-files
```
