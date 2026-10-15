# Scribe

**Scribe** is a leadership coaching web app that turns meeting data into evidence-based leadership insights and practical micro-actions for individual leaders. It captures two sources of meeting data:

1. **Granola** — meeting notes/transcripts synced from the user's account.
2. **Recall (Bot capture)** — opt-in bot joins Google Meet / Zoom / Teams / Webex meetings via a scheduled capture, with a full recorded video and transcript imported after the meeting.

The app then normalizes meeting data, runs an evidence-first analysis engine that labels observable leadership behaviors with supporting evidence, and generates a "weekly insight card" containing one strength, one growth area, supporting evidence, and one micro-action.

See `server/prd.md` for the full product requirements document and `server/plan.md` for the architecture/build plan. `server/frontend-handoff.md` documents the API contract for the frontend and known backend caveats.

---

## Product at a glance

- **Primary user:** an individual leader who wants private, practical feedback on communication/leadership behaviors across meetings.
- **Core principle:** "Granola captures meeting information. Scribe turns that information into evidence-based leadership insights and practical actions."
- **Evidence-first, no invented quotes:** observations carry `evidence_text` from real transcript segments; the engine abstains (`insufficient_evidence`) rather than fabricate.
- **Private by intent:** insights, meetings, observations are per-user; tokens are role-scoped server-side.
- **Micro-actions:** users can mark recommended actions planned/completed/dismissed/reflected (status patch persists today).
- **Meeting playback:** NoteDetail page plays the Recall recording with an interactive timeline (BOT/EVENTS/LOGS tracks, markers, keyboard shortcuts) and a transcript; clicking markers or timestamps seeks the video.

---

## High-level architecture

```
┌────────────────────┐        scheduled captures / webhook events
│  Recall.ai API     │◄──────────────────────────────────────┐
│  (bot capture)     │                                       │
└─────────┬──────────┘                                       │
          │  webhook → /api/webhooks/recall (public ngrok)    │
          ▼                                                  │
┌─────────────────────────────────────────────┐              │
│  FastAPI backend (server/backend/, port 8000)│              │
│  ├─ auth.py        (token-based JWT-like)   │              │
│  ├─ granola_sync_service (Granola API/notes)│              │
│  ├─ recall_capture_service (Recall bot/video)│              │
│  ├─ analysis_service (behavior labels)       │              │
│  ├─ insight_service (weekly insight cards)    │              │
│  ├─ captures.py, calendars.py               │              │
│  ├─ websocket.py (real-time sync push)       │              │
│  └─ SQLite DB (default) / PostgreSQL         │              │
└───────────────┬─────────────────────────────┘              │
                │ /api/* (proxied)                             │
                ▼                                              │
┌─────────────────────────────────────────────┐              │
│  React + Vite client (client/, port 5173)   │              │
│  ├─ pages: Landing / Auth / NotesList /      │              │
│  │  NoteDetail (with MeetingTimeline) /      │              │
│  │  Insights / Captures (MeetingCapturePanel)│              │
│  └─ /ws WebSocket for live sync              │              │
└─────────────────────────────────────────────┘              │
```

---

## Repository structure

```
scribe/
├── README.md                      # this file (root)
├── scribe.db                       # local SQLite DB (dev)
├── .venv/                          # Python venv at root (shared)
├── client/                        # React + Vite frontend
│   ├── index.html
│   ├── vite.config.js             # proxy /api and /ws -> :8000
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx                # routing incl. /app/captures, /app/insights
│   │   ├── api.js                 # API client
│   │   ├── styles.css             # global styles incl. MeetingTimeline CSS
│   │   ├── utils.js
│   │   └── components/
│   │       ├── Auth.jsx           # login/signup
│   │       ├── Landing.jsx
│   │       ├── TopBar.jsx / Sidebar.jsx
│   │       ├── NotesList.jsx / NoteDetail.jsx
│   │       ├── MeetingTimeline.jsx # playback timeline (BOT/EVENTS/LOGS)
│   │       ├── Insights.jsx
│   │       ├── MeetingCapturePanel.jsx  # Captures page UI
│   │       └── icons.jsx
├── server/
│   ├── prd.md                     # product requirements
│   ├── plan.md                    # build plan
│   ├── frontend-handoff.md        # API contract + caveats
│   └── backend/                   # FastAPI backend (dedicated README)
│       ├── README.md              # Granola/Recall deep-dive
│       ├── pyproject.toml
│       ├── .env / .env.example     # config
│       ├── app/
│       │   ├── main.py            # FastAPI app + CORS
│       │   ├── core/config.py     # settings (Pydantic)
│       │   ├── core/security.py
│       │   ├── db/models.py       # SQLAlchemy entities
│       │   ├── db/session.py
│       │   ├── api/deps.py        # get_current_user etc.
│       │   ├── api/routes/*.py    # all endpoints
│       │   └── services/*.py      # business logic
│       └── tests/                 # pytest (isolated via conftest)
└── update.pdf                     # latest design update (reference)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite 5 |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| DB | SQLite in dev (`scribe.db`), PostgreSQL recommended in prod |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic (available; current dev uses `init_db`) |
| Validation | Pydantic v2 |
| HTTP | HTTPX (Granola + Recall) |
| Tests | Pytest (+ pytest-asyncio) |
| Realtime | fastapi WebSocket |
| Deploy (local tunnels) | ngrok |

---

## Quickstart — run everything locally

### Prerequisites
- Node.js 18+ (developed on Node 24)
- Python 3.11+ with a venv at project root (`.venv/bin/python`)
- `ngrok` installed (for Recall webhooks; a public URL is required)

### 1. Backend
```bash
cd server/backend
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Health: `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`
- Docs: `http://127.0.0.1:8000/docs`

### 2. Frontend
```bash
cd client
npm install        # first time
npm run dev         # http://localhost:5173
```
Vite proxies `/api` and `/ws` to the backend.

### 3. ngrok (required for Recall webhooks locally)
```bash
ngrok http 8000
```
Then put the public URL (e.g. `https://xxxx.ngrok-free.dev`) into the backend `.env` as `PUBLIC_API_BASE_URL` and configure the same as a Recall webhook endpoint at `<public-url>/api/webhooks/recall` (headers `webhook-id/timestamp/signature` verified inside the backend).

Restart/re-run all three anytime — recommended cleanup first:
```bash
pkill -f "uvicorn app.main:app"; pkill -f "vite"; pkill -f "ngrok"
```

---

## Configuration (`server/backend/.env`)

See `.env.example` for the template. Key settings:

| Var | Purpose |
|---|---|
| `DATABASE_URL` | SQLite default `sqlite:///./scribe.db`; use Postgres in prod |
| `USE_DEMO_DATA` / `GRANOLA_API_KEY` / `GRANOLA_API_BASE_URL` | Granola sync (`false` + a real key = live) |
| `RECALL_REGION` / `RECALL_API_BASE_URL` / `RECALL_API_KEY` | Recall region & credentials (region must match key) |
| `RECALL_WORKSPACE_VERIFICATION_SECRET` (alias `RECALL_WEBHOOK_SECRET`) | Verify Recall webhook signatures |
| `PUBLIC_API_BASE_URL` | Public HTTPS URL Recall uses to POST webhooks; must not be localhost |

Note: backend resolves `.env` from CWD. Run uvicorn with CWD `server/backend` for env to be picked up.

---

## External references

### Products & providers integrated
- **Granola API**: https://docs.granola.ai/introduction — notes (`GET /v1/notes` cursor pagination, page size max 30), note details with `include=transcript`, oversized transcript fallback `GET /notes/{note_id}/transcript` (page size max 100). 5 req/s sustained, 25 req/5s burst. Client paces to this.
- **Recall.ai API**: https://us-east-1.recall.ai/api/v1 (hosted per region) — bot scheduling, recording retrieval, calendar connections, transcription, participant events/speaker timeline. Dashboard (keys + webhook secret): https://us-east-1.recall.ai/dashboard/developers/api-keys
- **ngrok**: https://ngrok.com/docs — local tunnel for Recall webhooks during dev.

### Stack / framework docs
- **FastAPI**: https://fastapi.tiangolo.com/
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **SQLAlchemy 2**: https://docs.sqlalchemy.org/en/20/
- **Alembic**: https://alembic.sqlalchemy.org/
- **Uvicorn**: https://www.uvicorn.org/
- **Pytest**: https://docs.pytest.org/
- **React 18**: https://react.dev/
- **Vite**: https://vitejs.dev/
- **HTTPX**: https://www.python-httpx.org/

### Product docs already in repo
- `server/prd.md` — full PRD (requirements, data model, acceptance, risks)
- `server/plan.md` — phased build plan
- `server/frontend-handoff.md` — API contract + caveats (as of 2026-10-14)
- `server/backend/README.md` — Granola & Recall capture deep-dive

---

## Backend API (summary)

All routes live in `server/backend/app/api/routes/`. Base URL `http://127.0.0.1:8000`. No `/api/v1` prefix today.

### Auth
- `POST /api/auth/signup` (and `/register`) — `{email, password}` → `{access_token, token, token_type, user}`
- `POST /api/auth/login`, `POST /api/auth/token` (OAuth2 form) → same
- `GET /api/auth/me` (Bearer) → `{id, email}`

### Status
- `GET /health` → `{status: "ok"}`
- `GET /api/status` → `{hasApiKey, demo_mode}`

### Granola sync
- `POST /api/integrations/granola/sync` — sync meetings for current (or demo) user
- WebSocket `/ws?token=` — emits `connected`, `meetings.updated`, `capture.updated` (30s periodic auto-sync)

### Meetings (Granola + Recall-capture imported)
- `GET /api/meetings` — list (newest first), per-user scoped
- `GET /api/meetings/{id}` — meeting + transcript segments (also returns transcript array)
- `GET /api/meetings/{id}/transcript` — `{meeting_id, segments, transcript}`
- `POST /api/meetings/{id}/analyze` — `{meeting_id, status, observation_count, observations[], metrics {talk_time_ms_by_speaker}}`
- `GET /api/meetings/{id}/video` — (Recall only) signed download URL + `speaker_timeline_download_url`

### Insights
- `GET /api/insights/current` — generates & returns current insight card `{id, strength, growth_area, evidence_summary, micro_action, status, micro_action_id}`
- `GET /api/insights` — list history (newest first)
- `GET /api/insights/{id}` — one insight (includes `generated_at`)

### Micro-actions
- `GET /api/actions` — list
- `PATCH /api/actions/{id}` — `{status}` (optional body; defaults to `completed`) → `{id, status, message}`

### Recall captures
- `POST /api/integrations/recall/captures` — `{title, meeting_url, join_at?, consent_confirmed}` (consent must be true; URL must be supported host + https). join_at defaults to now+1min; cannot be in the past
- `GET /api/integrations/recall/captures` — list user's captures
- `DELETE /api/integrations/recall/captures/{id}` — cancel scheduled capture
- `POST /api/integrations/recall/calendars` — connect Google/Outlook calendar `{platform, oauth_client_id, ...}`
- `GET /api/integrations/recall/calendars`
- `GET /api/integrations/recall/calendars/{id}/events?updated_at_gte=`
- `POST /api/integrations/recall/calendars/{id}/events/{event_id}/schedule` — `{consent_confirmed}`
- `DELETE /api/integrations/recall/calendars/{id}`
- `POST /api/webhooks/recall` — Recall webhook ingress (signature verified via Svix headers)

Capture lifecycle statuses: `scheduling` → `scheduled` → `joining` / `in_call_recording` → `post_processing` → `done` → transcript imported; failed states for errors. Transitions are broadcast over WebSocket so the UI updates in real time.

---

## Data model (key entities)

- `User` (id, email, password_hash, granola_user_id)
- `AccessToken` (token_hash, created_at; 30-day expiry)
- `Meeting` (granola_meeting_id unique, title, times, user_id; source inferred by `recall:` prefix)
- `TranscriptSegment` (meeting_id, speaker_name/id, text, start_time_ms/end_time_ms)
- `BehaviorObservation` (meeting_id, behavior_label, evidence_text, confidence, is_supported)
- `WeeklyInsight` (user_id, meeting_id, strength, growth_area, evidence_summary, micro_action, generated_at)
- `MicroAction` (insight_id, title, status, created/updated_at)
- `MeetingCapture` (user_id, title, meeting_url, join_at, consent, recall_bot_id, recall_recording_id, recall_transcript_id, meeting_id, status, …)
- `RecallWebhookEvent` (event_id PK, capture_id, event_type, received_at) — dedupe
- `CalendarConnection` (user_id, provider, recall_calendar_id, platform_email, status)

---

## Frontend routes

- `/` — Landing
- `/signin`, `/signup` — Auth
- `/app` — Meetings list (default view)
- `/app/meetings/{id}` — NoteDetail: video player (top) + transcript + MeetingTimeline (below video)
- `/app/insights` — Insights view
- `/app/captures` — Captures page: schedule new capture (title/URL/join_at/consent), list upcoming/past captures, calendar integration, cancel scheduled

Navigation via custom `window.history.pushState` inside React (no router lib).

---

## Key services (server/backend/app/services)

- `granola_client.py`, `granola_sync_service.py` — Granola HTTP client + sync/dedupe, transcript pagination (413 fallback).
- `recall_capture_service.py` — Recall client (schedule/cancel/transcribe/retrieve bot/calendar); webhook verification; status transitions; transcription + transcript import; broadcasts.
- `analysis_service.py` — behavior label detection: `asks_open_questions`, `gives_direct_instructions`, `recognizes_contributions`, `invites_perspectives`, `explores_alternatives`, `insufficient_evidence`.
- `insight_service.py` — `generate_weekly_insight_for_user(db, user_email)` returns the insight card dict; aborts with `insufficient_evidence` status when no evidence.
- Config `app/core/config.py` — Pydantic settings, Recall/Granola settings.

---

## Testing

Run from `server/backend/`:
```bash
. .venv/bin/activate
pytest -q              # isolated DB via tests/conftest.py
```
- Latest known: backend has 16 passed + 3 xfailed (as of prior frontend-handoff note); broader recent run reports ~30 tests passing.
- xfail notes (expected): talk-time metrics, authenticated insight privacy, persisted action completion — these are documented backend follow-ups, not failures. Treat as next work, not regressions.
- Test isolation: `tests/conftest.py` redirects `DATABASE_URL` to a temp sqlite DB so tests never wipe dev data. Do not modify it to point at real dev DB.

---

## Known limitations / next work (from PRD + frontend-handoff)

Open gaps that any agent can pick up next:

1. **Auth scoping on insights** — `GET /api/insights`, `GET /api/insights/{id}` are currently global, not owner-scoped (backend follow-up). Frontend should not promise privacy until fixed.
2. **Weekly insight idempotency** — `GET /api/insights/current` generates a new row each call; convert to stable weekly read/generate semantics.
3. **Action persistence** — `PATCH /api/actions/{id}` is stubbed; doesn't verify existence before writing (now partly real: returns 404 on missing). Make durable.
4. **CORS** — configured for localhost dev; adjust for deployed origins.
5. **Transcript endpoint for UI** — yes exists (use it; frontend NoteDetail uses `/api/meetings/{id}` now which also returns `transcript`).
6. **Video signed URL expiry & speaker timeline** — `/api/meetings/{id}/video` returns `download_url` + `speaker_timeline_download_url`; frontend timeline should fetch the speaker timeline from that URL (currently partially wired).
7. ** talk-time-by-speaker** — backend returns `metrics.talk_time_ms_by_speaker` but UI may not yet display; PRD asks for conditional (only when timing data exists).
8. **Granola scopes** — note scopes must include intended notes; verify with a live key.
9. **Durable task queue** — webhook jobs run as FastAPI `BackgroundTasks`; production should use Celery/Redis for recovery across restarts.
10. **Migrations** — Alembic present but dev uses init_db; productionize.
11. **Recall calendar OAuth refresh** stores client secret in DB as plain text — should be secured.
12. **Timeline visual polish** — MeetingTimeline under video verified; check interactive seek/timestamp click wiring end-to-end.

### Design references
- The root `README.md` (now this file) replaces the outdated minimal version. `update.pdf` is the latest design update — reference when matching visual style.
- UI style: light Apple-like Scribe (purple/white, rounded corners, soft shadows) existing design tokens in `client/src/styles.css`.

---

## Dev runtime facts (current session)

- Backend (uvicorn) on `:8000` (log: `/tmp/backend.log`)
- Frontend (vite) on `:5173` (log: `/tmp/vite.log`)
- ngrok public URL: `https://swell-reexamine-divisive.ngrok-free.dev` forwarded to `:8000` (this changes if tunnel restarts — update `.env` + Recall dashboard)
- `.env` already configured with `USE_DEMO_DATA=false` and a real Granola key + Recall credentials.

vite proxy: `/api` → `http://127.0.0.1:8000`; `/ws` → WS same.

---

## Further documentation (split by area)

- Client: `client/README.md`
- Backend ops: `server/backend/docs/operations.md`
- Backend deep-dive: `server/backend/README.md`
- Component contracts: `docs/components/` (MeetingTimeline, NoteDetail, MeetingCapturePanel, recall_capture_service)

## Notes for agents picking this up

- Don't touch `tests/conftest.py` isolation behavior.
- Don't expose secrets (Granola/Recall keys) in frontend — all live in backend `.env` only.
- Keep changes consistent with existing style/naming in surrounding files; prefer `edit` for targeted changes.
- Build/verify: frontend `npm run build`, backend `pytest -q` should be green before testing.
- Recall supports only Google Meet / Zoom / Teams (live+webex) meeting URLs; validated in `CaptureRequest.meeting_url_must_be_supported`.
- Consent (`consent_confirmed: true`) is mandatory for both manual captures and calendar scheduling — never auto-capture without it.
- Scheduled/recent captures live on a dedicated `Captures` page (`/app/captures`); opening a meeting shows it in NoteDetail.

### Project naming
- "finishing it off anytime" — contributors want any break-point to be re-enterable: services are stateless-ish, SQLite DB persisted at `server/backend/scribe.db`, all config in `.env`. Kill/restart services cleanly with `pkill` then launch as above.
