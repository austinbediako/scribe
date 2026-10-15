# Component contracts: `MeetingCapturePanel.jsx`

Location: `client/src/components/MeetingCapturePanel.jsx`.

## Props
- `captures` — array from `/api/integrations/recall/captures` (sorted by join_at asc)
- `onChanged` — re-fetch captures (App's loadNotes)

## Create capture flow
Form fields:
- `title` (required)
- `meeting_url` (required; https Google Meet/Zoom/Teams/Webex)
- `join_at` (optional; defaults to now+15min via localDateTimeAfter(15), tz-aware, future time)
- `consent_confirmed` (must be true to enable submit) — mandatory per spec, no capture without consent
Submits via `api.createCapture`. On failure shows error. Form resets on success.

## List / cancel
- Each capture shows `statusLabel`, title, formatted date, and cancel button for `status === 'scheduled'`.
- Cancel: `api.cancelCapture(id)`, then `onChanged()`.

## Calendar integration
- Connect Google/Outlook via `api.createCalendar` (requires OAuth refresh token — typically done server-side in prod, but exposed).
- List calendars `api.calendars`.
- List events `api.calendarEvents(connectionId, updatedSince)`.
- Schedule an event with consent `api.scheduleCalendarEvent(connectionId, eventId, {consent_confirmed})`.
- Delete connection `api.deleteCalendar`.

## Important UI specs
- Recent/scheduled captures are placed here (dedicated Captures page, NOT inline on NotesDetail/Home).
- Consent must be confirmed per capture.
- Supported platforms only: Google Meet / Zoom / Microsoft Teams / Webex.
- Calendar capture flow requires explicit per-event consent.

## Status mapping
See `statusLabel` map in source for all 14 states: `scheduling, scheduled, joining, waiting_room, joined, recording, recording_denied, processing, requesting_transcript, transcribing, importing_transcript, completed, failed, cancelled`.
