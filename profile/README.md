# Welcome to eclipse-score

This Github organization contains artifacts developed by the [Eclipse S-CORE Project](https://projects.eclipse.org/projects/automotive.score).

## Introduction to Eclipse S-CORE Project

See [S-CORE-website](https://eclipse-score.github.io/) and [documentation](https://eclipse-score.github.io/score).

## Repositories in the Github organization

*Note: descriptions are taken from [IAC configuration](https://github.com/eclipse-score/.eclipsefdn/blob/main/otterdog/eclipse-score.jsonnet) and may not be up to date. Change them there, not here!*

### General

| Repository | Description | Status |
|------------|-------------|--------|
| [score](https://github.com/eclipse-score/score) | Score project main repository | ✅ active |
| [process_description](https://github.com/eclipse-score/process_description) | Score project process description | ✅ active |

---

### Website

| Repository | Description | Status |
|------------|-------------|--------|
| [eclipse-score.github.io](https://github.com/eclipse-score/eclipse-score.github.io) | The landing page website for the Score project | 💤 obsolete |
| [eclipse-score-website](https://github.com/eclipse-score/eclipse-score-website) | (no description) | ✅ active |
| [eclipse-score-website-preview](https://github.com/eclipse-score/eclipse-score-website-preview) | (no description) | ✅ active |
| [eclipse-score-website-published](https://github.com/eclipse-score/eclipse-score-website-published) | (no description) | 💤 obsolete |

---

### Modules (Dependable Elements)

| Repository | Description | Status |
|------------|-------------|--------|
| [baselibs](https://github.com/eclipse-score/baselibs) | base libraries including common functionality | ✅ active |
| [communication](https://github.com/eclipse-score/communication) | Repository for the communication module LoLa | ✅ active |
| [feo](https://github.com/eclipse-score/feo) | Repository for the Fixed Order Execution (FEO) framework | ✅ active |
| [itf](https://github.com/eclipse-score/itf) | Integration Testing Framework repository | ✅ active |
| [operating_system](https://github.com/eclipse-score/operating_system) | Repository for the module operating system | ✅ active |
| [orchestrator](https://github.com/eclipse-score/orchestrator) | Orchestration framework & Safe async runtime for Rust | ✅ active |
| [persistency](https://github.com/eclipse-score/persistency) | Repository for persistency framework | ✅ active |

---

### Incubation

| Repository | Description | Status |
|------------|-------------|--------|
| [bazel-tools-python](https://github.com/eclipse-score/bazel-tools-python) | Repository for python static code checker | ✅ active |
| [bazel-tools-cc](https://github.com/eclipse-score/bazel-tools-cc) | Repository for clang-tidy based static code checker | ✅ active |
| [inc_config_management](https://github.com/eclipse-score/inc_config_management) | Incubation repository for config management | 💤 obsolete |
| [inc_daal](https://github.com/eclipse-score/inc_daal) | Incubation repository for DAAL module | ✅ active |
| [inc_feo](https://github.com/eclipse-score/inc_feo) | Incubation repository for the fixed execution order framework | 💤 obsolete |
| [inc_json](https://github.com/eclipse-score/inc_json) | Incubation repository for JSON module | 💤 obsolete |
| [inc_mw_com](https://github.com/eclipse-score/inc_mw_com) | Incubation repository for interprocess communication framework | 🕓 stale |
| [inc_mw_log](https://github.com/eclipse-score/inc_mw_log) | Incubation repository for logging framework | 💤 obsolete |
| [nlohmann_json](https://github.com/eclipse-score/nlohmann_json) | Nlohmann JSON Library | ✅ active |
| [inc_os_autosd](https://github.com/eclipse-score/inc_os_autosd) | Incubation repository for AutoSD Development Platform | ✅ active |
| [inc_process_test_management](https://github.com/eclipse-score/inc_process_test_management) | Incubation repository for Process - Sphinx-Test management | 💤 obsolete |
| [inc_process_variant_management](https://github.com/eclipse-score/inc_process_variant_management) | Incubation repository for Process - Sphinx-Variant management | 💤 obsolete |
| [testing_tools](https://github.com/eclipse-score/testing_tools) | Repository for testing utilities | 🕓 stale |
| [lifecycle](https://github.com/eclipse-score/lifecycle) | Repository for the lifecycle feature | ✅ active |


---

### Infrastructure

#### Integration

| Repository | Description | Status |
|------------|-------------|--------|
| [reference_integration](https://github.com/eclipse-score/reference_integration) | Score project integration repository | ✅ active |
| [os_images](https://github.com/eclipse-score/os_images) | OS Images for testing and deliveries | ✅ active |
| [rules_imagefs](https://github.com/eclipse-score/rules_imagefs) | Repository for Image FileSystem Bazel rules and toolchains definitions | ✅ active |

#### Toolchains

| Repository | Description | Status |
|------------|-------------|--------|
| [bazel_platforms](https://github.com/eclipse-score/bazel_platforms) | Bazel platform definitions used by S-CORE modules | ✅ active |
| [toolchains_gcc](https://github.com/eclipse-score/toolchains_gcc) | Bazel toolchains for GNU GCC | ✅ active |
| [toolchains_gcc_packages](https://github.com/eclipse-score/toolchains_gcc_packages) | Bazel toolchains for GNU GCC | ✅ active |
| [toolchains_qnx](https://github.com/eclipse-score/toolchains_qnx) | Bazel toolchains for QNX | ✅ active |
| [toolchains_rust](https://github.com/eclipse-score/toolchains_rust) | Rust toolchains | ✅ active |
| [ferrocene_toolchain_builder](https://github.com/eclipse-score/ferrocene_toolchain_builder) | Builder for Ferrocene artifacts | ✅ active |
| [score_rust_policies](https://github.com/eclipse-score/score_rust_policies) | Centralized Rust linting and formatting policies for S-CORE, including safety-critical guidelines. | ✅ active |
| [score_cpp_policies](https://github.com/eclipse-score/score_cpp_policies) | Centralized C++ quality tool policies for S-CORE, including sanitizer configurations and safety-critical guidelines. | 💤 obsolete |
| [rules_rust](https://github.com/eclipse-score/rules_rust) | S-CORE fork of bazelbuild/rules_rust | ✅ active |

#### Tooling & Tool Provision

| Repository | Description | Status |
|------------|-------------|--------|
| [devcontainer](https://github.com/eclipse-score/devcontainer) | Common DevContainer for Eclipse S-CORE | ✅ active |
| [docs-as-code](https://github.com/eclipse-score/docs-as-code) | Docs-as-code tooling for Eclipse S-CORE | ✅ active |
| [tooling](https://github.com/eclipse-score/tooling) | Tooling for Eclipse S-CORE | ✅ active |
| [tools](https://github.com/eclipse-score/tools) | Home of score-tools, the new pypi based tools approach | 🕓 stale |
| [sbom-tool](https://github.com/eclipse-score/sbom-tool) | Home of the SBOM generation tool | ✅ active |
| [bazel_registry](https://github.com/eclipse-score/bazel_registry) | Score project bazel modules registry | ✅ active |
| [bazel_registry_ui](https://github.com/eclipse-score/bazel_registry_ui) | House the ui for bazel_registry in Score | 🕓 stale |
| [dash-license-scan](https://github.com/eclipse-score/dash-license-scan) | pipx/uvx wrapper for the dash-licenses tool | ✅ active |

#### Automation ("CI/CD")

| Repository | Description | Status |
|------------|-------------|--------|
| [apt-install](https://github.com/eclipse-score/apt-install) | GitHub Action to execute apt-install in a clever way | ✅ active |
| [more-disk-space](https://github.com/eclipse-score/more-disk-space) | GitHub Action to make more disk space available in Ubuntu based GitHub Actions runners | 🕓 stale |
| [cicd-workflows](https://github.com/eclipse-score/cicd-workflows) | Reusable GitHub Workflows for CI/CD automation | ✅ active |

#### Other

| Repository | Description | Status |
|------------|-------------|--------|
| [.eclipsefdn](https://github.com/eclipse-score/.eclipsefdn) | Repository to host configurations related to the Eclipse Foundation. | ✅ active |
| [module_template](https://github.com/eclipse-score/module_template) | C++ & Rust Bazel Template Repository | ✅ active |
| [.github](https://github.com/eclipse-score/.github) | Houses the organisation README | ✅ active |
| [infrastructure](https://github.com/eclipse-score/infrastructure) | All general information related to the development and integration infrastructure | ✅ active |

---