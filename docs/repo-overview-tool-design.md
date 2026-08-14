# Repo Overview Tool Design

## Goals

- Collect GitHub organization data once and reuse it across multiple reports.
- Keep local iteration fast by rendering from a cached snapshot.
- Separate collection, enrichment, and rendering.
- Generate the profile README, HTML dashboard, and GitHub Pages content from a
  shared snapshot.

## Design Documents

- [Architecture and Data Model](repo-overview/architecture.md)
  - package layers
  - normalized snapshot model
  - GitHub API and Git collection responsibilities
- [Collection and Caching](repo-overview/collection-and-cache.md)
  - snapshot cache behavior
  - incremental refresh rules
- [Naming Data Provenance](repo-overview/module-mapping.md)
  - source of every `Naming` tab column
  - public/private platform repository configuration
  - feature and module association rules
- [Usage and Extension](repo-overview/usage-and-extension.md)
  - CLI commands
  - adding views and detectors
