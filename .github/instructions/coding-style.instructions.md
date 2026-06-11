---
applyTo: '**'
---

# Coding Style — Eclipse S-CORE

## C++

- Follow the project's clang-tidy configuration from `score_cpp_policies`
- Use `const` by default for variables, parameters, and member functions
- Prefer value semantics; avoid raw pointers — use `std::unique_ptr`, `std::shared_ptr`
- Prefer `std::string_view`, `std::span` for non-owning references
- Use `std::optional` for values that may be absent
- Use `std::expected` or project error types instead of exceptions where module convention requires it
- No C-style casts — use `static_cast`, `dynamic_cast`, `reinterpret_cast`
- Header includes: project headers first, then third-party, then standard library
- Use include guards or `#pragma once` per project convention
- Avoid macros; use `constexpr`, templates, or inline functions instead
- No `using namespace std;` in headers

## Rust

- Follow the project's Clippy configuration from `score_rust_policies`
- Strict policy (`clippy/strict/clippy.toml`) for safety-critical code: no `panic!`, `unwrap()`, `expect()`
- Relaxed policy (`clippy/relaxed/clippy.toml`) for tooling and tests only
- Prefer `&str` over `String` for function parameters where ownership is not needed
- Use `Result<T, E>` for all fallible operations — propagate with `?`
- Derive traits (`Debug`, `Clone`, `PartialEq`) where appropriate
- Group imports: `std`, external crates, crate-internal — separated by blank lines
- Use `#[must_use]` on functions where ignoring the return value is likely a bug

## Python

- Format with `ruff format`; lint with `ruff check`
- Type-check with `basedpyright`
- `snake_case` for functions/variables, `CapWords` for classes
- Type hints on all public functions
- Imports: standard library, third-party, local — separated by blank lines
- Absolute imports only; no wildcard imports

## General

- Consistent indentation per language convention (project `.editorconfig` or formatter config)
- Max line length per formatter config
- No trailing whitespace
- Files end with a single newline
- Organize code by feature/domain, not by type
