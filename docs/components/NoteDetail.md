# Component contracts: `NoteDetail.jsx`

Location: `client/src/components/NoteDetail.jsx`.

## Inputs
- `noteId` (string), `onBack()`, `onHome()`, `onMeetings()`.

## Responsibilities
- Fetch meeting (`api.note`), transcript (`api.transcript`), video (`api.video`) on mount (Promise.all for note+transcript; video separately).
- Set up data for `MeetingTimeline`: `durationSec`, `currentTimeSec`, `isPlaying`, `markers/events`, `speakerTimeline`.
- Provide `videoRef` and `seekTo(ms)`; wire video `<video>` events (`timeupdate`, `play`, `pause`, `ended`, `loadedmetadata`, `durationchange`) to update timeline state.
- Pull speaker timeline from `speaker_timeline_download_url` returned by `/api/meetings/{id}/video`; map entries into events with `track: 'events'` and timestamps relative (seconds).
- Expose analyze trigger (`/api/meetings/{id}/analyze`) with UI button → displays observations/evidence. (See component.)

## Video surfaced as signed download URL
- `api.video(id)` → `{download_url, expires_at, format, status, speaker_timeline_download_url, recording_id}`.
- If URL missing, `videoStatus='unavailable'`; otherwise 'loading' → 'ready'.
- `videoStatus` drives `MeetingTimeline` empty/error states.

## Note: meeting must be Recall-sourced to have video
Backend returns 404 `Video is not available for this meeting` for Granola-only meetings.
