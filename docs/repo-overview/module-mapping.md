# Naming Data Provenance

The HTML `Naming` tab is derived during collection. It does not use a
repository-to-feature mapping from configuration.

| Column | Source | Derivation |
|---|---|---|
| Repository | GitHub organization repository list and repository content | Includes every repository detected as a Bazel repository. Tables are separated by the configured repository category, like the other dashboard tabs. |
| Platform Docs | `signals.platform_repos` in `org_config.toml` | Identifies the public or private repository from which the Sphinx declaration was collected. |
| Platform Feature Path | Configured platform repository tree below `docs/features/` | Uses the feature directory containing the discovered Sphinx declaration, for example `docs/features/log_trace/logging` becomes `log_trace/logging`. |
| Sphinx Feature | Platform files below `docs/features/` and feature architecture files in the module repository | Shows both sources in one cell. Platform `.. feat::` declarations (or the existing platform `.. document::` fallback) are expected. A repository `.. feat::` declaration is shown with a warning because feature declarations belong in the platform documentation. The cell is not applicable for a platform repository itself. |
| Bazel Module | Root `MODULE.bazel` in each repository | Reads the `name` argument from the root `module(...)` declaration. Dependency names from `bazel_dep(...)` are not used. |
| Sphinx Module | `docs/module/index.rst` and feature architecture files in the module repository, plus `docs/modules/*/docs/index.rst` in configured platform repositories | Shows both sources in one cell. Repository `.. mod::` declarations are expected. A platform declaration is shown with a warning because module declarations belong in the module repository. |
| Repo Feature Path | Repository tree below `docs/features/` | For the multi-feature template, reports each `docs/features/<feature_name>` path. A bare `docs/features` value identifies the documented single-feature variant, where no additional feature-name folder exists and the repository or module name is expected to represent the feature. The cell is not applicable for platform documentation repositories. |
| Sphinx Config | `docs/conf.py`, with `docs/sphinx/conf.py` as fallback | Reads the literal `project` and `project_prefix` assignments. Values copied unchanged from the template remain visible as mismatches rather than being hidden. |

## Platform Documentation Sources

Platform documentation repositories are configured in `org_config.toml`:

```toml
[signals]
platform_repos = [
  "eclipse-score/score",
  "example/private-score-features",
]
```

Every configured repository is inspected independently. Discovered public and
private feature/module declarations are merged, and each snapshot item retains
its source repository. Identical paths from different sources therefore remain
distinguishable.

## Association Rules

Feature and Sphinx module declarations are associated using aliases derived
from:

- repository name
- Bazel module name
- local feature folder names
- local Sphinx module titles and IDs
- Sphinx `project` and `project_prefix`
- Sphinx title
- Sphinx ID
- leaf documentation directory

Matching removes `score_` and `inc_` prefixes, normalizes
`configuration`/`config` and `management`/`mgmt`, and removes punctuation.
Exact matches take precedence. A fuzzy match is accepted only above the
internal confidence threshold and when it is clearly better than the next
candidate.

Ambiguous or missing associations remain `—` in the generated table. They are
never guessed or supplied by configuration.

## Name Match Colors

All displayed name values are compared with the repository name. Platform
paths/directives, repository paths/directives, the Bazel module, and Sphinx
configuration use the same classification:

- green: exact match after documented normalization
- yellow: close, unambiguous match above the association threshold
- red: different from the repository name

The comparison removes `score_` and `inc_` prefixes, normalizes
`configuration`/`config` and `management`/`mgmt`, and ignores punctuation.
Missing values remain uncolored.
