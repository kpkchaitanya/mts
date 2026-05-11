# holistic-ai-product-management-framework.md

# Holistic AI-Native Product Management Framework
## Semantic Governance for AI-Native SDLC

---

## Governance Position

**Authority:** This document is the primary authority for product management and intent clarity within the MTS system.

**Position in the authority chain:**
```
Soul → Constitution → PM Framework (this document) → Agent Protocol → Spec → Eval → Workflow → Agents → Output
```

**Mandate:** Every feature spec produced in this system must trace upward through this framework. A spec that cannot be grounded in a properly decomposed INVEST story, a set of EARS requirements, and Gherkin acceptance scenarios is not eligible for implementation. Coding agents and pipeline agents must flag PM Framework violations before starting any implementation work.

**Primary guidance for:**
- Defining and validating product intent
- Decomposing business vision into implementable, traceable units
- Establishing requirements clarity before any agent acts
- Setting the semantic contract between business goals and technical specs

See `constitution.md` Section 6 (Authority Chain) and Section 9 (Governing Documents) for the formal governance record.

---

# 1. Purpose

This document defines the foundational principles, semantic hierarchy, decomposition strategies, and governance patterns for Product Management in AI-native software delivery systems.

Traditional SDLC primarily optimized for:
- human coordination
- Jira tracking
- sprint execution
- manual software development

AI-native SDLC must additionally optimize for:
- machine-consumable requirements
- AI-agent execution
- eval-driven development
- semantic traceability
- automated validation
- workflow orchestration
- runtime observability
- ontology-aligned knowledge systems

This framework establishes the semantic layering necessary for scalable AI-native development.

---

# 2. Core Philosophy

## Traditional Thinking

```text
Story = Requirement = Acceptance Criteria = Technical Design
```

This creates:
- ambiguity
- duplicated logic
- weak traceability
- implementation drift
- difficult automation
- poor AI-agent reliability

---

## AI-Native Thinking

```text
Business Intent
≠ User Story
≠ Requirement
≠ Validation
≠ Technical Design
≠ Eval
≠ Trace
```

Each layer has a distinct semantic purpose.

---

# 3. Core SDLC Hierarchy

```text
Business Vision
    ↓
Epic
    ↓
INVEST User Story
    ↓
EARS Requirements
    ↓
Gherkin Acceptance Scenarios
    ↓
Technical Stories
    ↓
Implementation
    ↓
Automated Tests
    ↓
Evals
    ↓
Execution Traces
    ↓
Observability & Governance
```

---

# 4. The Three Foundational Frameworks

| Framework | Purpose | Primary Focus | Audience |
|---|---|---|---|
| INVEST | Validate story quality | Business value & decomposition | PM / PO |
| EARS | Define system obligations | Requirements clarity | Architects / Analysts / AI |
| Gherkin | Validate observable behavior | Acceptance testing | QA / Automation |

---

# 5. INVEST Framework

## Purpose

INVEST ensures user stories are:
- properly decomposed
- estimable
- independently valuable
- testable

---

## INVEST Meaning

| Letter | Meaning |
|---|---|
| I | Independent |
| N | Negotiable |
| V | Valuable |
| E | Estimable |
| S | Small |
| T | Testable |

---

## Good User Story Example

```text
As a customer,
I want Klarna payments captured only after shipment,
so that I am charged accurately for fulfilled items.
```

---

## Common Violations

| Problem | Description |
|---|---|
| Large stories | Multiple architectural concerns mixed |
| Technical masquerading | Technical work disguised as business value |
| Hidden coupling | Dependency on unseen infrastructure |
| Cross-cutting duplication | Retry logic repeated everywhere |

---

# 6. EARS Framework

## Purpose

EARS (Easy Approach to Requirements Syntax) defines:
- system obligations
- conditions
- constraints
- behavioral rules

EARS improves:
- requirement precision
- AI readability
- ambiguity reduction
- traceability

---

# 7. EARS Core Principle

EARS answers:

```text
"What must the system do?"
```

---

# 8. EARS Patterns

| Pattern | Purpose | Example |
|---|---|---|
| Ubiquitous | Always true | The system shall encrypt passwords |
| Event-Driven | Trigger-based | When shipment confirms, system shall capture payment |
| State-Driven | State-sensitive | While session active, refresh token |
| Optional Feature | Conditional behavior | Where MFA enabled, require OTP |
| Unwanted Behavior | Failure handling | If timeout occurs, retry request |

---

# 9. Good EARS Example

```text
When a shipment is confirmed,
the system shall send a payment capture request.
```

---

# 10. EARS Characteristics

| Attribute | Description |
|---|---|
| Declarative | Defines obligations |
| Atomic | One rule per statement |
| Architecture-oriented | Focuses on system behavior |
| Machine-friendly | AI-readable |
| Concise | Minimal ambiguity |

---

# 11. Gherkin Framework

## Purpose

Gherkin defines:
- executable acceptance scenarios
- observable behaviors
- workflow validations

Most commonly used with:
- BDD
- Cucumber
- Playwright
- Cypress
- automation frameworks

---

# 12. Gherkin Core Principle

Gherkin answers:

```text
"How do we prove the system works?"
```

---

# 13. Gherkin Example

```gherkin
Scenario: Successful payment capture

Given a confirmed shipment for a Klarna order
When payment capture processing completes
Then the order shall be eligible for settlement
And the collection ticket shall close successfully
```

---

# 14. Good Gherkin Characteristics

| Attribute | Description |
|---|---|
| Observable | User/system-visible outcomes |
| Workflow-oriented | End-to-end scenarios |
| Executable | Automation-friendly |
| Validation-centric | Confirms expected behavior |

---

# 15. Bad Gherkin Example

```gherkin
Then capture_id is stored in paymentReference6
```

Problem:
- internal implementation detail
- not observable behavior

---

# 16. Better Gherkin

```gherkin
Then the order shall be available for reconciliation
```

---

# 17. Core Difference: EARS vs Gherkin

| EARS | Gherkin |
|---|---|
| Requirement language | Validation language |
| Defines obligations | Defines proof |
| Architecture-focused | Workflow-focused |
| Atomic rules | Scenario flows |
| Declarative | Behavioral |
| "System shall..." | "Given/When/Then..." |

---

# 18. Simple Analogy

| Concept | Analogy |
|---|---|
| EARS | Law |
| Gherkin | Court trial proving the law works |

---

# 19. AI-Native Decomposition Strategy

## User Stories Should Capture

- business value
- user outcomes
- capability intent

---

## EARS Requirements Should Capture

- obligations
- constraints
- triggers
- state behavior

---

## Gherkin Should Capture

- observable validation
- workflows
- acceptance behavior

---

## Technical Stories Should Capture

- implementation decomposition
- integrations
- orchestration
- infrastructure concerns

---

# 20. Recommended AI-Native Hierarchy

```text
EPIC
 ├── User Stories
 │
 ├── EARS Requirements
 │
 ├── Gherkin Acceptance Scenarios
 │
 ├── Technical Stories
 │
 ├── Shared Platform Requirements
 │
 ├── eval.md
 │
 └── trace.md
```

---

# 21. Shared Platform Requirements

Cross-cutting concerns should NOT be duplicated across stories.

---

## Examples

| Concern | Description |
|---|---|
| Idempotency | Duplicate prevention |
| Retry Policies | Network recovery |
| Queue Routing | Error handling |
| Correlation IDs | Distributed tracing |
| Replay Protection | Exactly-once semantics |
| Auditability | Regulatory traceability |
| Observability | Logging & metrics |
| Amount Conversion | Currency normalization |

---

# 22. Recommended Shared Governance Files

```text
/docs/governance/platform-requirements.md
/docs/governance/payment-platform-governance.md
/docs/governance/observability-governance.md
```

---

# 23. AI-Generated Story Smells

| Smell | Description |
|---|---|
| Mixed abstraction levels | Business + technical mixed together |
| Fake user stories | Platform concerns disguised as user value |
| Large stories | Too many responsibilities |
| Hidden dependencies | Coupling not visible |
| Internal Gherkin | Non-observable validations |
| Repeated logic | Retry/queue logic duplicated |

---

# 24. Technical Story Guidelines

## Good Technical Stories

Should focus on:
- integrations
- orchestration
- infrastructure capabilities
- implementation decomposition

---

## Avoid

Overly implementation-specific statements like:

```text
Modify XYZClass.java
```

Prefer:

```text
Extend payment dispatch logic to support Klarna routing.
```

This preserves:
- architectural flexibility
- refactoring freedom
- AI-agent adaptability

---

# 25. eval.md Philosophy

AI-native systems require measurable quality governance.

---

# Example Eval Categories

| Eval Category | Example |
|---|---|
| Functional Accuracy | Correct captures |
| Idempotency | No duplicate charges |
| Queue Routing | Correct failure handling |
| Reconciliation Accuracy | Feed correctness |
| Latency | API SLA |
| Retry Reliability | Recovery success |
| AI Accuracy | Requirement adherence |

---

# 26. trace.md Philosophy

Execution traces are first-class governance artifacts.

---

# Example Trace Fields

| Field | Purpose |
|---|---|
| order_id | Business correlation |
| shipment_id | Fulfillment correlation |
| capture_id | Payment correlation |
| correlation_id | Distributed tracing |
| queue_name | Operational routing |
| retry_count | Reliability analysis |
| workflow_step | Agent execution |
| eval_result | Runtime validation |

---

# 27. AI-Agent Readiness Principles

Well-structured AI-native systems allow agents to:
- independently implement
- independently validate
- independently evaluate
- independently trace
- independently replay
- independently observe

This requires semantic separation between:
- intent
- obligations
- validation
- implementation
- evaluation
- execution evidence

---

# 28. Product Management Evolution

## Traditional PM

Focused on:
- backlog tracking
- sprint coordination
- delivery management

---

## AI-Native PM

Focused on:
- semantic decomposition
- intent engineering
- eval-driven governance
- ontology alignment
- workflow orchestration
- AI-agent reliability

---

# 29. Recommended Repository Structure

```text
/docs
├── governance
│   ├── product-management
│   │   ├── holistic-ai-product-management-framework.md
│   │   ├── invest-framework.md
│   │   ├── ears-guidelines.md
│   │   ├── gherkin-guidelines.md
│   │   └── backlog-decomposition-strategy.md
│   │
│   ├── ai-sdlc
│   │   ├── eval-driven-development.md
│   │   ├── traceability-framework.md
│   │   └── observability-governance.md
│   │
│   ├── architecture
│   │   ├── ontology-framework.md
│   │   ├── workflow-orchestration.md
│   │   └── domain-driven-design.md
│   │
│   └── agent-governance
│       ├── context-engineering.md
│       ├── harness-engineering.md
│       └── workflow-governance.md
│
├── specs
├── workflows
├── evals
├── traces
└── ontology
```

---

# 30. Final Principle

Traditional repositories optimize for:

```text
Code Storage
```

AI-native repositories optimize for:

```text
Semantic Execution Systems
```

The future of AI-native SDLC is not:
- generating more Jira tickets

It is:
- building semantically layered, machine-consumable delivery systems capable of reliable AI-agent execution, validation, evaluation, tracing, and governance.