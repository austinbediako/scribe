# Backend service: `recall_capture_service.py`

Location: `server/backend/app/services/recall_capture_service.py`.

## Purpose
Manages the entire bot-capture pipeline:
1. Schedule a Recall bot given a `MeetingCapture`.
2. Verify webhook signatures (Svix).
3. Translate Recall webhook events into DB capture status transitions and broadcast over WebSocket (`broadcast_capture_status`).
4. On `recording.done`: `accept_recording_event` saves recording id, then `start_recall_transcription` requests async transcription+dialiarization.
5. On `transcript.done`: `accept_transcript_event` → `process_recall_transcript` downloads transcript + creates a `Meeting` (granola_meeting_id `recall:<bot_id>`) + `TranscriptSegment`s → triggers analysis availability.
6. Calendar OAuth + event listing/scheduling/canceling helpers.

## Key classes/functions
- `RecallClient` — HTTP wrapper (`schedule_capture`, `cancel_scheduled_capture`, `retrieve_bot`, `retrieve_calendar`, etc.)
- `RecallNotConfiguredError` — raised when `recall_api_key` missing
- `verify_recall_signature(secret, webhook_id, webhook_timestamp, webhook_signature, raw_body)` — Svix signature check
- `apply_recall_status_event(db, event_id, event_type, payload)` — updates capture status for generic `bot.status_change`
- `accept_recording_event`, `accept_transcript_event` — idempotent webhook acceptance using `RecallWebhookEvent` dedupe
- `start_recall_transcription(capture_id, recording_id)` — background task
- `process_recall_transcript(capture_id, transcript_id)` — background task that finalizes Meeting + TranscriptSegment
- `broadcast_capture_status(capture_id)` — WebSocket push

## Webhook event types handled (in `captures.py`)
- `recording.done`
- `transcript.done` / `transcript.failed`
- else → `apply_recall_status_event` (for `bot.status_change`, etc.)
- `calendar.update` / `calendar.sync_events` handled early for calendar connection status.

## Notes
- Background jobs run as FastAPI BackgroundTasks (not durable; replace with queue in prod).
- Cost: transcription + diarization incur Recall usage charges.
- See operations.md for env setup + dashboard webhook wiring.

## Cost/safety
- Consent gating is enforced in routes; service assumes consent recorded on `MeetingCapture.consent_confirmed`.
- No capture without consent achievable (route 400s if false).
