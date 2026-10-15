# Component contracts: `MeetingTimeline.jsx`

Location: `client/src/components/MeetingTimeline.jsx` (exported as `MeetingTimeline`).

## Props
- `durationSec` — total duration in seconds (overrides video duration when speaker timeline provides a max end). `number | null`
- `markers` — `{ id, track: 'bot'|'events'|'logs', timestamp (sec), endTimestamp (sec?), category, title, description, ... }[]`
- `events` — same shape, alternative data source that the panel aggregates on events/stats
- `isPlaying`, `currentTimeSec`, `onSeek(seconds)` — sync with video player
- `onPlayPause(bool)` — toggle play
- (see source for full prop list — additive_backward_compat is kept)

## Behavior
- Tracks: `TRACK_ORDER = ['bot', 'events', 'logs']` (labelled BOT, EVENTS, LOGS).
- Ruler with ticks (responsive; collapse labels on small screens).
- Markers rendered above tracks; click marker → `onSeek(marker.timestamp)`.
- Keyboard: Space (play/pause), ← / → (seek ±5s), ↑/↓ (previous/next marker). Disabled during text input.
- Responsive states: timeline collapses/stacks below 640px (`styles.css` media queries).
- States: loading (spinner), empty ("No events on timeline"), error (inline).

## Styling hooks (`styles.css`, `.mtl-*`)
- `.mtl` (root), `.mtl__toolbar`, `.mtl__tracks`, `.mtl__track`, `.mtl__track-label`, `.mtl__ruler`, `.mtl__marker`, `.mtl__marker--{category}`, `.mtl__playhead`, `.mtl__states`.

## Verified
- Component renders under video in NoteDetail; visual sanity after dev server refresh. CSS classes are reused throughout for consistency with the rest of the Apple-like Scribe theme.
>