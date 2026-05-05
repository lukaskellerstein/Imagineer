# Feature Specification: [FEATURE NAME]

**Feature Directory**: [feature-directory-path]
**Created**: [DATE]
**Status**: Draft
**Input**: User description: "[USER'S RAW DESCRIPTION OR LINK TO INPUT FILE]"

## Clarifications

*(Populated during specification when [NEEDS CLARIFICATION] markers are resolved, and again by `/speckit.clarify` if invoked. Each entry: question, chosen answer, rationale.)*

## User Scenarios & Testing *(mandatory)*

### User Story 1 — [Short title] (Priority: P1)

[1–2 sentences describing the user, what they want, and why.]

**Why this priority**: [What value this story delivers; why P1 (cannot ship without it).]

**Independent Test**: [How this story can be tested in isolation, without later stories.]

**Acceptance Scenarios**:

1. **Given** [precondition], **When** [action], **Then** [observable outcome].
2. **Given** [...], **When** [...], **Then** [...].

### User Story 2 — [Short title] (Priority: P2)

[Same structure.]

### User Story 3 — [Short title] (Priority: P3)

[Same structure.]

### Edge Cases

- [Edge case 1 — what should the system do?]
- [Edge case 2]

## Requirements *(mandatory)*

### Functional Requirements

Group by capability. Every `FR-###` MUST be testable and unambiguous. Use `MUST` / `SHOULD` / `MAY` per RFC 2119.

**[Capability A]**

- **FR-001**: System MUST [...]
- **FR-002**: System MUST [...]

**[Capability B]**

- **FR-010**: System MUST [...]

### Non-Functional Requirements

- **NFR-001**: [Performance / availability / privacy / accessibility target]
- **NFR-002**: [...]

### Key Entities *(include if feature involves data)*

- **[Entity name]**: [Purpose, key attributes, relationships — no DB schema yet]

## Success Criteria *(mandatory)*

### Measurable Outcomes

Each criterion MUST be measurable, technology-agnostic, and verifiable by a non-technical stakeholder.

- **SC-001**: [Outcome with concrete metric — e.g., "Customers complete the upload-to-approval flow in under 5 minutes for 90% of orders"]
- **SC-002**: [...]

## Assumptions *(optional but recommended)*

- [Defaults applied where the input was silent — surface them so the user can correct]

## Dependencies *(optional)*

- [External services, models, datasets, or upstream features this depends on]

## Out of Scope *(optional but recommended)*

- [Explicit non-goals — things a reader might assume are included but are not, this release]
