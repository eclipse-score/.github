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
Reference to DRs in `docs/design_decisions/`.

### Critical Decisions
Summarize the most important architectural decisions from DRs:

1. **[Decision Category]**: [Brief description]
   - See: DR-NNN
   - Impact: [Why this matters]

2. **[Decision Category]**: [Brief description]
   - See: DR-NNN
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
- **Language**: [e.g., C++20, Rust, Go, Python 3.12]
- **Runtime / Middleware**: [e.g., ara::com integration, gRPC service, SOME/IP binding, custom service runtime]
- **Data Storage**: [e.g., none, SQLite for tooling metadata, PostgreSQL if required]
- **Target Platform**: [e.g., Linux, QNX, containerized tooling environment]

### Supporting Tools
- **Testing**: [e.g., bazel test, pytest, cargo test, GoogleTest]
- **Build**: [e.g., Bazel]
- **Documentation**: [e.g., Sphinx, sphinx-needs, PlantUML]
- **CI/CD**: [e.g., GitHub Actions invoking Bazel targets]

### Technology Decision Rationale
Brief explanation of major technology choices and why they fit the architecture.

---

## API Design

### API Style
[gRPC, ara::com, SOME/IP, event-driven messaging, CLI-only, or N/A]

### Endpoint Structure
High-level description of how APIs are organized:
- **Interface Boundary**: [service interface, topic, RPC contract, CLI surface, or N/A]
- **Versioning Strategy**: [e.g., interface version in IDL/package, semantic versioning, or N/A]
- **Access Control**: [e.g., platform permissions, mTLS, repository permissions, or N/A]

### API Contracts
Location of API specifications:
- **IDL / ARXML / Proto**: [path]
- **Interface headers**: [path]
- **Command-line contract**: [path or N/A]

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
- **Method**: [e.g., mTLS, repository permissions, platform identity, or N/A]
- **Principal Management**: [Approach]
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
- **Containerization**: [devcontainer, Docker, Podman, or N/A]
- **Execution Model**: [native process, ECU target, containerized tooling, or N/A]

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
2. Use `/arch decide` to record new DR
3. Update architecture documentation if needed
4. Communicate changes to team

### Periodic Reviews
- **Frequency**: [e.g., quarterly]
- **Process**: Use `/arch evolve` to identify drift and inconsistencies

### Technical Debt Management
Strategy for identifying, tracking, and addressing technical debt.

---

## References

### Decision Records
- **Location**: `docs/design_decisions/`
- **Template**: See `dr-expert` skill
- **All DRs**: [Link to design decision index]

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

*This document is maintained by the project team and should be updated when significant architectural decisions are made. Use the architecture skill (`/arch`) to keep this document synchronized with DRs.*
