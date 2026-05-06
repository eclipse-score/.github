---
applyTo: '**/*.java'
---

# Java Spring Boot Guidelines

## Prerequisites
- Java 17 or later

## Project Structure
Follow **package-by-feature** then **package-by-layer**:
- `module/api/controllers/` -- HTTP layer
- `module/api/dtos/` -- Request/Response records
- `module/domain/services/` -- Business logic
- `module/domain/repositories/` -- Data access
- `module/domain/entities/` -- JPA entities
- `module/domain/mappers/` -- DTO-Entity conversion
- `module/domain/exceptions/` -- Custom exceptions
- `module/config/` -- Configuration classes

## Spring Boot Rules
1. **Constructor injection only** -- no `@Autowired`, no field injection
2. **Transactional boundaries** on service layer:
   - `@Transactional(readOnly=true)` for reads
   - `@Transactional` for writes
   - Keep transactions short
3. **No JPA entities in web layer** -- use dedicated Request/Response records with Jakarta Validation
4. Custom Spring Data JPA methods with JPQL over long derived query names
5. Use Command objects for create/update operations passed to service layer
6. **Typed configuration** via `@ConfigurationProperties` with validations
7. Global exception handling: `@RestControllerAdvice` + `@ExceptionHandler` returning consistent `ErrorResponse` DTO
8. SLF4J logging only -- never `System.out.println()`
9. **No Lombok**

## Database Schema
- Flyway migrations in `src/main/resources/db/migration`
- Naming: `V{version}__{description}.sql`
- Hibernate `ddl-auto=validate`
- Single coherent migration per ticket with rollback script
- Sequential versions, no gaps
- Keep test data out of production migrations

## Query Practices
- Prevent extra queries; consolidate
- Prefer derived queries / JPQL before native SQL
- Use projections or DTO queries to limit data transfer
- Profile query count for complex operations

## Collections & Streams
- Minimize passes; combine filtering & mapping
- Use typed collections; avoid duplicate traversals
- `Stream.toList()` for immutable; `Collectors.toCollection(ArrayList::new)` for mutable
- Extract complex stream chains into named methods
- Favour unmodifiable collections for read-only views

## Null Handling
- `Optional` at API boundaries, not internal fields
- `Objects.requireNonNull` for mandatory constructor params
- Extract potentially null-derived values once

## Configuration Management
- Externalize via `application.yml` + environment variables
- Remove hard-coded profiles from base YAML
- Centralize versions in BOM repository

## Modern Java 17+ Features
- **Records** for DTOs and value objects — prefer `record` over POJO for immutable data carriers
- **Sealed classes** for restricted type hierarchies — use `sealed` + `permits` for domain models with fixed subtypes
- **Pattern matching** with `instanceof` — eliminate explicit casts
- **Text blocks** for multi-line strings (SQL, JSON templates)
- **Switch expressions** — use `->` syntax with exhaustive matching

## Immutability
- Return `List.copyOf()`, `Map.copyOf()`, `Set.copyOf()` from public methods
- Use `Collections.unmodifiable*` for internal views
- Mark fields `final` by default
- Prefer records over mutable POJOs for data transfer

## Security
- **No hardcoded secrets** — use Spring Cloud Config, Vault, or environment variables
- **Parameterized queries only** — never concatenate SQL strings
- **Input validation** at controller layer using Jakarta Bean Validation (`@Valid`, `@NotNull`, `@Size`)
- **No sensitive data in logs** — mask PII, tokens, passwords
- **CORS and CSRF** configured explicitly in `SecurityFilterChain`
- **Dependency scanning** — OWASP Dependency-Check in CI pipeline

## Testing
1. **TDD mandatory**: RED → GREEN → REFACTOR for new features and bug fixes
2. **Unit tests**: isolation with mocks, prefer real dependencies where possible
3. **Integration tests**: Testcontainers for real DB, message brokers
4. Given-When-Then pattern, AssertJ assertions
5. `BaseIT.java` + `TestcontainersConfiguration.java` pattern
6. Min 80% code coverage; 100% for security-critical code
7. Descriptive test names explaining what is verified
8. JaCoCo for coverage enforcement in CI
