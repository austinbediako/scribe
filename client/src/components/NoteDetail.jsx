import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { noteTitle, noteOwner, formatDateTime, noteSummary, normalizeTranscript } from '../utils.js';
import { ChevronLeft } from './icons.jsx';
import { MeetingTimeline } from './MeetingTimeline.jsx';

function formatTime(value) {
  if (value === null || value === undefined) return '';
  const seconds = Number(value);
  if (Number.isNaN(seconds)) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

function money(ms) {
  if (!ms) return '0s';
  return `${Math.round(ms / 1000)}s`;
}

export function NoteDetail({ noteId, onBack, onHome, onMeetings }) {
  const [state, setState] = useState({ loading: true, error: null, note: null, transcript: null });
  const [analysis, setAnalysis] = useState({ loading: false, error: null, result: null });
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoStatus, setVideoStatus] = useState('idle');
  const [speakerTimeline, setSpeakerTimeline] = useState([]);
  const [timelineDurationSec, setTimelineDurationSec] = useState(null);
  const [currentTimeSec, setCurrentTimeSec] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState([]);
  const videoRef = useRef(null);

  const seekTo = (ms) => {
    const v = videoRef.current;
    if (!v || !Number.isFinite(ms)) return;
    const sec = Math.max(0, ms / 1000);
    v.currentTime = sec;
    setCurrentTimeSec(sec);
    v.play().catch(() => {});
  };

  const handleTimeUpdate = () => {
    const v = videoRef.current;
    if (v && Number.isFinite(v.currentTime)) {
      setCurrentTimeSec(v.currentTime);
    }
  };

  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);
  const handleEnded = () => setIsPlaying(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || videoStatus !== 'ready') return undefined;
    const updateDuration = () => {
      if (Number.isFinite(video.duration) && video.duration > 0) {
        setTimelineDurationSec(video.duration);
      }
    };
    updateDuration();
    video.addEventListener('loadedmetadata', updateDuration);
    video.addEventListener('durationchange', updateDuration);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('ended', handleEnded);
    return () => {
      video.removeEventListener('loadedmetadata', updateDuration);
      video.removeEventListener('durationchange', updateDuration);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('ended', handleEnded);
    };
  }, [videoStatus, videoUrl]);

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, note: null, transcript: null });
    setAnalysis({ loading: false, error: null, result: null });
    setVideoUrl(null);
    setVideoStatus('loading');
    setSpeakerTimeline([]);
    setTimelineDurationSec(null);
    setCurrentTimeSec(0);
    setIsPlaying(false);
    setTimelineEvents([]);

    Promise.all([api.note(noteId), api.transcript(noteId)])
      .then(([note, transcript]) => {
        if (!cancelled) setState({ loading: false, error: null, note, transcript });
      })
      .catch((error) => {
        if (!cancelled) setState({ loading: false, error, note: null, transcript: null });
      });

    api.video(noteId)
      .then(async (video) => {
        if (cancelled) return;
        if (video?.download_url) {
          setVideoUrl(video.download_url);
          setVideoStatus('ready');
          if (video?.speaker_timeline_download_url) {
            try {
              const response = await fetch(video.speaker_timeline_download_url);
              const data = await response.json();
              if (!cancelled && Array.isArray(data)) {
                setSpeakerTimeline(data);
                const maxEnd = data.reduce(
                  (max, item) =>
                    Math.max(max, (Number(item?.end_timestamp?.relative) || Number(item?.start_timestamp?.relative) || 0) * 1000),
                  0
                );
                if (maxEnd > 0) setTimelineDurationSec(maxEnd / 1000);

                const events = data.map((entry, idx) => ({
                  id: `speaker-${entry?.participant?.id || idx}-${entry?.start_timestamp?.relative || 0}`,
                  track: 'events',
                  category: 'system',
                  timestamp: Number(entry?.start_timestamp?.relative) || 0,
                  endTimestamp: Number(entry?.end_timestamp?.relative) || undefined,
                  title: entry?.participant?.name || 'Speaker',
                  description: `${entry?.participant?.name || 'Unknown'} spoke`,
                }));
                setTimelineEvents(events);
              }
            } catch {
              if (!cancelled) setSpeakerTimeline([]);
            }
          }
        } else {
          setVideoUrl(null);
          setVideoStatus('unavailable');
        }
      })
      .catch(() => {
        if (cancelled) return;
        setVideoUrl(null);
        setVideoStatus('unavailable');
      });

    api.note(noteId)
      .then((noteData) => {
        if (cancelled) return;
        if (noteData && noteData.started_at) {
          const startTime = new Date(noteData.started_at).getTime() / 1000;
          const botEvents = [
            {
              id: 'bot-scheduled',
              track: 'bot',
              category: 'system',
              timestamp: 0,
              title: 'Bot scheduled',
              description: 'Meeting capture was scheduled',
            },
            {
              id: 'bot-joined',
              track: 'bot',
              category: 'success',
              timestamp: Math.max(5, startTime),
              title: 'Bot joined meeting',
              description: 'Scribe Meeting Coach joined the call',
            },
            {
              id: 'bot-recording',
              track: 'bot',
              category: 'success',
              timestamp: Math.max(8, startTime + 2),
              title: 'Recording started',
              description: 'Bot began capturing audio/video',
            },
          ];
          setTimelineEvents((prev) => [...prev, ...botEvents]);
        }
      })
      .catch(() => {
        // Ignore errors for bot events
      });

    return () => {
      cancelled = true;
    };
  }, [noteId]);

  const analyze = async () => {
    setAnalysis({ loading: true, error: null, result: null });
    try {
      const result = await api.analyze(noteId);
      setAnalysis({ loading: false, error: null, result });
    } catch (error) {
      setAnalysis({ loading: false, error, result: null });
    }
  };

  const note = state.note;
  const meetingTimestamp = note?.started_at || note?.created_at;
  const durationSec = timelineDurationSec || (note?.ended_at && note?.started_at
    ? (new Date(note.ended_at).getTime() - new Date(note.started_at).getTime()) / 1000
    : 120);

  return (
    <div className="detail">
      <div className="detail__bar detail__bar--rich">
        <nav className="breadcrumb" aria-label="Breadcrumb">
          <button type="button" className="breadcrumb__link" onClick={onHome || (() => {})}>Home</button>
          <span className="breadcrumb__sep">/</span>
          <button type="button" className="breadcrumb__link" onClick={onMeetings || onBack}>Meetings</button>
          <span className="breadcrumb__sep">/</span>
          <span className="breadcrumb__current">{noteTitle(state.note || { title: noteId })}</span>
        </nav>
        <button className="btn btn--ghost detail__back" onClick={onBack}>
          <ChevronLeft />
          Back
        </button>
      </div>

      {state.loading && <div className="detail__loading">Loading meeting…</div>}

      {state.error && (
        <div className="empty">
          <h2 className="empty__title">Couldn't load this meeting</h2>
          <p className="empty__text">{state.error.message}</p>
        </div>
      )}

      {note && (
        <article className="detail__content">
          <header className="detail__hero">
            <div className="detail__kicker">Meeting details</div>
            <h1 className="detail__title">{noteTitle(note)}</h1>
            <div className="detail__meta">
              {noteOwner(note) && <span className="metaPill">{noteOwner(note)}</span>}
              {formatDateTime(note.started_at || note.created_at) && (
                <span className="metaPill">{formatDateTime(note.started_at || note.created_at)}</span>
              )}
              {note?.source && <span className="metaPill">{note.source === 'recall' ? 'Recall capture' : 'Granola'}</span>}
            </div>
          </header>

          {(videoStatus === 'loading' || videoStatus === 'ready') && (
            <section className="section">
              <h2 className="section__title">Meeting recording</h2>
              {videoStatus === 'loading' ? (
                <div
                  className="empty__text"
                  style={{
                    width: '100%',
                    maxWidth: '760px',
                    minHeight: '180px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '12px',
                    border: '1px dashed var(--border, #d1d5db)',
                    background: 'var(--surface-2, #f4f4f5)',
                  }}
                >
                  Loading meeting recording…
                </div>
              ) : (
                <video
                  ref={videoRef}
                  src={videoUrl}
                  controls
                  preload="none"
                  playsInline
                  style={{ width: '100%', maxWidth: '760px', borderRadius: '12px' }}
                />
              )}
              <a className="recordingAction" href={videoUrl} target="_blank" rel="noreferrer" aria-label="Open or download recording">
                <svg className="recordingAction__art" viewBox="0 0 64 64" fill="none" aria-hidden="true">
                  <rect x="6" y="10" width="52" height="44" rx="11" fill="url(#recordingGradient)" />
                  <path d="M26 24.5v15l14-7.5-14-7.5Z" fill="white" />
                  <path d="M49 41l6 6-6 6" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="17" cy="17" r="3.5" fill="white" fillOpacity="0.75" />
                </svg>
                <span className="recordingAction__text">
                  <strong>Open or download recording</strong>
                  <small>Opens the secure Recall-hosted video in a new tab.</small>
                </span>
                <ChevronLeft className="recordingAction__chevron" />
              </a>
              <defs>
                <linearGradient id="recordingGradient" x1="6" y1="10" x2="58" y2="54" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#60a5fa" />
                  <stop offset="0.55" stopColor="#2563eb" />
                  <stop offset="1" stopColor="#1e1b4b" />
                </linearGradient>
              </defs>
            </section>
          )}

          <MeetingTimeline
            durationSeconds={durationSec}
            currentTime={currentTimeSec}
            isPlaying={isPlaying}
            events={timelineEvents}
            meetingTimestamp={meetingTimestamp}
            isLoading={state.loading || videoStatus === 'loading'}
            error={state.error?.message || null}
            onPlay={handlePlay}
            onPause={handlePause}
            onSeek={(sec) => seekTo(sec * 1000)}
            onEventSelect={(event) => console.log('Event selected:', event)}
          />

          <section className="section">
            <h2 className="section__title">Transcript</h2>
            <TranscriptBlock transcript={state.transcript} onSeek={seekTo} />
          </section>

          <section className="section section--analyze">
            <button className="btn btn--primary analyzeDock__button" onClick={analyze} disabled={analysis.loading}>
              {analysis.loading ? 'Analyzing…' : 'Analyze meeting'}
            </button>
            {analysis.error && <p className="authError">{analysis.error.message}</p>}
            {analysis.result && (
              <div className="analysisResult">
                <p className="analysisCount">{analysis.result.observation_count} observations</p>
                <div className="talkTime">
                  <span className="talkTime__label">Talk time</span>
                  {Object.entries(analysis.result.metrics?.talk_time_ms_by_speaker || {}).map(([speaker, ms]) => (
                    <span className="talkTime__item" key={speaker}>
                      {speaker}: {money(ms)}
                    </span>
                  ))}
                </div>
                <ul className="observationList">
                  {analysis.result.observations.map((observation) => (
                    <li key={observation.id} className="observation">
                      <strong>{observation.behavior_label}</strong> ({observation.confidence})
                      <p>{observation.evidence_text}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </article>
      )}
    </div>
  );
}

function formatMilliseconds(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '';
  const seconds = n > 1000 ? Math.round(n / 1000) : Math.round(n);
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function TranscriptBlock({ transcript, onSeek }) {
  const segments = normalizeTranscript(transcript?.segments || transcript);

  if (!transcript || !segments.length) {
    const text = typeof transcript?.transcript === 'string' ? transcript.transcript : '';
    if (!text) return <p className="section__muted">No transcript available for this meeting.</p>;
    return <div className="section__prose">{text}</div>;
  }

  return (
    <div className="transcript">
      {segments.map((segment, index) => {
        const timeLabel = formatMilliseconds(segment.timestampMs ?? segment.timestamp);
        return (
        <div className="turn" key={index}>
          <div className="turn__side">
            <span className="turn__speaker">{segment.speaker}</span>
            {(segment.timestampMs || segment.timestamp) !== null && (
              <button
                type="button"
                className="turn__time turn__time--link"
                onClick={() => onSeek?.(segment.timestampMs ?? segment.timestamp)}
              >
                {timeLabel}
              </button>
            )}
          </div>
          <div className="turn__text">{segment.text}</div>
        </div>
        );
      })}
    </div>
  );
}