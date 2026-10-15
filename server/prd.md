# Scribe — Product Requirements Document (PRD)

**Product:** Scribe  
**Document:** Backend Product Requirements Document  
**Version:** 1.0  
**Status:** Draft  
**Date:** 14 October 2026  
**Primary Integration:** Granola API  
**Future Integration:** Empactify

---

## 1. Executive Summary

Scribe is a leadership coaching application built on meeting data from Granola.

The application retrieves meeting information available to an authorized user, analyzes meeting transcripts for evidence of leadership behaviors, and generates private weekly insight cards containing a strength, a growth area, supporting evidence, and a practical micro-action.

Scribe aims to help leaders understand their communication patterns and make incremental improvements to their leadership behavior.

The initial product will operate as a standalone application. Its backend will integrate with Granola, process meeting data, run leadership behavior analysis using an existing AI model, persist insights, and expose APIs for the frontend.

Future iterations may integrate with Empactify to transform selected insights into learning posts, training modules, surveys, polls, and reports, subject to the availability of supported integration interfaces.

### Core Product Principle

**Granola captures meeting information. Scribe turns that information into evidence-based leadership insights and practical actions.**

---

## 2. Problem Statement

Leaders participate in meetings regularly, but meeting notes alone do not necessarily help them understand how they communicate, involve others, recognize contributions, or balance questions with instructions.

Scribe addresses this gap by analyzing available meeting data and identifying observable leadership behaviors.

Instead of providing generic meeting summaries, Scribe delivers concise, personalized insights that help leaders recognize potential strengths, identify opportunities for growth, and experiment with practical behavioral changes.

Insights must be grounded in available evidence and must not present uncertain AI interpretations as definitive facts.

---

## 3. Product Vision

Help leaders turn everyday meetings into opportunities for personal leadership development.

Scribe will establish a continuous reflection process:

1. Retrieve authorized meeting data from Granola.
2. Normalize meeting notes and available transcript information.
3. Identify candidate leadership behaviors.
4. Evaluate patterns across relevant meetings.
5. Generate personalized weekly insights.
6. Recommend a practical micro-action.
7. Allow users to reflect on and track their actions over time.

---

## 4. Goals and Non-Goals

### 4.1 Goals

The initial release must:

- Connect securely to the Granola API.
- Retrieve available meeting notes and transcripts.
- Handle pagination and incomplete or oversized transcript responses.
- Normalize meeting information into consistent internal structures.
- Analyze observable leadership behaviors using a defined framework.
- Use an existing AI model rather than train a model from scratch.
- Associate generated observations with supporting evidence.
- Generate structured weekly insight cards.
- Store meeting data, observations, insights, and micro-actions.
- Provide backend endpoints for the frontend.
- Keep personal leadership insights private to the relevant user by default.
- Support a standalone demonstration before any Empactify integration.

### 4.2 Non-Goals

The initial release will not:

- Train a foundation model or fine-tune a model from scratch.
- Replace Granola's meeting capture or transcription capabilities.
- Recreate Empactify's existing AI learning companion.
- Directly publish posts, training modules, polls, surveys, or reports to Empactify without a supported integration mechanism.
- Automatically send private leadership insights to a user's manager.
- Diagnose personality or make definitive judgments about leadership ability.
- Calculate precise talk-time metrics when reliable speaker attribution and timing data are unavailable.

---

## 5. Target Users

### 5.1 Primary User: Individual Leader

A leader who wants private, practical feedback about communication and leadership behaviors across meetings.

### 5.2 Secondary Stakeholders

**Frontend Developer**

Consumes Scribe's APIs to display meetings, evidence, weekly insights, and micro-actions.

**Product Team**

Defines the leadership behavior framework, validates AI-generated insights, and evaluates the user experience.

**Future Empactify Users**

May benefit from selected insights being converted into learning resources when a supported integration becomes available.

---

## 6. Core User Journey

1. The user obtains authorized access to Granola.
2. Scribe retrieves meeting information available to the connected account.
3. The backend identifies meetings within the relevant analysis period.
4. Meeting details and available transcript data are retrieved.
5. The backend validates and normalizes the data.
6. Meeting records and transcript segments are stored.
7. The analysis engine identifies candidate leadership behaviors.
8. Supporting evidence is associated with each observation.
9. The insight generator identifies a potential strength, growth area, and micro-action.
10. A validated weekly insight card is saved.
11. The frontend retrieves and displays the insight.
12. The user reviews the evidence and decides whether to try the recommended micro-action.

---

## 7. Functional Requirements

Priority definitions:

- **P0:** Required for the initial working demonstration.
- **P1:** Important follow-up capability.
- **P2:** Future enhancement.

### 7.1 Granola API Integration

**FR-001 — Authentication (P0)**

The backend must authenticate with Granola using a server-side API key.

**FR-002 — Meeting Retrieval (P0)**

The backend must retrieve meeting notes available to the authorized Granola account.

**FR-003 — Individual Meeting Retrieval (P0)**

The backend must retrieve details for an individual meeting using its Granola identifier.

**FR-004 — Transcript Retrieval (P0)**

The backend must retrieve transcript information using the supported API mechanism when available.

**FR-005 — Pagination (P0)**

The backend must support pagination when retrieving meeting lists.

**FR-006 — Missing Transcripts (P0)**

The backend must handle meetings without available transcripts without failing the entire ingestion process.

**FR-007 — Large Transcripts (P0)**

The backend must handle oversized transcript responses, including documented HTTP 413 responses, using the appropriate supported retrieval mechanism.

**FR-008 — Incremental Synchronization (P1)**

The backend should support retrieving newly available meetings without repeatedly processing the entire history.

**FR-009 — Duplicate Prevention (P1)**

The backend should prevent duplicate meeting records when synchronization is repeated.

**FR-010 — Error Handling (P0)**

The backend must handle authentication failures, rate limits, timeouts, and upstream service errors.

It must return safe, understandable error messages without exposing credentials or sensitive transcript information.

> **Implementation requirement:** Verify endpoint names, request parameters, response structures, pagination, transcript access, and account restrictions against the current official Granola documentation before implementation.

### 7.2 Meeting Data Normalization and Storage

**FR-011 — Normalization (P0)**

The backend must transform available Granola meeting data into a consistent internal schema.

**FR-012 — Source References (P0)**

Each meeting record must retain its source identifier and any relevant source references.

**FR-013 — Transcript Storage (P0)**

The backend must store available transcript information according to the defined retention policy.

**FR-014 — Speaker Attribution (P0)**

The backend must explicitly represent missing, incomplete, or uncertain speaker attribution.

**FR-015 — Processing Status (P1)**

The backend should track ingestion status, analysis status, and relevant timestamps.

**FR-016 — Reprocessing (P1)**

The backend should support reprocessing meeting data without creating duplicate records.

#### Proposed Data Entities

- `User`
- `Meeting`
- `TranscriptSegment`
- `BehaviorObservation`
- `WeeklyInsight`
- `MicroAction`

The final schema must be based on the verified Granola payload and the selected database.

### 7.3 Leadership Behavior Analysis

**FR-017 — Behavior Framework (P0)**

The analysis engine must evaluate transcript content against a documented leadership behavior framework.

**FR-018 — Behavior Identification (P0)**

The engine must identify candidate behaviors such as:

- Asking open-ended questions.
- Giving instructions.
- Acknowledging or recognizing contributions.
- Inviting other perspectives.
- Exploring alternatives before making decisions.

These behaviors must only be identified when sufficient evidence exists.

**FR-019 — Supporting Evidence (P0)**

Each observation must include supporting evidence or a reference to the relevant transcript segment when available.

**FR-020 — Observation and Interpretation (P0)**

The engine must distinguish directly observable behavior from AI-generated interpretation.

**FR-021 — Uncertainty Handling (P0)**

The engine must represent uncertainty and abstain when evidence is insufficient.

**FR-022 — Speaker Validation (P0)**

The engine must not attribute behavior to a leader when the relevant utterance cannot reasonably be attributed to that person.

**FR-023 — Pattern Recognition (P1)**

The engine should identify recurring patterns across multiple meetings rather than treating isolated statements as definitive indicators.

**FR-024 — Confidence Assessment (P1)**

The engine should include confidence indicators and quality checks for generated observations.

The leadership framework must define each behavior explicitly to reduce inconsistent or unsupported classifications.

### 7.4 Talk-Time and Transcript Metrics

**FR-025 — Talk-Time Estimation (P1)**

Scribe may estimate talk time when reliable speaker attribution and timing information are available.

**FR-026 — Question-to-Instruction Analysis (P1)**

Scribe may calculate question-to-instruction ratios using a defined and validated utterance classification method.

**FR-027 — Insufficient Data (P0)**

The backend must indicate when a metric cannot be calculated reliably because the required data is missing or incomplete.

Transcript-based estimates must not be presented as precise measurements unless the underlying data supports that precision.

### 7.5 Weekly Insight Generation

**FR-028 — Weekly Insights (P0)**

The backend must generate a weekly insight card when sufficient meeting evidence is available.

**FR-029 — Insight Structure (P0)**

Each insight card must contain:

- One strength.
- One growth area.
- Supporting evidence.
- One practical micro-action.

**FR-030 — Structured Output (P0)**

The backend must return insights in a validated structure suitable for frontend consumption.

**FR-031 — Evidence Integrity (P0)**

The system must not invent meetings, quotations, evidence, or behavioral observations.

**FR-032 — Insufficient Evidence (P0)**

When evidence is insufficient, the system must return an appropriate status or explanation rather than fabricate an insight.

**FR-033 — Historical Insights (P1)**

The system should retain historical insights for longitudinal reflection.

**FR-034 — Micro-Action Tracking (P1)**

The system should allow users to mark micro-actions as planned, completed, dismissed, or reflected upon.

### 7.6 Backend API

The following are proposed Scribe application endpoints. They are not Granola API endpoints.

| Method | Endpoint | Description | Priority |
|---|---|---|---|
| GET | `/health` | Check service health | P0 |
| POST | `/api/integrations/granola/sync` | Initiate meeting synchronization | P0 |
| GET | `/api/meetings` | List the current user's imported meetings | P0 |
| GET | `/api/meetings/{meeting_id}` | Retrieve a meeting and its processing status | P0 |
| POST | `/api/meetings/{meeting_id}/analyze` | Request meeting analysis | P0 |
| GET | `/api/insights/current` | Retrieve the current weekly insight | P0 |
| GET | `/api/insights` | List historical insights | P1 |
| GET | `/api/insights/{insight_id}` | Retrieve an insight and its evidence | P0 |
| PATCH | `/api/actions/{action_id}` | Update a micro-action's status | P1 |

Authentication and authorization must ensure that users can access only their own meetings, evidence, insights, and actions unless a separate permission model is explicitly implemented.

### 7.7 Future Empactify Integration

**FR-035 (P2)**

The architecture should separate leadership insight generation from future Empactify publishing functionality.

**FR-036 (P2)**

If supported integration interfaces become available, selected insights may be used to create:

- Learning posts.
- Training modules.
- Surveys.
- Polls.
- Reports.

**FR-037 (P2)**

Future publishing workflows should include user review, permission checks, and duplicate prevention.

Direct Empactify publishing is outside the initial standalone demonstration unless a supported integration mechanism is confirmed.

---

## 8. Non-Functional Requirements

### 8.1 Security and Privacy

- Store Granola API credentials exclusively on the backend.
- Use environment variables or a secrets manager for credentials.
- Never expose API keys to the browser or commit secrets to source control.
- Authenticate Scribe users.
- Enforce authorization on every user-owned resource.
- Keep leadership insights private to the relevant user by default.
- Collect and retain only the data required for the product's stated purpose.
- Define retention and deletion policies for transcripts, evidence, and insights.
- Avoid logging full transcripts or credentials.
- Process meeting information only with appropriate authorization.
- Communicate that transcript-derived observations may be incomplete or uncertain.

### 8.2 Reliability

- Handle API errors, timeouts, rate limits, pagination, and incomplete responses.
- Retry transient failures with bounded backoff.
- Avoid repeatedly retrying permanent authentication or validation errors.
- Make ingestion and analysis safe to retry.
- Track processing states and failures.
- Prevent duplicate meeting records and duplicate insight generation for the same user and analysis period, unless regeneration is explicitly requested.

### 8.3 Performance and Scalability

- Use asynchronous I/O for upstream API requests where appropriate.
- Avoid processing very large transcripts synchronously when doing so would create excessive latency.
- Introduce background processing when workload or response time justifies it.
- Apply request timeouts and reasonable transcript-size limits.

### 8.4 Maintainability

- Separate the Granola connector, normalization layer, analysis engine, insight generator, database operations, and API routes.
- Validate external responses and AI-generated outputs against explicit schemas.
- Version the leadership behavior framework.
- Write unit and integration tests for critical workflows.

---

## 9. Suggested Technology Stack

The following stack is a recommendation and should be aligned with the team's existing technical decisions.

| Layer | Suggested Technology | Purpose |
|---|---|---|
| Backend framework | Python + FastAPI | HTTP API and automatic API documentation |
| HTTP client | HTTPX | Asynchronous Granola API requests |
| Configuration | Pydantic Settings | Environment-based configuration |
| Database | PostgreSQL | Persistent relational storage |
| ORM | SQLAlchemy | Database access |
| Migrations | Alembic | Database schema evolution |
| AI analysis | Existing LLM API | Behavior classification and insight generation |
| Validation | Pydantic | Request and AI-output validation |
| Testing | Pytest | Unit and integration tests |
| Deployment | Team-approved hosting platform | Application hosting |

Training a model from scratch is not required for the initial release.

---

## 10. High-Level Data Flow

1. The user authenticates with Scribe.
2. The backend accesses Granola using authorized credentials.
3. Meeting records are retrieved, including additional pages where necessary.
4. Meeting details and available transcripts are fetched.
5. The normalization layer validates and transforms the data.
6. Meeting information is persisted with source references.
7. The analysis engine identifies candidate leadership behaviors.
8. Supporting evidence is associated with each observation.
9. The insight generator creates a validated weekly insight card.
10. The insight is stored and linked to relevant observations and meetings.
11. The frontend retrieves the insight through Scribe's API.
12. The user reviews the evidence and decides whether to act on the recommendation.

---

## 11. Acceptance Criteria

The initial backend demonstration is acceptable when:

1. The backend authenticates with Granola using an authorized API key.
2. The backend retrieves real meeting records available to the connected account.
3. Pagination is handled correctly.
4. Meeting details and available transcripts can be retrieved using the documented API methods.
5. Missing or oversized transcripts are handled without crashing the service.
6. Meeting records are normalized and persisted.
7. Repeated synchronization does not create duplicate meeting records.
8. Leadership behavior observations include traceable supporting evidence when adequate data exists.
9. The analysis engine abstains when speaker attribution or transcript content is inadequate.
10. A weekly insight can be generated with a strength, growth area, evidence, and micro-action.
11. The frontend can retrieve meetings and insights through Scribe's API.
12. One user cannot retrieve another user's private meetings or insights.
13. API keys and sensitive transcript content are not exposed in client responses or logs.
14. Automated tests cover the primary workflow and important error conditions.

---

## 12. Testing Strategy

### 12.1 Unit Tests

Test:

- Granola response normalization.
- Pagination handling.
- Transcript segment parsing.
- Speaker attribution validation.
- Leadership behavior classification.
- Insight schema validation.
- Authorization checks.
- Micro-action state transitions.

### 12.2 Integration Tests

Test:

- Granola authentication and meeting retrieval.
- Missing transcript handling.
- Oversized transcript handling.
- Database persistence.
- Duplicate-ingestion prevention.
- Insight generation from representative transcript fixtures.
- Frontend endpoint response contracts.

Use a controlled test account when available.

### 12.3 AI Quality Tests

Create a small, reviewed collection of representative transcript examples.

For each example, define expected behaviors and supporting evidence, including examples where the correct result is **insufficient evidence**.

Evaluate generated results for:

- Unsupported claims.
- Incorrect speaker attribution.
- Inconsistent behavior classification.
- Fabricated quotations.
- Poorly supported growth recommendations.
- Inappropriate certainty.

AI outputs must be evaluated for quality rather than accepted merely because they conform to a JSON schema.

---

## 13. Risks and Mitigations

| Risk | Potential Impact | Mitigation |
|---|---|---|
| Granola API access or plan limitations | Required meeting data may be inaccessible | Verify credentials, access scopes, and plan requirements early |
| Meeting notes available without full transcripts | Detailed behavioral analysis may be limited | Inspect actual responses and support insufficient-data states |
| Incomplete speaker attribution | Behaviors may be assigned to the wrong person | Validate speaker identity and abstain when uncertain |
| Missing timestamps | Talk-time calculations may be unreliable | Make time-based metrics conditional on data availability |
| Unsupported AI judgments | Reduced user trust | Require evidence, use a defined framework, and communicate uncertainty |
| Duplicate synchronization | Duplicate meetings or insight cards | Use stable identifiers and idempotent operations |
| Sensitive data exposure | Privacy and trust risks | Enforce access controls, minimize retention, and protect logs |
| Empactify interfaces unavailable | Future publishing functionality may be blocked | Keep the standalone demonstration independent |

---

## 14. Implementation Plan

### Phase 1: API Discovery and Connectivity

Tasks:

- Confirm Granola API access and credentials.
- Verify authentication and endpoint behavior.
- Inspect pagination and transcript response structures.
- Build the initial API client.
- Implement a health endpoint.
- Retrieve real meeting data.

**Exit criterion:** The backend can reliably retrieve authorized meeting data from Granola.

### Phase 2: Normalization and Persistence

Tasks:

- Define internal meeting and transcript schemas.
- Implement database models and migrations.
- Store meeting metadata and available transcript segments.
- Implement synchronization status.
- Prevent duplicate ingestion.

**Exit criterion:** Meetings can be synchronized, stored, and retrieved consistently.

### Phase 3: Evidence-Based Analysis

Tasks:

- Define the initial leadership behavior framework.
- Implement transcript processing and evidence extraction.
- Integrate an existing LLM where needed.
- Validate generated classifications.
- Implement uncertainty and abstention rules.

**Exit criterion:** The service returns testable behavior observations with supporting evidence.

### Phase 4: Weekly Insight Cards

Tasks:

- Aggregate observations across the defined weekly period.
- Generate strengths, growth areas, and micro-actions.
- Validate and persist insight cards.
- Expose the relevant endpoints.
- Implement historical retrieval if time permits.

**Exit criterion:** The frontend can display a complete insight card grounded in stored evidence.

### Phase 5: Hardening and Demonstration

Tasks:

- Add automated tests and error handling.
- Verify privacy and authorization.
- Test repeated synchronization.
- Test incomplete and unavailable transcript scenarios.
- Prepare a demonstration using real authorized data or clearly labeled fixtures.

**Exit criterion:** The complete workflow can be demonstrated reliably from Granola meeting data to a Scribe insight card.

---

## 15. Open Questions

The following questions must be resolved before the implementation is finalized:

1. Which backend language and framework has the team selected?
2. Does the team have a working Granola API key and an account with the necessary access?
3. Which transcript formats and speaker-attribution fields are returned by actual API responses?
4. Will the demo support one connected account or multiple Scribe users?
5. Which authentication method will Scribe use for its users?
6. Which LLM provider has the team approved, if any?
7. What leadership behavior framework will the first version use?
8. What retention and deletion policy will apply to transcripts and derived insights?
9. What are the hackathon's time constraints and minimum demonstration requirements?
10. Will future Empactify publishing use a supported API, an agent/tool interface, or another integration mechanism?

---

## 16. Official Reference

Granola API documentation:

https://docs.granola.ai/introduction

All endpoint names, parameters, authentication requirements, response formats, and access restrictions must be verified against the current official documentation and actual API responses.

---

## Appendix A: Illustrative Insight Card

### Strength: You invite perspectives before making decisions.

**Evidence:** In two reviewed meetings, you asked team members to identify risks before choosing an approach.

### Growth Area: Explore alternatives more consistently.

**Evidence:** In another discussion, you assigned a solution before inviting alternative suggestions.

### Micro-Action

Before deciding on a solution in your next meeting, ask:

"What alternatives should we consider?"

**Important:** This example is illustrative. Actual insights must be generated from authorized meeting data and linked to genuine supporting evidence. A small number of observations should not be treated as a definitive assessment of a person's leadership ability.