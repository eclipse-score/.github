# eclipse-score .github repository

This repository hosts the start page for the eclipse-score GitHub organization.
It also contains the repository-overview tool that collects organization data
and renders the profile README and HTML dashboard from a shared snapshot.

The complete tool documentation starts at
[Repo Overview Tool Design](docs/repo-overview-tool-design.md).

## Development

```sh
uv sync --all-groups
uv run generate-repo-overview
uv run generate-repo-overview collect --org-config org_config.toml
uv run generate-repo-overview render-overview
uv run generate-repo-overview render-details
uv run pre-commit run --all-files
```
