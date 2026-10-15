# Scribe Backend Plan

## Goal

Build the backend for Scribe as an evidence-first service that ingests Granola meeting data, stores normalized records, analyzes leadership behaviors, and exposes private APIs for weekly leadership insights.

## Product constraints from the PRD

- Primary data source: Granola API
- Future optional integration: Empactify
- MVP must be a standalone app
- Use an existing AI model; do not train a model from scratch
- Keep observations grounded in evidence and abstain when data is insufficient
- Default privacy: insights are private to the user
- Handle oversized or missing transcript data gracefully
- Support idempotent sync and avoid duplicate meetings

## Recommended architecture

### Stack

- Backend: Python + FastAPI
- Database: PostgreSQL
- ORM: SQLAlchemy
- Migrations: Alembic
- Validation: Pydantic
- HTTP client: HTTPX
- Testing: Pytest
- Optional async tasks: Celery / Redis
- Secrets: environment variables or cloud secret manager

### High-level flow

1. User authenticates to Scribe
2. Backend requests Granola data using authorized credentials
3. Meeting records and transcript data are normalized
4. Transcript evidence is analyzed for leadership behaviors
5. Behavior observations are stored with evidence references
6. Weekly insight is generated with strength, growth area, evidence, and micro-action
7. Frontend retrieves meetings and insights through Scribe APIs

## Core backend modules

### 1. API layer

Responsibilities:
- health endpoint
- authentication and authorization
- meeting retrieval endpoints
- sync endpoints
- analysis trigger endpoints
- insight retrieval endpoints
- micro-action updates

Proposed endpoints:
- GET /health
- POST /api/integrations/granola/sync
- GET /api/meetings
- GET /api/meetings/{meeting_id}
- POST /api/meetings/{meeting_id}/analyze
- GET /api/insights/current
- GET /api/insights
- GET /api/insights/{insight_id}
- PATCH /api/actions/{action_id}

### 2. Granola integration layer

Responsibilities:
- authenticate with Granola
- retrieve meeting list and details
- retrieve transcript data when available
- handle pagination
- handle oversized responses and documented upstream errors
- map upstream schema to internal schemas
- retry transient failures with bounded backoff

Rules:
- validate all external payloads before use
- never expose API keys or transcript contents to clients
- treat missing transcripts as valid business state

### 3. Persistence layer

Core entities:
- User
- Meeting
- TranscriptSegment
- BehaviorObservation
- WeeklyInsight
- MicroAction

Database principles:
- stable upstream IDs for dedupe
- one user has many meetings
- one meeting has many transcript segments
- one meeting can produce many observations
- one insight can reference multiple observations

### 4. Analysis layer

Responsibilities:
- identify leadership behaviors from transcript evidence
- validate speaker attribution
- distinguish observed behavior from interpretation
- abstain when data is insufficient
- attach evidence references to each observation

Initial behavior categories:
- open-ended questions
- direct instruction or guidance
- recognition of contributions
- inviting perspectives
- exploring options before deciding

The analysis layer should be conservative. A missing or weak evidence trail is a valid result, not a failed analysis.

### 5. Insight generation layer

Responsibilities:
- aggregate observations over a relevant time period
- extract a strength
- identify a growth area
- include supporting evidence
- generate a practical micro-action
- produce a structured output for the frontend

Output requirements:
- strength
- growth area
- evidence summary
- micro-action
- status metadata and confidence indicators if applicable

### 6. Security and privacy layer

Responsibilities:
- enforce per-user authorization
- never log secrets or full transcripts
- store credentials on backend only
- minimize retention of raw transcript data
- ensure private insights are not exposed across users
- validate any AI-generated content before persistence

## Execution plan

### Phase 1: Foundation and contract validation

Build the base backend structure:
- FastAPI application skeleton
- Postgres + SQLAlchemy setup
- Alembic migrations
- environment configuration
- auth scaffolding
- health endpoint
- base project directories and test layout

Deliverable:
- the app boots cleanly and can connect to PostgreSQL locally

### Phase 2: Granola ingestion

Implement:
- Granola client and authentication
- meeting list retrieval
- meeting detail retrieval
- transcript retrieval
- pagination handling
- retry and timeout handling
- deduped sync behavior
- ingestion status tracking

Deliverable:
- a user can sync Granola meetings into Scribe without duplicate records

### Phase 3: Data normalization and storage

Implement:
- normalized meeting schema
- transcript storage
- source metadata retention
- speaker attribution representation
- missing/unknown speaker states
- reprocessing support without duplicate data

Deliverable:
- meeting data is stored in a predictable internal shape

### Phase 4: Leadership behavior analysis

Implement:
- transcript parsing and chunking
- evidence extraction logic
- speaker validation
- candidate behavior detection
- insufficient evidence handling
- observation persistence

Deliverable:
- meeting analysis produces behavior observations with traceable evidence

### Phase 5: Weekly insight generation

Implement:
- rolling analysis window logic
- aggregation across meetings
- strength/growth selection
- micro-action generation
- insight persistence
- insight retrieval API

Deliverable:
- one weekly insight can be generated and consumed by the frontend

### Phase 6: Hardening and QA

Implement:
- API auth checks and ownership rules
- unit tests for normalization and validation logic
- integration tests for sync and analysis flows
- AI quality tests with reviewed transcript examples
- privacy and logging review
- error handling and idempotency checks

Deliverable:
- MVP is stable, testable, and safe for demo use

## Project structure

```text
app/
  api/
    deps.py
    routes/
      health.py
      meetings.py
      insights.py
      actions.py
  core/
    config.py
    security.py
  db/
    base.py
    session.py
    models/
    migrations/
  integrations/
    granola/
      client.py
      schemas.py
      service.py
  services/
    sync_service.py
    analysis_service.py
    insight_service.py
  schemas/
    meeting.py
    observation.py
    insight.py
    action.py
  tests/
    unit/
    integration/
```

## Engineering principles

- Validate external data before using it
- Prefer evidence-backed conclusions over inferred certainty
- Design for idempotent reprocessing
- Keep the leadership framework explicit and versioned
- Write tests for the critical data lifecycle: sync -> normalize -> analyze -> insight
- Separate AI-generated output from deterministic domain logic as much as possible

## Risks to watch

- Granola API contract and auth flow may not match assumptions
- transcript data may be incomplete or missing speaker attribution
- oversized transcript payloads may require a special retrieval path
- AI may hallucinate unsupported claims if not constrained by evidence
- duplicate syncs may create duplicate meetings or insights if IDs are not stable

## Recommended first milestone

The first milestone should be:

1. bootable FastAPI app
2. PostgreSQL connection and models
3. Granola sync client
4. normalized meeting storage
5. a single analysis pass over a sample transcript
6. one weekly insight generation output
7. API endpoints for meetings and insights

This delivers the real MVP without prematurely solving Empactify or broader product expansion.

## Next step

Start by creating the backend project skeleton and the core database models, then move into the Granola connector and sync flow.
