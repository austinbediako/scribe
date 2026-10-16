# Scribe — agent context & project state

Private leadership-coaching web app. Meetings are captured via **Recall.ai bots** (Google Meet / Zoom / Teams / Webex), transcripts are analyzed for observable leadership behaviors, and users get a weekly coaching card (strength / growth area / evidence / micro-action) plus per-meeting insight cards.

This file is the source of truth for "what happened and why" — keep it updated when making significant changes.

---

## Deployment topology (production)

| Piece | Where | URL |
|---|---|---|
| Frontend (Vite/React static) | Vercel project `scribe`, team `kaeytees-projects` | https://scribe-livid.vercel.app (alias: scribe-kaeytees-projects.vercel.app) |
| Backend (FastAPI) | Render web service `scribe-api`, **free plan** | https://scribe-api-yk5t.onrender.com |
| Database | Render free Postgres `scribe-db` (1 GB, **expires 30 days after creation**) | wired via `DATABASE_URL` env |
| Recall webhook | Recall dashboard → `https://scribe-api-yk5t.onrender.com/api/webhooks/recall` | replaces ngrok in prod |
| Repo | GitHub `austinbediako/scribe` (private), branch `main` | push to main auto-deploys Vercel; Render via blueprint |

### Deployment gotchas (learned the hard way)

- **Render free plan = ephemeral filesystem.** SQLite on prod was wiping *everything* on every 15-min-idle spin-down (accounts, captures, meetings all gone). That's why `render.yaml` now provisions free Postgres `scribe-db` and wires `DATABASE_URL` via `fromDatabase`. **Never go back to SQLite on Render.**
- **A "Manual Deploy" on the Render service does NOT apply blueprint `databases:` blocks.** To create/update the Postgres or env from `render.yaml`, use Blueprints → Sync/Apply.
- **Free Postgres expires 30 days after creation** (+14-day grace). For anything serious, move `DATABASE_URL` to an external Postgres (Neon/Supabase) or pay for Render's starter.
- **Env var changes on Vercel don't retroactively apply** — a rebuild is required. Push a commit or redeploy after changing `VITE_API_BASE_URL`.
- **Render appends a random suffix to hostnames** (`scribe-api` → `scribe-api-yk5t`). Don't hardcode the clean name anywhere; the actual URL lives in `VITE_API_BASE_URL` + `PUBLIC_API_BASE_URL` + `render.yaml`.
- **Blueprint `sync:false` env vars** (`GRANOLA_API_KEY`, `RECALL_API_KEY`, `RECALL_WORKSPACE_VERIFICATION_SECRET`) must be entered manually in the Render dashboard — they are never committed.

## Frontend config

- `client/` uses **pnpm** (not npm). `pnpm install`, `pnpm run build`. `pnpm-workspace.yaml` has `allowBuilds: { esbuild: true }` — required or esbuild's postinstall is blocked.
- `VITE_API_BASE_URL` (set on Vercel prod+preview) → backend base URL. Unset → relative `/api`, and `client/vite.config.js` proxies `/api` + `/ws` to `127.0.0.1:8000` for local dev.
- `client/vercel.json` is **only** the SPA fallback — no `/api` or `/ws` proxying (that hack was removed; the frontend calls the backend directly cross-origin).
- WebSocket URL is derived from `VITE_API_BASE_URL` (`https`→`wss`) via `wsUrl()` in `api.js`.

## Auth & security rules that must not regress

- All `/api/meetings/*`, `/api/actions*`, `/api/insights/*`, `/api/integrations/recall/*` endpoints require `get_current_user` and filter by `user.id`. Anonymous access must return 401/404 — never leak other users' data.
- `POST /api/integrations/granola/sync` still has the demo-user fallback (documented demo path) — the only place anonymous writes can happen.
- In `api.js`, 401s clear the token + fire `scribe:unauthorized` → logout — **except** `/auth/login` and `/auth/signup`, which must stay on the auth page and show the error inline. Don't broaden this exemption.
- Passwords: PBKDF2-HMAC-SHA256 (`core/security.py`). Tokens: SHA256-hashed in `AccessToken`, 30-day expiry.
- Capture consent (`consent_confirmed: true`) is mandatory — never bypass it.

## Meeting public IDs

- `Meeting.public_id` = `"mtg-" + secrets.token_urlsafe(6)` — the value shown in URLs (`/app/meetings/mtg-xxx`).
- All meeting endpoints accept public_id **or** numeric id. `init_db` backfills missing public_ids on startup.
- **Both** serializers must include `public_id`: `routes/meetings.py` AND `routes/websocket.py::_serialize_meetings`. (A WS push once stripped it and URLs regressed to numeric.)

## Insights

- `GET /api/insights/current` → **idempotent weekly card**: returns existing insight generated this ISO week (`_current_week_start` in `insight_service.py`), else creates one from all the user's `BehaviorObservation`s.
- `GET /api/meetings/{id}/insight` → **ephemeral per-meeting card**, computed from that meeting's observations only. Does NOT create `WeeklyInsight` rows — don't change that or meeting previews pollute weekly history.
- Frontend `Insights.jsx` has a `This week / By meeting` toggle + searchable meeting picker.

## Timeline (`MeetingTimeline.jsx` + `NoteDetail.jsx`)

- Speaker events come from Recall's `speaker_timeline_download_url` (fetched client-side). Each participant gets a **deterministic color** (`speakerColor()` palette in `NoteDetail.jsx`) via an event-level `color` override.
- Layout: **single fixed-height track** (72px). Each speaker occupies an invisible horizontal band; markers stagger vertically. Names appear on hover tooltip + details strip — never as lane labels (grew unbounded with speaker count).
- The fabricated "Bot scheduled/joined/recording" markers were removed — events must come from real data only.
- Ruler ticks are colored by the speaker active at that interval (`tickColor`).

## Frontend quirks worth knowing

- **Custom router** — `window.history.pushState` in `App.jsx`, no router lib. Routes: `/`, `/signin`, `/signup`, `/app`, `/app/meetings/{id}`, `/app/insights`, `/app/captures`.
- **Data loading**: `loadNotes()` runs on any `/app*` route; the WS (`/ws?token=`) stays connected while in-app and pushes `connected`/`meetings.updated`/`capture.updated`. (A previous bug: effects only ran on `/app`, so refreshing `/app/captures` showed nothing forever.)
- **Mobile**: sidebar hides ≤768px; a `position:fixed` bottom tab bar (Meetings/Captures/Insights) replaces it. `.app` uses `100dvh` — plain `100vh` puts the bar under mobile browser chrome.
- Granola was removed from the UI surface (empty-state copy, status pill, landing footnote, `api.sync`). The **backend** Granola sync endpoint still exists but nothing in the client calls it.
- Design skills installed: `.windsurf/skills/apple-design`, `.windsurf/skills/anti-slop`. Follow them for UI work — flat surfaces, one accent (`--purple`/`--purple-soft`), no gradient slop, no fake links, custom inline SVGs only (no external image URLs).

## Backend layout

- `app/api/routes/` — auth, meetings, insights, actions, captures (+ Recall webhook at `POST /api/webhooks/recall`), websocket, granola sync, calendars.
- `app/services/` — `analysis_service` (deterministic substring matching — **not an LLM**, don't claim otherwise), `insight_service`, `granola_sync_service`, `recall_capture_service`.
- `db/session.py` normalizes `postgres://` → `postgresql+psycopg://` (Render's URL format). `psycopg[binary]` is the driver.
- `pyproject.toml` includes `httpx2` — looks suspicious but is required by Starlette's TestClient.
- Recall capture pipeline: `POST captures` → bot scheduled → webhook `recording.done` → `start_recall_transcription` → `transcript.done` → `process_recall_transcript` creates Meeting + TranscriptSegments (`granola_meeting_id="recall:{bot_id}"`) → auto-analyze + WS broadcasts. Webhook signature (Svix headers) verified via `RECALL_WORKSPACE_VERIFICATION_SECRET`.

## Verify before shipping

```bash
cd server/backend && .venv/bin/python -m pytest -q   # 32 tests, all must pass
cd client && pnpm run build                           # must be green
```

- Backend tests are isolated via `tests/conftest.py` (temp SQLite) — never point it at the dev DB.
- Local venv lives at `server/backend/.venv` (python3.13); if broken, rebuild: `python3.13 -m venv .venv && pip install -e .`
- Commits go straight to `main` and push (auto-deploys Vercel). No PR workflow established.

## Known remaining gaps

- `PATCH /api/actions/{id}` works but micro-action lifecycle is minimal.
- Webhook jobs are non-durable `BackgroundTasks` — a restart mid-processing loses them.
- `CalendarConnection` stores OAuth secrets as plaintext.
- Analysis is keyword matching, not ML — confidence is hardcoded.
- Free-tier cold starts (~1 min after 15 min idle) can delay the first Recall webhook; Recall retries handle it, but the first capture after idle may lag.
