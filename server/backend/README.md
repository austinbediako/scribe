# Scribe Backend

Scribe backend service for Granola-driven leadership insight generation.

## Granola configuration

Local development defaults to demo data. To enable live sync, set `USE_DEMO_DATA=false` and provide a Granola API key with access to the notes you want Scribe to read. The documented API base URL is `https://public-api.granola.ai/v1`; the example placeholder credential is rejected when demo mode is disabled.

The client uses `Authorization: Bearer <key>` and `GET /notes` cursor pagination (`notes`, `hasMore`, `cursor`; page size capped at 30). It fetches each note with `include=transcript`; if Granola returns `413 TRANSCRIPT_TOO_LARGE`, it retrieves the transcript through cursor-paginated `GET /notes/{note_id}/transcript` (page size capped at 100). Requests are paced to Granola's documented sustained rate of 5 requests per second. API access depends on the key's configured scopes; the documented burst capacity is 25 requests per 5 seconds.

## Recall meeting capture

Set `RECALL_API_KEY` and `RECALL_WEBHOOK_SECRET` in the backend environment. `RECALL_API_BASE_URL` must use the same Recall region as the API key. Capture is opt-in: users submit a meeting link, start time, and an explicit consent confirmation.

Recall must be able to reach the backend at a stable public HTTPS URL. Configure a Recall webhook endpoint at `<public-backend-url>/api/webhooks/recall`, use the workspace verification secret as `RECALL_WEBHOOK_SECRET`, and subscribe it to `bot.status_change`, `recording.done`, `transcript.done`, and `transcript.failed`. For local development, use a stable tunnel URL and update the Recall dashboard endpoint when it changes.

After a meeting, Scribe requests Recall async transcription on `recording.done`, then imports and analyzes the transcript on `transcript.done`. Transcription and diarization may incur Recall usage charges. Webhook jobs currently run as FastAPI background tasks; production deployments should use a durable task queue if they need recovery across process restarts.
