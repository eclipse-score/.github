# Architecture Documentation

> **Generated**: [DATE]  
> **Project**: [PROJECT_NAME]  
> **Status**: Living Document

---

## Overview

### Project Name
[PROJECT_NAME]

### Purpose
Brief description of what this project does and its primary goals.

### Scope
What is included and excluded from this project.

---

## Architecture Style

### Primary Style
[e.g., Hexagonal, Layered, Clean Architecture, Modular Monolith, Microservices, Event-Driven]

### Rationale
Why this architectural style was chosen for this project. What problems does it solve? What trade-offs were made?

---

## System Context

### External Systems
List of external systems, services, or APIs this project integrates with:
- **[System Name]**: Purpose, protocol, and interaction pattern

### Users and Actors
Who interacts with this system and how:
- **[Actor Type]**: Description of their role and interactions

---

## Component Structure

### High-Level Components
Description of the major components or modules:

#### [Component Name]
- **Purpose**: What this component does
- **Responsibilities**: Key responsibilities
- **Dependencies**: What it depends on
- **Boundaries**: What it must not do or access

### Directory Structure
```
[Show relevant directory structure that reflects the architecture]
```

---

## Key Architectural Decisions

### Decision Registry
Reference to ADRs in `docs/adr/`.

### Critical Decisions
Summarize the most important architectural decisions from ADRs:

1. **[Decision Category]**: [Brief description]
   - See: ADR-NNN
   - Impact: [Why this matters]

2. **[Decision Category]**: [Brief description]
   - See: ADR-NNN
   - Impact: [Why this matters]

---

## Boundaries and Constraints

### Architectural Boundaries
Rules that must be enforced to maintain architectural integrity:

1. **[Boundary Name]**: [Rule description]
   - Example: "Domain layer must not import from infrastructure layer"
   - Enforced by: Architecture skill `/arch review`

### Technical Constraints
- **[Constraint Type]**: Description
- **[Constraint Type]**: Description

---

## Technology Stack

### Primary Stack
List core technologies and frameworks:
- **Language**: [e.g., Python 3.11+, TypeScript 5.x]
- **Framework**: [e.g., FastAPI, Express, React]
- **Database**: [e.g., PostgreSQL 15]
- **Infrastructure**: [e.g., Docker, Kubernetes]

### Supporting Tools
- **Testing**: [e.g., pytest, vitest]
- **Build**: [e.g., Vite, setuptools]
- **CI/CD**: [e.g., GitHub Actions]

### Technology Decision Rationale
Brief explanation of major technology choices and why they fit the architecture.

---

## API Design

### API Style
[REST, GraphQL, gRPC, Event-Driven, etc.]

### Endpoint Structure
High-level description of how APIs are organized:
- **Base URL**: [if applicable]
- **Versioning Strategy**: [e.g., URL path versioning: /api/v1/]
- **Authentication**: [e.g., JWT, OAuth 2.0]

### API Contracts
Location of API specifications:
- **OpenAPI/Swagger**: [path or URL]
- **GraphQL Schema**: [path]
- **Proto files**: [path]

---

## Data Architecture

### Data Model
High-level description of the domain model and key entities.

### Data Storage Strategy
- **Primary Database**: [Type and purpose]
- **Caching**: [Strategy and tools]
- **File Storage**: [If applicable]

### Data Flow
Describe how data moves through the system:
1. [Step 1]
2. [Step 2]
3. [Step 3]

---

## Testing Strategy

### Testing Approach
[Testing Trophy, Testing Pyramid, or custom approach]

### Test Categories
- **Unit Tests**: Scope and coverage goals
- **Integration Tests**: What integrations are tested
- **End-to-End Tests**: Critical user flows covered
- **Performance Tests**: [If applicable]

### Testing Tools
- [Tool 1]: Purpose
- [Tool 2]: Purpose

---

## Security Architecture

### Authentication & Authorization
- **Method**: [e.g., JWT, OAuth 2.0, SAML]
- **User Management**: [Approach]
- **Role-Based Access**: [If applicable]

### Security Boundaries
- **Input Validation**: Where and how
- **Data Encryption**: At rest and in transit
- **Secrets Management**: [Approach]

### Security Considerations
Key security patterns and practices applied in this project.

---

## Scalability & Performance

### Scalability Strategy
- **Horizontal Scaling**: [Approach]
- **Vertical Scaling**: [Considerations]
- **Load Balancing**: [Strategy]

### Performance Targets
- **Response Time**: [Target]
- **Throughput**: [Target]
- **Concurrent Users**: [Target]

### Caching Strategy
Where and how caching is applied to improve performance.

---

## Error Handling & Resilience

### Error Handling Strategy
[e.g., Result types, exceptions, error codes]

### Resilience Patterns
- **Retries**: [Policy]
- **Circuit Breakers**: [Where applied]
- **Fallbacks**: [Strategy]
- **Timeouts**: [Policy]

---

## Observability

### Logging
- **Strategy**: [Structured logging, log levels]
- **Location**: [Where logs are stored]
- **Tools**: [Logging framework/platform]

### Monitoring
- **Metrics**: Key metrics tracked
- **Dashboards**: [If applicable]
- **Alerting**: [Strategy]

### Tracing
- **Distributed Tracing**: [If applicable]
- **Tools**: [e.g., OpenTelemetry]

---

## Deployment Architecture

### Environments
- **Development**: Configuration and purpose
- **Staging**: Configuration and purpose
- **Production**: Configuration and purpose

### Infrastructure
- **Hosting**: [Cloud provider, on-premises]
- **Containerization**: [Docker, Podman]
- **Orchestration**: [Kubernetes, Docker Compose]

### CI/CD Pipeline
High-level description of the build, test, and deployment process.

---

## Development Workflow

### Branching Strategy
[e.g., Trunk-based, Git Flow, GitHub Flow]

### Code Review Process
Key aspects of the code review process, including architecture reviews.

### Architecture Reviews
How architectural decisions are reviewed:
- Use `/arch review` to check code against documented decisions
- Review task plans against architecture documentation

---

## Evolution and Maintenance

### Architecture Evolution Process
How architectural changes are proposed, discussed, and recorded:
1. Identify need for change
2. Use `/arch decide` to record new ADR
3. Update architecture documentation if needed
4. Communicate changes to team

### Periodic Reviews
- **Frequency**: [e.g., quarterly]
- **Process**: Use `/arch evolve` to identify drift and inconsistencies

### Technical Debt Management
Strategy for identifying, tracking, and addressing technical debt.

---

## References

### Architecture Decision Records
- **Location**: `docs/adr/`
- **Template**: See `adr-expert` skill
- **All ADRs**: [Link to ADR index]

### Architecture Documentation
- **File**: `.stage/docs/architecture.md`
- **Template**: See architecture skill assets

### Related Documentation
- API Documentation: [link]
- Developer Guide: [link]

---

## Appendix

### Glossary
Key terms and their definitions specific to this project.

### Diagrams
Links to or embedded C4 diagrams, sequence diagrams, or other visual representations:
- **System Context Diagram**: [link or embedded]
- **Container Diagram**: [link or embedded]
- **Component Diagram**: [link or embedded]

---

*This document is maintained by the project team and should be updated when significant architectural decisions are made. Use the architecture skill (`/arch`) to keep this document synchronized with ADRs.*
