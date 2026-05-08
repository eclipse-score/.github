---
agent: test-security
tools: ['vscode', 'execute', 'read', 'search', 'web']
description: 'Comprehensive security review of uncommitted changes. Checks for vulnerabilities, secrets, and OWASP Top 10 issues.'
---

Perform a comprehensive security scan on the current codebase or changed files.

## Scan Scope
- Default: Scan only files modified in the current branch vs base branch
- If user requests full scan: Scan entire `src/` directory

## Security Checks

### 1. Secrets Detection
- Scan for hardcoded API keys, passwords, tokens, connection strings
- Check patterns: `password=`, `secret=`, `api_key=`, `token=`, Bearer tokens, AWS keys
- Check `.env` files are in `.gitignore`
- Check no secrets in committed config files
- **Severity: CRITICAL** for any finding

### 2. OWASP Top 10
1. **Injection** — SQL, NoSQL, OS command injection via string concatenation
2. **Broken Auth** — Missing auth checks, weak session management
3. **Sensitive Data Exposure** — PII in logs, unencrypted sensitive data
4. **XXE** — Unsafe XML parsing
5. **Broken Access Control** — Missing authorization, IDOR vulnerabilities
6. **Security Misconfiguration** — Debug mode enabled, default credentials
7. **XSS** — Unsanitized user input in HTML/JS output
8. **Insecure Deserialization** — Untrusted data deserialized without validation
9. **Vulnerable Dependencies** — Known CVEs in dependencies
10. **Insufficient Logging** — Missing audit trail for security events

### 3. Input Validation
- All user inputs validated at API boundaries
- Parameterized queries only (no string-concatenated SQL)
- File path sanitization (no path traversal)
- Request size limits configured

### 4. Dependency Vulnerability Scan
- Python: `pip-audit --format=json`
- Rust: `cargo audit --json`
- Go: `nancy sleuth` or `nancy` CLI
- C++: OWASP Dependency-Check report
- Flag: Critical and High CVEs

## Findings Format
Present each finding as:

**Security Finding:**
- **File:** `path/to/file:L42`
- **Severity:** Critical | High | Medium | Low
- **Category:** Secrets | OWASP-# | Input Validation | Dependency
- **Description:** What was found
- **Risk:** What an attacker could exploit
- **Remediation:** How to fix

## Summary Report
| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Secrets | count | count | count | count |
| OWASP | count | count | count | count |
| Input Validation | count | count | count | count |
| Dependencies | count | count | count | count |

**Overall Security Status: PASS / FAIL**
- PASS: Zero Critical and High findings
- FAIL: Any Critical or High finding present

Save to: `.stage/<ISSUE-ID>/security-scan.md` if GitHub Issues context exists.

## Rules
- Always check for secrets FIRST — they are the most dangerous
- Reference `.github/instructions/security.instructions.md` for project standards
- Never approve code with unresolved Critical findings
- Present findings for user review — user decides on remediation
