# Scribe Frontend (`client/`)

React 18 + Vite dev server. Provides the Scribe UI: landing/auth, meetings list, NoteDetail with video + transcript + MeetingTimeline playback, Insights, and Captures.

## Setup

```sh
cd client
pnpm install
pnpm run dev         # http://localhost:5173
pnpm run build       # production build (must be green before merging)
pnpm run preview
```

Vite proxies `/api` and `/ws` to `http://127.0.0.1:8000` (see `vite.config.js`).

## Routing (custom, no router lib)

Paths handled in `App.jsx` via `window.history.pushState`:
- `/` Landing
- `/signin`, `/signup` Auth
- `/app` (also `/app/meetings`) — meetings list (NoteList); selected meeting via `/app/meetings/{id}` shows NoteDetail
- `/app/insights` — Insights
- `/app/captures` — MeetingCapturePanel
- `/app/meetings/{id}` — NoteDetail full

## Key components

| Component | Purpose |
|---|---|
| App.jsx | route orchestration, global state (notes, captures, token, user), WebSocket sync |
| Auth.jsx | login/signup, returns token to parent |
| TopBar.jsx, Sidebar.jsx | layout, search, navigation (Meetings/Insights/Captures) |
| NotesList.jsx | list of meetings |
| NoteDetail.jsx | video player (top) + transcript + MeetingTimeline (below video); seekTo; fetches /api/meetings/{id}, /transcript, /video |
| MeetingTimeline.jsx | fixed-height speaker-strip timeline (per-speaker colored markers + ruler ticks), playhead, keyboard shortcuts |
| Insights.jsx | weekly insight + By-meeting toggle with searchable meeting picker |
| MeetingCapturePanel.jsx | schedule/list/cancel captures + calendars, consent gating |
| icons.jsx | SVG icon set |

## Integration contract
- See root `AGENTS.md` for deployment topology and invariants; `README.md` for the API catalog.
- API base: `import.meta.env.VITE_API_BASE_URL` (set on Vercel); unset → relative `/api` proxied to `:8000` in dev.
- Auth: token stored in `localStorage` as `scribe_token`; 401s clear the token + dispatch `scribe:unauthorized`, **except** `/auth/login` and `/auth/signup`, which keep the user on the auth page and show the error inline.
- Real-time: WebSocket `/ws?token=...` (URL derived from `VITE_API_BASE_URL`) updates meetings list and broadcasts `capture.updated`; `loadNotes()` runs on every `/app*` route.
- MeetingTimeline seeks video via refs passed down; transcript timestamps click-to-seek uses `seekTo(ms)`.

## Style
- Global tokens in `src/styles.css`. Light Apple-like Scribe: purple/white, rounded corners, soft shadows. MeetingTimeline styles live in the same file (`.meetingTimeline__*` classes).

## Testing/build
- `pnpm run build` (canonical local verification).
- Visual states (MeetingTimeline loading/empty) verified manually with dev server refresh.
