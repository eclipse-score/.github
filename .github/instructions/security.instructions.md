---
applyTo: '**'
---

# Security Guidelines — Eclipse S-CORE

## Mandatory Checks Before Every Commit

- [ ] No hardcoded secrets (API keys, passwords, tokens, private keys)
- [ ] No credentials in comments, log messages, or test fixtures
- [ ] All external inputs validated at system boundaries
- [ ] Memory safety verified (no buffer overflows, use-after-free, double-free)
- [ ] No undefined behavior in C++ code
- [ ] Error messages do not leak internal details or memory addresses

## Secret Management

- NEVER hardcode secrets in source code — use environment variables or secret managers
- NEVER commit `.env`, `credentials.json`, or key files
- Keep secret-containing files in `.gitignore`
- Rotate any secrets that may have been exposed

## Memory Safety (C++)

- Use RAII for all resource management
- Prefer smart pointers (`std::unique_ptr`, `std::shared_ptr`) over raw pointers
- Use `std::span` and `std::string_view` for bounds-safe access
- Run sanitizers in CI: ASan, UBSan, LSan, TSan (see `score_cpp_policies`)
- No `reinterpret_cast` without explicit justification
- No manual `new`/`delete` — use container types or smart pointers
- Validate array indices and buffer sizes at boundaries

## Memory Safety (Rust)

- No `unsafe` blocks without explicit justification and safety comments
- Minimize `unsafe` scope — wrap in safe abstractions
- All `unsafe` blocks must document why safety invariants are upheld
- Prefer `checked_add`, `checked_mul` over wrapping arithmetic for sizes/offsets

## Cryptography

- NEVER implement custom cryptographic algorithms
- Use established libraries (OpenSSL, BoringSSL, ring, RustCrypto)
- Use `std::random_device` or `getrandom` for security-sensitive randomness — not `rand()`
- TLS 1.2+ for all network communication

## Supply Chain Security

- Audit transitive dependencies regularly
- Use Dependabot / OWASP Dependency-Check for CVE scanning
- Pin dependency versions in `MODULE.bazel`
- Verify integrity of downloaded artifacts (checksums, signatures)

## Input Validation

- Validate all data from external sources (network, files, IPC)
- Check buffer sizes before copy operations
- Reject malformed input early — fail fast
- Never trust data from untrusted processes or external ECUs without validation

## Embedded / Automotive Specific

- No dynamic memory allocation in safety-critical paths after initialization
- Privilege isolation: separate safety-critical from non-critical components
- Communication channel authentication between ECUs
- Log security-relevant events for post-incident analysis
- Follow ISO 21434 (cybersecurity engineering) requirements where applicable

## Security Response Protocol

If a security issue is found during development:
1. STOP current work immediately
2. Assess severity (Critical / High / Medium / Low)
3. Fix CRITICAL issues before continuing any other work
4. Rotate any potentially exposed secrets
5. Report via SECURITY.md disclosure process
