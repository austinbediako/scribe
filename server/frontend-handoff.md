# Scribe Frontend Handoff

This document describes the backend contract and current integration boundaries for the frontend agent. It reflects the backend as implemented on 2026-10-14; it is not a promise that unfinished product features are available.

## Local Setup

From `backend/`:

```sh
. .venv/bin/activate
uvicorn app.main:app --reload
```

Base URL: `http://127.0.0.1:8000`

Health check: `GET /health` returns `{"status":"ok"}`. The API currently has no `/api/v1` prefix. FastAPI's interactive docs are available at `/docs` while the server is running.

The checked-in/local development configuration uses `USE_DEMO_DATA=true`. In demo mode, Granola sync returns local demo meeting/transcript data; it does not prove that a real Granola workspace is connected. Live Granola access requires a valid API key, `USE_DEMO_DATA=false`, and note scopes that include the intended notes. Never place the Granola key in frontend code.

## Implemented API

### Sync demo/Granola meetings

`POST /api/integrations/granola/sync`

No request body. Returns:

```json
{
  "status": "success",
  "synced_count": 1,
  "message": "Granola sync completed."
}
```

The route currently associates sync with the fixed backend user `demo@example.com`; it does not accept a signed-in user identity yet.

### List meetings

`GET /api/meetings`

Returns an array, newest first:

```json
[
  {
    "id": "1",
    "granola_meeting_id": "not_1d3tmYTlCICgjy",
    "title": "Leadership sync demo",
    "source": "granola",
    "started_at": "2026-10-14T09:00:00",
    "ended_at": "2026-10-14T09:30:00",
    "transcript_available": true
  }
]
```

Important: use `id` (Scribe's database ID) in the analyze route. `granola_meeting_id` is Granola's note ID. There is currently no API route to retrieve transcript text or meeting-level analysis detail except by calling analyze.

### Get a meeting

`GET /api/meetings/{meeting_id}`

Returns the same meeting object as the list item. Missing IDs return `404`.

### Analyze a meeting

`POST /api/meetings/{meeting_id}/analyze`

No request body. Returns evidence-based observations:

```json
{
  "meeting_id": "1",
  "status": "success",
  "observation_count": 1,
  "observations": [
    {
      "id": "1",
      "behavior_label": "asks_open_questions",
      "confidence": "high",
      "evidence_text": "What do you think about the launch plan?",
      "is_supported": true
    }
  ]
}
```

Current labels include `asks_open_questions`, `gives_direct_instructions`, `recognizes_contributions`, `invites_perspectives`, `explores_alternatives`, and `insufficient_evidence`. This is prototype pattern matching, not a validated leadership assessment. An insufficient-evidence observation has `is_supported: false` and should not be presented as a confident claim.

### Get current insight card

`GET /api/insights/current`

Returns one object with `id`, `strength`, `growth_area`, `evidence_summary`, `micro_action`, and `status` (`generated` or `insufficient_evidence`). For example:

```json
{
  "id": "1",
  "strength": "You consistently ask good clarifying questions before moving to a decision.",
  "growth_area": "You could balance questions with clearer decision framing so your team knows the next step.",
  "evidence_summary": "What do you think about the launch plan?",
  "micro_action": "Before your next team conversation, invite one additional perspective and close with the decision you intend to make.",
  "status": "generated"
}
```

Important backend behavior: this GET currently generates and saves a new insight each time observations exist; it is not a read-only fetch of a stable weekly card. Avoid polling it or invoking it repeatedly until the API is changed to an idempotent read/generate workflow.

### List/get insight history

- `GET /api/insights` returns an array of insight objects with the card fields, `status`, and `generated_at`.
- `GET /api/insights/{insight_id}` returns one insight object with the card fields and `status`; it currently omits `generated_at`.

Both currently query globally rather than by authenticated owner. Do not treat these routes as private-user-safe or expose real users' data through them yet.

### Micro-action status

`PATCH /api/actions/{action_id}` currently accepts no body and returns:

```json
{
  "id": "1",
  "status": "completed",
  "message": "Micro-action status updated."
}
```

This is currently a stub: it does not verify that the action exists or persist status. Do not show a durable completion state based solely on this response.

## Recommended Demo Flow

1. Call `POST /api/integrations/granola/sync`.
2. Load `GET /api/meetings` and show `transcript_available` as availability only; transcript content is not exposed by an endpoint.
3. Call `POST /api/meetings/{id}/analyze` for the selected meeting and render evidence with its label/confidence.
4. Call `GET /api/insights/current` only when intentionally generating a demo card; repeated calls currently create duplicate insight rows.

Handle empty arrays, `insufficient_evidence`, 404s, and failed sync/analyze requests as first-class UI states. Dates may be null. The backend does not currently provide pagination for its own meetings or insight history endpoints.

## Not Yet Implemented / Integration Caveats

- Authentication and authorization are absent. Routes do not identify the current leader, and insight list/detail are not owner-scoped. The requirement that insights are private is not met by the current API.
- CORS middleware is not configured. A browser app on another origin may be blocked until backend CORS is configured for the frontend's local/deployed origin.
- No talk-time-by-speaker metric or quantitative question/instruction ratios are returned.
- Action completion is not persisted.
- Weekly insight generation has no weekly date window or scheduled job; it counts existing observations.
- No transcript retrieval endpoint, Posts/Trainings/Surveys APIs, or Empactify integration exists yet.
- The Granola client follows the documented `/v1/notes` and transcript contract, but live authentication against the target workspace has not been verified.

Treat these boundaries as backend follow-up items, not frontend implementation bugs. Use mock/demo UI states for unavailable capabilities and avoid promising privacy or persisted actions until the backend adds and tests those contracts.

## Backend Verification

From `backend/`:

```sh
. .venv/bin/activate
pytest -q
```

Latest known result: `16 passed, 3 xfailed`. The expected failures document missing talk-time metrics, authenticated insight privacy, and persisted action completion.
