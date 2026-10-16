# Component contracts: `MeetingTimeline.jsx`

Location: `client/src/components/MeetingTimeline.jsx` (exported as `MeetingTimeline`).

## Props
- `durationSeconds` — total duration in seconds (overridden by max speaker-timeline end when available).
- `currentTime`, `isPlaying`, `onPlay`, `onPause`, `onSeek(seconds)` — sync with the video player.
- `events` — `{ id, lane (speaker name), timestamp (sec), endTimestamp (sec?), category, color, title, description }[]`
- `meetingTimestamp`, `isLoading`, `error`, `onEventSelect`, `onToggleVisibility`, `initialVisible`

## Behavior
- **Single fixed-height track** (72px) labelled SPEAKERS. Each unique `lane` (speaker) occupies an invisible horizontal band; markers stagger vertically within the strip so lane count never affects height.
- Each event may carry `color` (per-speaker, assigned in `NoteDetail.jsx` via `speakerColor()`); falls back to `CATEGORY_COLOR[category]`.
- Ruler ticks get a colored dash (`tickColor`) reflecting the speaker active at — or most recent before — that tick.
- Marker click → select + `onSeek(event.timestamp)`. Hover shows `Name — time — description` tooltip; selection shows a details strip.
- Duration bars render under markers when `endTimestamp` is present.
- Keyboard: `Space` play/pause, `J`/`K` seek ∓10s. Disabled while typing.
- Seek-by-click on the ruler/track area; playhead line; Hide/Show timeline toggle.

## Styling hooks (`styles.css`, `.meetingTimeline__*`)
- `.meetingTimeline` (root, light theme via `--tl-*` tokens), `__toolbar`, `__ruler`, `__tick`, `__tickMark`, `__trackRow`, `__trackLabel`, `__trackArea`, `__marker` (+ `.is-selected`), `__durationBar`, `__playheadLine`, `__details`.

## Verified
- Renders under the video in NoteDetail; events come from Recall `speaker_timeline_download_url` fetched client-side. No fabricated events (bot-schedule markers were removed).
