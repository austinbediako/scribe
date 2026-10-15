# Backend Operations Guide (`server/backend`)

## Running

```sh
cd server/backend
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Recreating the virtualenv

`.venv` is machine-local (absolute symlinks) — do not copy it between machines. If `.venv/bin/python` fails with "No such file or directory", rebuild it with Python 3.11+:

```sh
cd server/backend
rm -rf .venv
python3.13 -m venv .venv   # or any python3.11+
.venv/bin/pip install -e .
```

### Frontend dependencies

`client/` uses pnpm (`pnpm install`, `pnpm run build`). Do not pin platform-specific binaries (`@esbuild/darwin-x64`, `@rollup/rollup-darwin-x64`) in `package.json` — esbuild and rollup resolve the correct arch binary automatically via their own optional dependencies.

Health `GET /health`, docs `/docs`. Env loaded from `.env` in CWD — run with CWD `server/backend`.

## Tests

```sh
. .venv/bin/activate
pytest -q                  # isolated temp DB via tests/conftest.py
pytest tests/test_recall_capture.py -q
```

Latest reality: ~30 tests pass; 3 xfail on talk-time metrics, authenticated insight privacy, persisted action completion.

## Migrations

Alembic is configured but current dev uses `init_db()` at startup (creates all tables). For schema changes: edit `app/db/models.py`, then generate a migration:
```sh
alembic revision --autogenerate -m "description"
alembic upgrade head
```
(Wire production deployments to `alembic upgrade head`, not `init_db`.)

## Database
- Default `DATABASE_URL=sqlite:///./scribe.db`. Switch to Postgres via URL.
- Per-user ownership: meetings, insights, captures, calendars scoped to `user.id` when auth present; sync resolves to the authenticated user or a demo user (`resolve_request_user`).
- Tokens expire after 30 days (see `get_user_by_token`).

## Background processing
- Recall webhooks enqueue `BackgroundTasks` (broadcast, start transcription, process recall transcript). In production, replace with a durable queue (Celery/Redis) for recovery across restarts.
- Granola sync runs inside the request on `POST /api/integrations/granola/sync` and inside the WebSocket `sync` handler.

## External setup checklist

### Granola
- Set `USE_DEMO_DATA=false` + valid `GRANOLA_API_KEY` with note scopes.
- Either demo mode uses a local fixture meeting.
- Client paces requests to Granola limits; cached sync handles 413 via paginated transcript endpoint.

### Recall
- Keys must be same region as `RECALL_API_BASE_URL`.
- Set `RECALL_WORKSPACE_VERIFICATION_SECRET` (alias `RECALL_WEBHOOK_SECRET`) for webhook signature.
- Configure Recall dashboard webhook → `<PUBLIC_API_BASE_URL>/api/webhooks/recall`, subscribe `bot.status_change`, `recording.done`, `transcript.done`, `transcript.failed`. Update the endpoint whenever ngrok/tunnel URL changes.
- `PUBLIC_API_BASE_URL` must be stable HTTPS (ngrok reserved domain). Never localhost.

### Secrets
- Keep all keys in `server/backend/.env` (git-ignored). Never expose to client.
- `CalendarConnection` stores OAuth client secret in DB as plain text — secure before prod.

## Logging/privacy
- Avoid logging full transcripts; avoid logging credentials. Secret logging review still needed for prod.
- Insights are private-by-intent but not yet owner-scoped on list/get (follow-up).

## Adding a new route
1. Create file in `app/api/routes/`, export `router = APIRouter()`.
2. Include in `app/main.py` (`app.include_router`).
3. Auth via `Depends(get_current_user)` / optional variant; DB via `Depends(get_db)`.
4. Scope queries by `user.id` for safety.
5. Add tests in `tests/`.

## Data flow recap
1. Granola sync → meetings + transcripts (normalized).
2. Capture (manual or calendar) → Recall bot → webhook → recording → transcription → transcript import into `Meeting` (granola_meeting_id `recall:<bot_id>`).
3. `/api/meetings/{id}/analyze` → `BehaviorObservation` rows.
4. `/api/insights/current` → aggregates observations → `WeeklyInsight` + `MicroAction`.

See `app/services/` for the implementation details:
- `granola_client.py`, `granola_sync_service.py`
- `recall_capture_service.py` (Recall client + webhooks + transcript import)
- `analysis_service.py` (behavior labeling)
- `insight_service.py` (weekly insight card generation)
