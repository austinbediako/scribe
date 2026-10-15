import { useEffect, useMemo, useRef, useState } from 'react';

function formatPlaybackTime(value) {
  const totalSeconds = Math.max(0, Number(value) || 0);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function formatMeetingTimestamp(value) {
  if (!value) return 'Meeting timeline';
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toUTCString().replace(' GMT', ' UTC');
  } catch {
    return String(value);
  }
}

const CATEGORY_COLOR = {
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',
  system: '#8B5CF6',
  neutral: '#6B7280',
};

const TRACK_ORDER = ['bot', 'events', 'logs'];

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function calculatePosition(timestampSeconds, durationSeconds) {
  if (!Number.isFinite(timestampSeconds) || !Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    return 0;
  }
  return clamp((timestampSeconds / durationSeconds) * 100, 0, 100);
}

function normalizeEvent(event, durationSeconds) {
  if (!event || typeof event !== 'object') return null;
  const rawTimestamp = Number(event.timestamp);
  if (!Number.isFinite(rawTimestamp) || rawTimestamp < 0) return null;
  const safeDuration = Math.max(1, Number(durationSeconds) || 1);
  const category = typeof event.category === 'string' && CATEGORY_COLOR[event.category] ? event.category : 'neutral';
  const track = typeof event.track === 'string' ? event.track : 'events';
  if (!TRACK_ORDER.includes(track)) return null;
  const timestamp = clamp(rawTimestamp, 0, safeDuration);
  const endTimestamp = Number.isFinite(Number(event.endTimestamp))
    ? clamp(Number(event.endTimestamp), timestamp, safeDuration)
    : undefined;
  return {
    id: String(event.id || `${track}-${timestamp}-${event.title || 'event'}`),
    track,
    category,
    title: typeof event.title === 'string' && event.title.trim() ? event.title.trim() : 'Untitled event',
    description: typeof event.description === 'string' ? event.description : '',
    metadata: event.metadata && typeof event.metadata === 'object' ? event.metadata : {},
    severity: typeof event.severity === 'string' ? event.severity : '',
    timestamp,
    endTimestamp,
  };
}

function generateTicks(durationSeconds, containerWidth) {
  const safeDuration = Math.max(1, Number(durationSeconds) || 1);
  const safeWidth = Math.max(240, Number(containerWidth) || 720);
  let interval = 5;
  if (safeDuration <= 60) interval = 5;
  else if (safeDuration <= 180) interval = 15;
  else if (safeDuration <= 600) interval = 60;
  else if (safeDuration <= 1800) interval = 300;
  else interval = 600;

  const maximumTicks = Math.max(3, Math.floor(safeWidth / 92));
  while (safeDuration / interval > maximumTicks && interval < 86400) {
    interval *= 2;
  }

  const ticks = [];
  for (let time = 0; time <= safeDuration + 0.0001; time += interval) {
    ticks.push(Math.min(time, safeDuration));
  }
  if (ticks.length < 2) ticks.push(safeDuration);
  return [...new Set(ticks.map((value) => Number(value.toFixed(3))))];
}

function PlayIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l11-6.5-11-6.5Z" fill="currentColor" /></svg>;
}

function PauseIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="5" width="3.5" height="14" fill="currentColor" /><rect x="13.5" y="5" width="3.5" height="14" fill="currentColor" /></svg>;
}

export function MeetingTimeline({
  durationSeconds = 121,
  currentTime = 0,
  isPlaying = false,
  events = [],
  meetingTimestamp = null,
  isLoading = false,
  error = null,
  onPlay,
  onPause,
  onSeek,
  onEventSelect,
  onToggleVisibility,
  initialVisible = true,
}) {
  const containerRef = useRef(null);
  const rulerAreaRef = useRef(null);
  const [visible, setVisible] = useState(initialVisible);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [containerWidth, setContainerWidth] = useState(900);

  const normalizedEvents = useMemo(
    () => events.map((event) => normalizeEvent(event, durationSeconds)).filter(Boolean),
    [events, durationSeconds]
  );
  const safeDuration = Math.max(1, Number(durationSeconds) || 1);
  const safeCurrentTime = clamp(Number(currentTime) || 0, 0, safeDuration);
  const ticks = useMemo(() => generateTicks(safeDuration, containerWidth), [safeDuration, containerWidth]);
  const selectedEvent = useMemo(
    () => normalizedEvents.find((event) => event.id === selectedEventId) || null,
    [normalizedEvents, selectedEventId]
  );

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry?.contentRect?.width) setContainerWidth(Math.max(320, Math.floor(entry.contentRect.width)));
    });
    observer.observe(containerRef.current);
    setContainerWidth(Math.max(320, Math.floor(containerRef.current.getBoundingClientRect().width)));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onKeyDown = (nativeEvent) => {
      const activeElement = document.activeElement;
      const isTyping = activeElement && (
        activeElement.tagName === 'INPUT' ||
        activeElement.tagName === 'TEXTAREA' ||
        activeElement.isContentEditable
      );
      if (isTyping) return;
      if (nativeEvent.code === 'Space') {
        nativeEvent.preventDefault();
        if (isPlaying) onPause?.();
        else onPlay?.();
      } else if (nativeEvent.key.toLowerCase() === 'j') {
        nativeEvent.preventDefault();
        onSeek?.(clamp(safeCurrentTime - 10, 0, safeDuration));
      } else if (nativeEvent.key.toLowerCase() === 'k') {
        nativeEvent.preventDefault();
        onSeek?.(clamp(safeCurrentTime + 10, 0, safeDuration));
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isPlaying, onPause, onPlay, onSeek, safeCurrentTime, safeDuration]);

  const handleVisibility = (nextVisible) => {
    setVisible(nextVisible);
    onToggleVisibility?.(nextVisible);
  };

  const handleSeekByClick = (nativeEvent) => {
    const target = nativeEvent.currentTarget;
    const rect = target.getBoundingClientRect();
    const next = clamp((nativeEvent.clientX - rect.left) / rect.width, 0, 1);
    onSeek?.(next * safeDuration);
  };

  const trackEvents = (trackName) => normalizedEvents.filter((event) => event.track === trackName);

  const playheadLeft = `${(safeCurrentTime / safeDuration) * 100}%`;

  if (error) {
    return (
      <section className="meetingTimeline meetingTimeline--error" aria-label="Meeting timeline">
        <div className="meetingTimeline__toolbar">
          <strong>Timeline unavailable</strong>
        </div>
        <p>{error}</p>
      </section>
    );
  }

  return (
    <section className="meetingTimeline" aria-label="Meeting timeline" ref={containerRef}>
      <div className="meetingTimeline__toolbar">
        <div className="meetingTimeline__toolbarLeft">
          <button
            type="button"
            className="meetingTimeline__iconButton"
            aria-label={isPlaying ? 'Pause recording' : 'Play recording'}
            onClick={() => (isPlaying ? onPause?.() : onPlay?.())}
          >
            {isPlaying ? <PauseIcon /> : <PlayIcon />}
          </button>
          <button
            type="button"
            className="meetingTimeline__restart"
            aria-label="Restart recording"
            onClick={() => onSeek?.(0)}
          >
            ⟲
          </button>
          <div className="meetingTimeline__time">
            <strong>{formatPlaybackTime(safeCurrentTime)}</strong>
            <span> / {formatPlaybackTime(safeDuration)}</span>
          </div>
          <span className="meetingTimeline__timestamp">{formatMeetingTimestamp(meetingTimestamp)}</span>
        </div>
        <div className="meetingTimeline__toolbarRight">
          <span className="meetingTimeline__shortcutHint"><kbd>Space</kbd> play</span>
          <span className="meetingTimeline__shortcutHint"><kbd>J/K</kbd> ±10s</span>
          <label className="meetingTimeline__hide">
            <input type="checkbox" checked={visible} onChange={(event) => handleVisibility(event.target.checked)} />
            <span>{visible ? 'Hide Timeline' : 'Show Timeline'}</span>
          </label>
        </div>
      </div>

      {isLoading && <div className="meetingTimeline__loading">Loading timeline…</div>}

      {!isLoading && visible && (
        <>
          <div className="meetingTimeline__body">
            <div className="meetingTimeline__ruler">
              <div className="meetingTimeline__labelColumn" />
              <div className="meetingTimeline__rulerArea" ref={rulerAreaRef} onClick={handleSeekByClick}>
                {ticks.map((tick) => (
                  <div key={tick} className="meetingTimeline__tick" style={{ left: `${(tick / safeDuration) * 100}%` }}>
                    <span>{formatPlaybackTime(tick)}</span>
                  </div>
                ))}
                <div className="meetingTimeline__playheadLine" style={{ left: playheadLeft }} />
              </div>
            </div>

            {TRACK_ORDER.map((trackName) => (
              <div key={trackName} className="meetingTimeline__trackRow">
                <div className="meetingTimeline__trackLabel">{trackName.toUpperCase()}</div>
                <div className="meetingTimeline__trackArea" onClick={handleSeekByClick}>
                  {trackEvents(trackName).map((event) => {
                    const left = `${calculatePosition(event.timestamp, safeDuration)}%`;
                    return (
                      <span key={event.id} style={{ position: 'absolute', left, top: '50%', transform: 'translate(-50%, -50%)' }}>
                        {event.endTimestamp ? (
                          <span
                            className="meetingTimeline__durationBar"
                            style={{
                              left: 0,
                              width: `${calculatePosition(event.endTimestamp, safeDuration) - calculatePosition(event.timestamp, safeDuration)}%`,
                              background: CATEGORY_COLOR[event.category],
                            }}
                            title={`${event.title} ${formatPlaybackTime(event.timestamp)} - ${formatPlaybackTime(event.endTimestamp)}`}
                          />
                        ) : null}
                        <button
                          type="button"
                          className={`meetingTimeline__marker${selectedEventId === event.id ? ' is-selected' : ''}`}
                          style={{ background: CATEGORY_COLOR[event.category] }}
                          aria-label={`${event.title} at ${formatPlaybackTime(event.timestamp)}`}
                          title={`${event.title} - ${formatPlaybackTime(event.timestamp)}${event.description ? ` - ${event.description}` : ''}`}
                          onClick={(nativeEvent) => {
                            nativeEvent.stopPropagation();
                            setSelectedEventId(event.id);
                            onEventSelect?.(event);
                            onSeek?.(event.timestamp);
                          }}
                        />
                      </span>
                    );
                  })}
                  <div className="meetingTimeline__playheadLine" style={{ left: playheadLeft }} />
                </div>
              </div>
            ))}
          </div>

          {selectedEvent && (
            <div className="meetingTimeline__details">
              <strong>{selectedEvent.title}</strong>
              <span>{formatPlaybackTime(selectedEvent.timestamp)}</span>
              {selectedEvent.description ? <p>{selectedEvent.description}</p> : null}
            </div>
          )}
        </>
      )}

      {!isLoading && !visible && normalizedEvents.length > 0 && (
        <p className="meetingTimeline__muted">Timeline hidden. Playback controls remain available.</p>
      )}

      {!isLoading && !normalizedEvents.length && visible && (
        <p className="meetingTimeline__muted">No activity recorded.</p>
      )}
    </section>
  );
}

export const meetingTimelineUtils = {
  formatPlaybackTime,
  calculateTimelinePosition: (timestamp, duration) => calculatePosition(timestamp, duration, 1000),
  generateTimeTicks: generateTicks,
  getEventCategoryColor: (category) => CATEGORY_COLOR[category] || CATEGORY_COLOR.neutral,
  normalizeTimelineEvent: normalizeEvent,
};