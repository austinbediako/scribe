import { useState } from 'react';
import { api } from '../api.js';
import { CalendarIcon, CheckIcon, MicIcon } from './icons.jsx';

const STATUS_META = {
  scheduling: { label: 'Scheduling', tone: 'pending' },
  scheduled: { label: 'Scheduled', tone: 'pending' },
  joining: { label: 'Joining', tone: 'active' },
  waiting_room: { label: 'Waiting for host', tone: 'attention' },
  joined: { label: 'Joined', tone: 'active' },
  recording: { label: 'Capturing', tone: 'active' },
  recording_denied: { label: 'Recording denied', tone: 'error' },
  processing: { label: 'Processing', tone: 'active' },
  requesting_transcript: { label: 'Transcribing', tone: 'active' },
  transcribing: { label: 'Transcribing', tone: 'active' },
  importing_transcript: { label: 'Importing', tone: 'active' },
  completed: { label: 'Complete', tone: 'done' },
  failed: { label: 'Failed', tone: 'error' },
  cancelled: { label: 'Cancelled', tone: 'muted' },
};

function statusMeta(status) {
  return STATUS_META[status] || { label: 'Pending', tone: 'muted' };
}

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Meeting time unavailable'
    : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

export function MeetingCapturePanel({ captures, onChanged }) {
  const [title, setTitle] = useState('');
  const [meetingUrl, setMeetingUrl] = useState('');
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [busyCaptureId, setBusyCaptureId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [error, setError] = useState('');

  const scheduleCapture = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await api.createCapture({
        title: title.trim(),
        meeting_url: meetingUrl.trim(),
        consent_confirmed: consentConfirmed,
      });
      setTitle('');
      setMeetingUrl('');
      setConsentConfirmed(false);
      await onChanged();
    } catch (requestError) {
      setError(requestError.message || 'Could not schedule meeting capture.');
    } finally {
      setSubmitting(false);
    }
  };

  const copyCapture = async (capture) => {
    const text = `${capture.title} — ${formatDate(capture.join_at)}\nStatus: ${statusMeta(capture.status).label}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(capture.id);
      window.setTimeout(() => setCopiedId((current) => (current === capture.id ? null : current)), 1600);
    } catch {
      setError('Could not copy capture details.');
    }
  };

  const cancelCapture = async (captureId) => {
    setBusyCaptureId(captureId);
    setError('');
    try {
      await api.cancelCapture(captureId);
      await onChanged();
    } catch (requestError) {
      setError(requestError.message || 'Could not cancel this capture.');
    } finally {
      setBusyCaptureId(null);
    }
  };

  return (
    <div className="captures">
      <header className="captures__header">
        <div className="insights__titleGroup">
          <CalendarIcon />
          <h1 className="insights__title">Meeting captures</h1>
        </div>
        <p className="insights__subtitle">
          Scribe sends a visible transcription bot to the meetings you schedule here.
        </p>
      </header>

      <section className="captureCard" aria-labelledby="capture-title">
        <div className="captureCard__head">
          <div className="captureCard__icon" aria-hidden="true">
            <MicIcon />
          </div>
          <div>
            <h2 className="captureCard__title" id="capture-title">Schedule a capture</h2>
            <p className="captureCard__description">
              Paste a meeting link. The bot joins visibly as “Scribe Meeting Coach” — the host may need to admit it.
            </p>
          </div>
        </div>

        <form className="captureForm" onSubmit={scheduleCapture}>
          <label className="capture__field">
            <span>Meeting title</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Weekly planning"
              maxLength={500}
              required
            />
          </label>
          <label className="capture__field">
            <span>Meeting link</span>
            <input
              type="url"
              value={meetingUrl}
              onChange={(event) => setMeetingUrl(event.target.value)}
              placeholder="https://meet.google.com/..."
              required
            />
            <small>Google Meet, Zoom, Microsoft Teams, or Webex</small>
          </label>

          <label className="captureForm__consent">
            <input
              type="checkbox"
              checked={consentConfirmed}
              onChange={(event) => setConsentConfirmed(event.target.checked)}
              required
            />
            <span>
              I have permission to record this meeting and will get consent from
              participants where required.
            </span>
          </label>

          {error && <p className="auth__error" role="alert">{error}</p>}

          <div className="captureForm__actions">
            <button className="btn btn--primary" type="submit" disabled={submitting || !consentConfirmed}>
              {submitting ? 'Scheduling…' : 'Schedule capture'}
            </button>
          </div>
        </form>
      </section>

      <section className="captureQueue" aria-live="polite" aria-label="Capture queue">
        <h2 className="section__title">Scheduled and recent captures</h2>
        {captures.length === 0 ? (
          <p className="captureQueue__empty">Nothing scheduled yet. Your captures will appear here once you schedule one.</p>
        ) : (
          <ul className="captureQueue__list">
            {captures.map((capture) => {
              const meta = statusMeta(capture.status);
              return (
                <li className="captureItem" key={capture.id}>
                  <span className={`captureItem__dot captureItem__dot--${meta.tone}`} aria-hidden="true" />
                  <div className="captureItem__text">
                    <strong>{capture.title || 'Untitled capture'}</strong>
                    <span className="captureItem__meta">
                      {formatDate(capture.join_at)}
                      {capture.status_detail ? ` · ${capture.status_detail}` : ''}
                    </span>
                  </div>
                  <span className={`captureItem__status captureItem__status--${meta.tone}`}>
                    {meta.label}
                  </span>
                  <div className="captureItem__actions">
                    <button
                      className="btn btn--ghost btn--sm"
                      onClick={() => copyCapture(capture)}
                      type="button"
                    >
                      {copiedId === capture.id ? 'Copied' : 'Copy'}
                    </button>
                    {capture.status === 'scheduled' && (
                      <button
                        className="btn btn--ghost btn--sm captureItem__cancel"
                        onClick={() => cancelCapture(capture.id)}
                        disabled={busyCaptureId === capture.id}
                        type="button"
                      >
                        {busyCaptureId === capture.id ? 'Cancelling…' : 'Cancel'}
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
