# Welcome to eclipse-score

This Github organization contains artifacts developed by the [Eclipse S-CORE Project](https://projects.eclipse.org/projects/automotive.score).

## Introduction to Eclipse S-CORE Project

See [S-CORE-website](https://eclipse-score.github.io/) and [documentation](https://eclipse-score.github.io/score).

## Repositories in the Github organization

*Note: categories and descriptions are taken from [IAC configuration](https://github.com/eclipse-score/.eclipsefdn/blob/main/otterdog/eclipse-score.jsonnet). If you need changes, you must change them there, not here!*

### General

| Repository | Description |
|------------|-------------|
| [process_description](https://github.com/eclipse-score/process_description) | Score project process description |
| [score](https://github.com/eclipse-score/score) | Score project main repository |

---

### Modules

Core S-CORE modules, libraries, and APIs.

#### General

| Repository | Description |
|------------|-------------|
| [baselibs](https://github.com/eclipse-score/baselibs) | base libraries including common functionality |
| [baselibs_rust](https://github.com/eclipse-score/baselibs_rust) | Repository for the Rust baselibs |
| [communication](https://github.com/eclipse-score/communication) | Repository for the communication module LoLa |
| [config_management](https://github.com/eclipse-score/config_management) | Repository for config management |
| [feo](https://github.com/eclipse-score/feo) | Repository for the Fixed Order Execution (FEO) framework |
| [kyron](https://github.com/eclipse-score/kyron) | Safe async runtime for Rust |
| [lifecycle](https://github.com/eclipse-score/lifecycle) | Repository for the lifecycle feature |
| [logging](https://github.com/eclipse-score/logging) | Repository for logging daemon |
| [orchestrator](https://github.com/eclipse-score/orchestrator) | Orchestration framework & Safe async runtime for Rust |
| [persistency](https://github.com/eclipse-score/persistency) | Repository for persistency framework |
| [scrample](https://github.com/eclipse-score/scrample) | Repository for example component |

#### Incubation

Repositories for experimental or early-stage features.

| Repository | Description |
|------------|-------------|
| [inc_daal](https://github.com/eclipse-score/inc_daal) | Incubation repository for DAAL module |
| [inc_diagnostics](https://github.com/eclipse-score/inc_diagnostics) | Incubation repository for diagnostics feature |
| [inc_os_autosd](https://github.com/eclipse-score/inc_os_autosd) | Incubation repository for AutoSD Development Platform |
| [inc_someip_gateway](https://github.com/eclipse-score/inc_someip_gateway) | Incubation repository for SOME/IP gateway feature |
| [inc_time](https://github.com/eclipse-score/inc_time) | incubation repo for time sync module |

---

### Infrastructure

Shared tooling, build automation, and integration infrastructure.

#### Automation

Continuous integration workflows, automation, and supporting services.

| Repository | Description |
|------------|-------------|
| [apt-install](https://github.com/eclipse-score/apt-install) | GitHub Action to execute apt-install in a clever way |
| [cicd-actions](https://github.com/eclipse-score/cicd-actions) | Reusable GitHub Actions for CI/CD automation |
| [cicd-workflows](https://github.com/eclipse-score/cicd-workflows) | Reusable GitHub Workflows for CI/CD automation |
| [more-disk-space](https://github.com/eclipse-score/more-disk-space) | GitHub Action to make more disk space available in Ubuntu based GitHub Actions runners |

#### General

Infrastructure repositories that do not need a more specific subgroup.

| Repository | Description |
|------------|-------------|
| [.github](https://github.com/eclipse-score/.github) | Houses the organisation README |
| [infrastructure](https://github.com/eclipse-score/infrastructure) | All general information related to the development and integration infrastructure |
| [module_template](https://github.com/eclipse-score/module_template) | C++ & Rust Bazel Template Repository |
| [sbom-tool](https://github.com/eclipse-score/sbom-tool) | Home of the SBOM generation tool |
| [tooling](https://github.com/eclipse-score/tooling) | Tooling for Eclipse S-CORE |
| [tools](https://github.com/eclipse-score/tools) | Home of score-tools, the new pypi based tools approach |

#### Integration

Integration repositories for various systems and components.

| Repository | Description |
|------------|-------------|
| [itf](https://github.com/eclipse-score/itf) | Integration Testing Framework repository |
| [os_images](https://github.com/eclipse-score/os_images) | OS Images for testing and deliveries |
| [reference_integration](https://github.com/eclipse-score/reference_integration) | Score project integration repository |
| [rules_imagefs](https://github.com/eclipse-score/rules_imagefs) | Repository for Image FileSystem Bazel rules and toolchains definitions |
| [testing_tools](https://github.com/eclipse-score/testing_tools) | Repository for testing utilities |

#### Toolchains

Toolchain repositories for compilers, linters, and other development tools.

| Repository | Description |
|------------|-------------|
| [bazel-tools-cc](https://github.com/eclipse-score/bazel-tools-cc) | Repository for clang-tidy based static code checker |
| [bazel_cpp_toolchains](https://github.com/eclipse-score/bazel_cpp_toolchains) | Bazel C/C++ toolchain configuration repository |
| [bazel_platforms](https://github.com/eclipse-score/bazel_platforms) | Bazel platform definitions used by S-CORE modules |
| [ferrocene_toolchain_builder](https://github.com/eclipse-score/ferrocene_toolchain_builder) | Builder for Ferrocene artifacts |
| [rules_rust](https://github.com/eclipse-score/rules_rust) | S-CORE fork of bazelbuild/rules_rust |
| [score_cpp_policies](https://github.com/eclipse-score/score_cpp_policies) | Centralized C++ quality tool policies for S-CORE, including sanitizer configurations and safety-critical guidelines. |
| [score_rust_policies](https://github.com/eclipse-score/score_rust_policies) | Centralized Rust linting and formatting policies for S-CORE, including safety-critical guidelines. |
| [toolchains_gcc](https://github.com/eclipse-score/toolchains_gcc) | Bazel toolchains for GNU GCC |
| [toolchains_gcc_packages](https://github.com/eclipse-score/toolchains_gcc_packages) | Bazel toolchains for GNU GCC |
| [toolchains_qnx](https://github.com/eclipse-score/toolchains_qnx) | Bazel toolchains for QNX |
| [toolchains_rust](https://github.com/eclipse-score/toolchains_rust) | Rust toolchains |

#### Tooling

Developer tools, scripts, and shared engineering utilities.

| Repository | Description |
|------------|-------------|
| [bazel_registry](https://github.com/eclipse-score/bazel_registry) | Score project bazel modules registry |
| [bazel_registry_ui](https://github.com/eclipse-score/bazel_registry_ui) | House the ui for bazel_registry in Score |
| [dash-license-scan](https://github.com/eclipse-score/dash-license-scan) | pipx/uvx wrapper for the dash-licenses tool |
| [devcontainer](https://github.com/eclipse-score/devcontainer) | Common DevContainer for Eclipse S-CORE |
| [docs-as-code](https://github.com/eclipse-score/docs-as-code) | Docs-as-code tooling for Eclipse S-CORE |

---

### Website

Project websites, published documentation, and related web assets.

| Repository | Description |
|------------|-------------|
| [eclipse-score-website](https://github.com/eclipse-score/eclipse-score-website) | (no description) |
| [eclipse-score-website-preview](https://github.com/eclipse-score/eclipse-score-website-preview) | (no description) |
| [eclipse-score-website-published](https://github.com/eclipse-score/eclipse-score-website-published) | (no description) |
| [eclipse-score.github.io](https://github.com/eclipse-score/eclipse-score.github.io) | The landing page website for the Score project |

---

### Uncategorized

Repositories that are not yet assigned to a dedicated category.

| Repository | Description |
|------------|-------------|
| [.eclipsefdn](https://github.com/eclipse-score/.eclipsefdn) | Repository to host configurations related to the Eclipse Foundation. |
| [bazel-tools-python](https://github.com/eclipse-score/bazel-tools-python) | Repository for python static code checker |
| [dev_playground](https://github.com/eclipse-score/dev_playground) | Repository for developer tools and playground |
| [nlohmann_json](https://github.com/eclipse-score/nlohmann_json) | Nlohmann JSON Library |
| [score-crates](https://github.com/eclipse-score/score-crates) | Repository to provide a defined list of rust crates to be used as bzl_mods |
