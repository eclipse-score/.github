---
description: 'Security review skill -- OWASP Top 10 checklist, secret detection patterns, dependency scanning, and remediation guidance.'
---

# Security Review Skill

This skill provides deep knowledge for security reviews. It is loaded on-demand when an agent or prompt needs to perform security analysis.

## When to Use
- During RELEASE stage: as part of code review security checks
- When user invokes `@security-review` agent
- When running `security-scan` prompt
- Before creating pull requests

## OWASP Top 10 Checklist

### 1. Injection (A03:2021)
**Check for:**
- SQL queries built with string concatenation or interpolation
- NoSQL queries with unvalidated user input
- OS command execution with user-supplied arguments
- LDAP queries with unsanitized input

**Remediation:**
- Use parameterized queries / prepared statements
- Use ORM methods instead of raw queries
- Validate and sanitize all input at API boundaries
- Use allowlists for command arguments

### 2. Broken Authentication (A07:2021)
**Check for:**
- Missing authentication on protected endpoints
- Weak password policies
- Session tokens in URLs
- Missing MFA for sensitive operations

**Remediation:**
- Enforce authentication at service boundaries
- Use established auth libraries (Spring Security, Passport.js, etc.)
- Store passwords with bcrypt or Argon2
- Implement rate limiting on auth endpoints

### 3. Sensitive Data Exposure (A02:2021)
**Check for:**
- PII in log statements
- Sensitive data in API responses (passwords, tokens, SSN)
- Unencrypted data at rest or in transit
- Sensitive data in error messages

**Remediation:**
- Mask PII in logs
- Use field-level encryption for sensitive data
- Enforce TLS for all communications
- Return generic error messages to clients

### 4. XML External Entities (A05:2021)
**Check for:**
- XML parsing with external entity expansion enabled
- DTD processing enabled

**Remediation:**
- Disable external entity processing in XML parsers
- Use JSON instead of XML where possible

### 5. Broken Access Control (A01:2021)
**Check for:**
- Missing authorization checks after authentication
- IDOR (Insecure Direct Object References)
- Privilege escalation paths
- Missing CORS configuration

**Remediation:**
- Implement role-based or attribute-based access control
- Validate resource ownership in every request
- Configure CORS explicitly (no wildcard origins)

### 6. Security Misconfiguration (A05:2021)
**Check for:**
- Debug mode enabled in production configs
- Default credentials in config files
- Verbose error responses with stack traces
- Unnecessary features or services enabled

**Remediation:**
- Use separate config profiles for dev/prod
- Remove default credentials
- Map exceptions to generic error responses
- Disable unused features

### 7. Cross-Site Scripting / XSS (A03:2021)
**Check for:**
- User input rendered in HTML without sanitization
- `innerHTML` or `dangerouslySetInnerHTML` with user data
- Template injection in server-side rendering

**Remediation:**
- Sanitize all user input before rendering
- Use framework-provided escaping (React auto-escapes by default)
- Implement Content Security Policy (CSP) headers

### 8. Insecure Deserialization (A08:2021)
**Check for:**
- Untrusted data deserialized without validation
- Java `ObjectInputStream` with untrusted input
- JSON deserialization to polymorphic types without type checking

**Remediation:**
- Validate serialized data before deserializing
- Use allowlists for deserialization types
- Prefer simple data formats (JSON with strict schemas)

### 9. Using Components with Known Vulnerabilities (A06:2021)
**Check for:**
- Outdated dependencies with known CVEs
- Transitive dependencies with vulnerabilities
- Unlicensed or abandoned packages

**Remediation:**
- Run `npm audit`, `pip-audit`, OWASP Dependency-Check
- Update vulnerable dependencies
- Pin versions in production

### 10. Insufficient Logging & Monitoring (A09:2021)
**Check for:**
- Missing audit trail for authentication events
- No logging of authorization failures
- Missing rate limiting or alerting

**Remediation:**
- Log all authentication attempts (success and failure)
- Log authorization failures with context
- Implement rate limiting and alerting

## Secret Detection Patterns
Scan for these regex patterns in source code:
- `password\s*=\s*['"][^'"]+['"]`
- `api[_-]?key\s*=\s*['"][^'"]+['"]`
- `secret\s*=\s*['"][^'"]+['"]`
- `token\s*=\s*['"][^'"]+['"]`
- `AKIA[0-9A-Z]{16}` (AWS Access Key)
- `Bearer\s+[A-Za-z0-9\-._~+/]+=*`
- Connection strings with embedded credentials

## Severity Classification
| Severity | Criteria | Action |
|----------|----------|--------|
| **Critical** | Exploitable remotely, no auth required, data breach risk | Block release, fix immediately |
| **High** | Exploitable with auth, privilege escalation, data leakage | Block release, fix before merge |
| **Medium** | Exploitable under specific conditions, limited impact | Fix recommended, can merge with tracking |
| **Low** | Informational, best practice violation, no direct exploit | Track for future improvement |
