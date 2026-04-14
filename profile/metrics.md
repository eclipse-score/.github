# Cross-Repo Metrics Report

Generated on 2026-04-14T14:37:52.210546+00:00

- Repositories: 59
- With GitHub Actions: 49
- Using daily workflow: 2
- With lint/style config: 13
- With coverage config: 1
- With releases: 33

## Signal Definitions

- `Bazel Version`: first non-comment line from `.bazelversion`. `-` means the repo does not declare one there.
- `Lint/Style Config`: `yes` if `.gitlint`, `.editorconfig`, or `.pre-commit-config.yaml` exists.
- `GitHub Actions`: `yes` if `.github/workflows` exists.
- `Daily Workflow`: `yes` if any workflow file references `cicd-workflows/.github/workflows/daily.yml@...`.
- `Coverage Config`: `yes` if `coverage.yml`, `coverage.xml`, `pytest.ini`, or `.coveragerc` exists.
- `Latest Release`: release tag name, falling back to the release name when needed.
- `Commits Since Release`: compare the latest release tag to the current default branch head. `-` means no release or no comparable tag.

| Repository | Category | Last Push | Issues | PRs | Bazel Version | Lint/Style Config | GitHub Actions | Daily Workflow | Coverage Config | Latest Release | Release Date | Commits Since Release | Stars | Forks |
|------------|----------|-----------|--------|-----|---------------|-------------------|----------------|----------------|-----------------|----------------|--------------|-----------------------|-------|-------|
| [.eclipsefdn](https://github.com/eclipse-score/.eclipsefdn) | Uncategorized | 2026-04-10 | 2 | 1 | - | no | yes | no | no | - | - | - | 0 | 34 |
| [.github](https://github.com/eclipse-score/.github) | infrastructure | 2026-04-14 | 3 | 2 | - | yes | yes | no | no | - | - | - | 0 | 9 |
| [apt-install](https://github.com/eclipse-score/apt-install) | infrastructure | 2026-03-30 | 0 | 0 | - | no | yes | no | no | - | - | - | 3 | 3 |
| [baselibs](https://github.com/eclipse-score/baselibs) | modules | 2026-04-14 | 55 | 24 | 8.3.1 | no | yes | no | no | v0.2.5 | 2026-04-10 | 53 | 24 | 54 |
| [baselibs_rust](https://github.com/eclipse-score/baselibs_rust) | modules | 2026-03-31 | 13 | 3 | 8.4.2 | no | yes | no | no | v0.1.1 | 2026-03-24 | 2 | 1 | 7 |
| [bazel-tools-cc](https://github.com/eclipse-score/bazel-tools-cc) | infrastructure | 2026-03-27 | 3 | 3 | 8.4.2 | no | yes | no | no | v0.1.0 | 2025-12-15 | 0 | 1 | 5 |
| [bazel-tools-python](https://github.com/eclipse-score/bazel-tools-python) | Uncategorized | 2026-03-27 | 3 | 2 | 7.5.0 | yes | yes | no | no | v0.1.3 | 2025-11-25 | 3 | 0 | 4 |
| [bazel_cpp_toolchains](https://github.com/eclipse-score/bazel_cpp_toolchains) | infrastructure | 2026-04-14 | 8 | 3 | 8.3.1 | no | yes | no | no | v0.5.0 | 2026-04-09 | 0 | 2 | 9 |
| [bazel_platforms](https://github.com/eclipse-score/bazel_platforms) | infrastructure | 2026-03-26 | 0 | 0 | - | no | no | no | no | v0.1.2 | 2026-03-26 | 0 | 1 | 10 |
| [bazel_registry](https://github.com/eclipse-score/bazel_registry) | infrastructure | 2026-04-14 | 7 | 3 | - | yes | yes | yes | no | v0.5.0-beta | 2025-12-22 | 133 | 2 | 18 |
| [bazel_registry_ui](https://github.com/eclipse-score/bazel_registry_ui) | infrastructure | 2026-04-14 | 4 | 3 | 8.4.2 | yes | yes | no | no | - | - | - | 0 | 3 |
| [cicd-actions](https://github.com/eclipse-score/cicd-actions) | infrastructure | 2026-03-10 | 0 | 0 | - | no | no | no | no | - | - | - | 0 | 3 |
| [cicd-workflows](https://github.com/eclipse-score/cicd-workflows) | infrastructure | 2026-04-09 | 13 | 4 | - | yes | yes | no | no | - | - | - | 0 | 12 |
| [communication](https://github.com/eclipse-score/communication) | modules | 2026-04-14 | 71 | 32 | 8.3.0 | no | yes | no | no | v0.1.4 | 2026-03-09 | 312 | 44 | 76 |
| [config_management](https://github.com/eclipse-score/config_management) | modules | 2026-03-31 | 2 | 2 | 8.3.0 | no | yes | no | no | - | - | - | 1 | 5 |
| [dash-license-scan](https://github.com/eclipse-score/dash-license-scan) | infrastructure | 2026-03-06 | 3 | 1 | - | no | yes | no | no | v0.0.1a1 | 2025-12-19 | 0 | 1 | 3 |
| [dev_playground](https://github.com/eclipse-score/dev_playground) | Uncategorized | 2026-03-10 | 0 | 0 | - | no | no | no | no | - | - | - | 1 | 3 |
| [devcontainer](https://github.com/eclipse-score/devcontainer) | infrastructure | 2026-04-13 | 3 | 0 | - | yes | yes | no | no | v1.3.0 | 2026-03-23 | 4 | 2 | 8 |
| [docs-as-code](https://github.com/eclipse-score/docs-as-code) | infrastructure | 2026-04-14 | 35 | 8 | 8.4.2 | yes | yes | yes | no | v4.0.0 | 2026-04-13 | 1 | 6 | 24 |
| [eclipse-score-website](https://github.com/eclipse-score/eclipse-score-website) | website | 2026-04-09 | 12 | 0 | - | no | yes | no | no | - | - | - | 0 | 10 |
| [eclipse-score-website-preview](https://github.com/eclipse-score/eclipse-score-website-preview) | website | 2026-04-09 | 0 | 0 | - | no | no | no | no | - | - | - | 0 | 2 |
| [eclipse-score-website-published](https://github.com/eclipse-score/eclipse-score-website-published) | website | 2026-04-09 | 2 | 0 | - | no | no | no | no | - | - | - | 0 | 2 |
| [eclipse-score.github.io](https://github.com/eclipse-score/eclipse-score.github.io) | website | 2026-01-08 | 7 | 4 | 7.4.0 | yes | yes | no | no | - | - | - | 8 | 16 |
| [feo](https://github.com/eclipse-score/feo) | modules | 2026-04-14 | 4 | 3 | 8.3.0 | no | yes | no | no | v1.0.5 | 2026-02-19 | 11 | 4 | 17 |
| [ferrocene_toolchain_builder](https://github.com/eclipse-score/ferrocene_toolchain_builder) | infrastructure | 2026-03-31 | 0 | 0 | - | no | yes | no | no | 1.2.0 | 2026-03-16 | 3 | 0 | 2 |
| [inc_daal](https://github.com/eclipse-score/inc_daal) | modules | 2026-04-01 | 4 | 4 | 8.3.0 | no | yes | no | no | - | - | - | 4 | 7 |
| [inc_diagnostics](https://github.com/eclipse-score/inc_diagnostics) | modules | 2026-04-13 | 2 | 2 | 8.3.0 | no | yes | no | no | - | - | - | 0 | 4 |
| [inc_os_autosd](https://github.com/eclipse-score/inc_os_autosd) | modules | 2026-03-25 | 1 | 1 | 8.3.0 | no | yes | no | no | - | - | - | 0 | 8 |
| [inc_someip_gateway](https://github.com/eclipse-score/inc_someip_gateway) | modules | 2026-04-14 | 17 | 7 | 8.3.0 | yes | yes | no | no | - | - | - | 3 | 7 |
| [inc_time](https://github.com/eclipse-score/inc_time) | modules | 2026-04-10 | 2 | 2 | 8.3.0 | no | yes | no | no | - | - | - | 1 | 5 |
| [infrastructure](https://github.com/eclipse-score/infrastructure) | infrastructure | 2026-04-14 | 1 | 1 | - | no | no | no | no | - | - | - | 0 | 3 |
| [itf](https://github.com/eclipse-score/itf) | infrastructure | 2026-04-14 | 4 | 1 | 8.5.0 | no | yes | no | yes | 0.2.0 | 2026-04-08 | 14 | 0 | 16 |
| [kyron](https://github.com/eclipse-score/kyron) | modules | 2026-04-01 | 20 | 4 | 8.3.0 | no | yes | no | no | v0.1.1 | 2026-02-17 | 5 | 2 | 7 |
| [lifecycle](https://github.com/eclipse-score/lifecycle) | modules | 2026-04-14 | 39 | 6 | 8.4.2 | no | yes | no | no | v0.1.0 | 2026-02-17 | 86 | 3 | 17 |
| [logging](https://github.com/eclipse-score/logging) | modules | 2026-04-09 | 18 | 12 | 8.3.0 | no | yes | no | no | v0.1.0 | 2026-02-19 | 17 | 2 | 19 |
| [module_template](https://github.com/eclipse-score/module_template) | infrastructure | 2026-04-14 | 13 | 11 | 8.3.0 | yes | yes | no | no | - | - | - | 2 | 15 |
| [more-disk-space](https://github.com/eclipse-score/more-disk-space) | infrastructure | 2026-01-20 | 0 | 0 | - | no | yes | no | no | - | - | - | 0 | 2 |
| [nlohmann_json](https://github.com/eclipse-score/nlohmann_json) | Uncategorized | 2026-04-14 | 5 | 4 | - | no | yes | no | no | - | - | - | 3 | 6 |
| [orchestrator](https://github.com/eclipse-score/orchestrator) | modules | 2026-04-09 | 17 | 2 | 8.3.0 | no | yes | no | no | v0.1.0 | 2026-02-17 | 7 | 5 | 16 |
| [os_images](https://github.com/eclipse-score/os_images) | infrastructure | 2026-03-11 | 6 | 3 | 8.3.0 | no | yes | no | no | - | - | - | 0 | 5 |
| [persistency](https://github.com/eclipse-score/persistency) | modules | 2026-04-14 | 32 | 12 | 8.4.2 | no | yes | no | no | v0.3.0 | 2026-02-17 | 19 | 2 | 28 |
| [process_description](https://github.com/eclipse-score/process_description) | general | 2026-04-14 | 67 | 3 | 8.4.2 | no | yes | no | no | v1.5.3 | 2026-04-13 | 0 | 2 | 22 |
| [qnx_unit_tests](https://github.com/eclipse-score/qnx_unit_tests) | infrastructure | 2026-04-09 | 0 | 0 | 8.6.0 | no | yes | no | no | 0.1.0 | 2026-04-09 | 0 | 0 | 3 |
| [reference_integration](https://github.com/eclipse-score/reference_integration) | infrastructure | 2026-04-10 | 29 | 6 | 8.4.2 | no | yes | no | no | v0.5.0-beta | 2025-12-22 | 62 | 4 | 24 |
| [rules_imagefs](https://github.com/eclipse-score/rules_imagefs) | infrastructure | 2026-04-02 | 0 | 0 | 8.3.1 | no | yes | no | no | v0.0.3 | 2026-04-02 | 0 | 0 | 2 |
| [rules_rust](https://github.com/eclipse-score/rules_rust) | infrastructure | 2026-04-14 | 6 | 5 | 8.4.2 | yes | yes | no | no | 0.68.1-score | 2026-02-18 | 0 | 0 | 2 |
| [sbom-tool](https://github.com/eclipse-score/sbom-tool) | infrastructure | 2026-04-02 | 1 | 1 | - | no | no | no | no | - | - | - | 0 | 3 |
| [score](https://github.com/eclipse-score/score) | general | 2026-04-14 | 572 | 19 | 8.3.0 | yes | yes | no | no | v0.5.4 | 2026-02-20 | 105 | 93 | 93 |
| [score-crates](https://github.com/eclipse-score/score-crates) | Uncategorized | 2026-03-25 | 3 | 3 | - | no | yes | no | no | v0.0.9 | 2026-03-25 | 0 | 1 | 13 |
| [score_cpp_policies](https://github.com/eclipse-score/score_cpp_policies) | infrastructure | 2026-03-03 | 2 | 2 | - | no | no | no | no | - | - | - | 0 | 3 |
| [score_rust_policies](https://github.com/eclipse-score/score_rust_policies) | infrastructure | 2026-03-11 | 1 | 1 | - | no | yes | no | no | 0.0.5 | 2026-02-05 | 1 | 0 | 5 |
| [scrample](https://github.com/eclipse-score/scrample) | modules | 2026-03-14 | 7 | 4 | 8.3.0 | no | yes | no | no | v0.1.1 | 2026-01-26 | 2 | 3 | 11 |
| [testing_tools](https://github.com/eclipse-score/testing_tools) | infrastructure | 2026-03-27 | 1 | 1 | 8.4.2 | no | yes | no | no | v0.4.0 | 2026-02-19 | 0 | 1 | 6 |
| [toolchains_gcc](https://github.com/eclipse-score/toolchains_gcc) | infrastructure | 2026-03-11 | 5 | 2 | - | no | no | no | no | v0.0.7 | 2025-12-02 | 1 | 4 | 14 |
| [toolchains_gcc_packages](https://github.com/eclipse-score/toolchains_gcc_packages) | infrastructure | 2026-03-04 | 1 | 1 | - | no | yes | no | no | - | - | - | 0 | 8 |
| [toolchains_qnx](https://github.com/eclipse-score/toolchains_qnx) | infrastructure | 2026-03-11 | 8 | 1 | 8.1.0 | no | yes | no | no | v0.0.7 | 2026-02-09 | 2 | 5 | 10 |
| [toolchains_rust](https://github.com/eclipse-score/toolchains_rust) | infrastructure | 2026-04-01 | 4 | 2 | - | no | yes | no | no | v0.8.0 | 2026-03-23 | 0 | 1 | 9 |
| [tooling](https://github.com/eclipse-score/tooling) | infrastructure | 2026-04-14 | 26 | 18 | 8.3.1 | yes | yes | no | no | v1.2.0 | 2026-04-02 | 6 | 6 | 20 |
| [tools](https://github.com/eclipse-score/tools) | infrastructure | 2026-04-10 | 1 | 1 | - | no | no | no | no | - | - | - | 1 | 2 |
