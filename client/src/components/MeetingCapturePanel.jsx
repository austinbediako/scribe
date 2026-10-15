import { useState } from 'react';
import { api } from '../api.js';

function localDateTimeAfter(minutes) {
  const date = new Date(Date.now() + minutes * 60 * 1000);
  date.setSeconds(0, 0);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60 * 1000).toISOString().slice(0, 16);
}

function statusLabel(status) {
  const labels = {
    scheduling: 'Scheduling',
    scheduled: 'Scheduled',
    joining: 'Joining',
    waiting_room: 'Waiting for host',
    joined: 'Joined',
    recording: 'Capturing',
    recording_denied: 'Recording not allowed',
    processing: 'Processing transcript',
    requesting_transcript: 'Starting transcription',
    transcribing: 'Starting transcription',
    importing_transcript: 'Importing transcript',
    completed: 'Capture complete',
    failed: 'Capture failed',
    cancelled: 'Cancelled',
  };
  return labels[status] || 'Capture status pending';
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
  const [joinAt] = useState(() => localDateTimeAfter(15));
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [busyCaptureId, setBusyCaptureId] = useState(null);
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
    const text = `${capture.title} — ${formatDate(capture.join_at)}\nStatus: ${statusLabel(capture.status)}`;
    try {
      await navigator.clipboard.writeText(text);
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
    <section className="capture" aria-labelledby="capture-title">
      <div className="capture__intro">
        <div>
          <p className="capture__eyebrow">Meeting capture</p>
          <h2 className="capture__title" id="capture-title">Schedule a Scribe capture</h2>
          <p className="capture__description">
            Add a meeting link and start time. Scribe will invite a visible transcription bot;
            the host may need to admit it.
          </p>
        </div>
      </div>

      <form className="capture__form" onSubmit={scheduleCapture}>
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
        <div className="capture__quickLinks">
          <button
            className="btn btn--ghost btn--sm"
            type="button"
            onClick={() => {
              if (meetingUrl.trim()) navigator.clipboard?.writeText(meetingUrl.trim());
            }}
            disabled={!meetingUrl.trim()}
          >
            Copy meeting link
          </button>
          <small>Scribe will schedule the bot automatically and may need host admission.</small>
        </div>
        <label className="capture__consent">
          <input
            type="checkbox"
            checked={consentConfirmed}
            onChange={(event) => setConsentConfirmed(event.target.checked)}
            required
          />
          <span>I have permission to invite the bot and will obtain any participant consent required.</span>
        </label>
        {error && <p className="capture__error" role="alert">{error}</p>}
        <button className="btn btn--primary" type="submit" disabled={submitting || !consentConfirmed}>
          {submitting ? 'Scheduling…' : 'Schedule capture'}
        </button>
      </form>

      {captures.length > 0 && (
        <div className="capture__queue" aria-live="polite">
          <h3>Scheduled and recent captures</h3>
          {captures.map((capture) => (
            <div className="capture__item" key={capture.id}>
              <div className="capture__itemText">
                <strong>{capture.title}</strong>
                <span>{formatDate(capture.join_at)}</span>
                {capture.status_detail && <span className="capture__detail">{capture.status_detail}</span>}
              </div>
              <span className={`capture__status capture__status--${capture.status}`}>
                {statusLabel(capture.status)}
              </span>
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => copyCapture(capture)}
                type="button"
              >
                Copy
              </button>
              {capture.status === 'scheduled' && (
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={() => cancelCapture(capture.id)}
                  disabled={busyCaptureId === capture.id}
                  type="button"
                >
                  {busyCaptureId === capture.id ? 'Cancelling…' : 'Cancel'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
