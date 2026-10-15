import { useEffect, useMemo, useState } from 'react';
import { api } from '../api.js';
import { SparkleIcon, SearchIcon, NoteIcon } from './icons.jsx';
import { formatDateTime, noteTitle, noteDate } from '../utils.js';

function InsightCards({ insight, completing, onComplete }) {
  if (!insight) return null;
  if (insight.status === 'insufficient_evidence') {
    return (
      <div className="empty">
        <h2 className="empty__title">Not enough evidence yet</h2>
        <p className="empty__text">
          {insight.growth_area ||
            'Sync or analyze a few more meetings and Scribe will generate a coaching card.'}
        </p>
      </div>
    );
  }
  return (
    <div className="insightCards">
      <div className="insightCard insightCard--strength">
        <div className="insightCard__badge">Strength</div>
        <p className="insightCard__text">{insight.strength}</p>
      </div>

      <div className="insightCard insightCard--growth">
        <div className="insightCard__badge">Growth area</div>
        <p className="insightCard__text">{insight.growth_area}</p>
      </div>

      <div className="insightCard">
        <div className="insightCard__badge">Evidence</div>
        <p className="insightCard__text">{insight.evidence_summary}</p>
      </div>

      <div className="insightCard insightCard--action">
        <div className="insightCard__badge">Micro-action</div>
        <p className="insightCard__text">{insight.micro_action}</p>
        {insight.micro_action_id && (
          <button className="btn btn--outline" onClick={onComplete} disabled={completing}>
            {completing ? 'Saving…' : 'Mark complete'}
          </button>
        )}
      </div>
    </div>
  );
}

export function Insights() {
  const [mode, setMode] = useState('week');
  const [state, setState] = useState({ loading: true, error: null, insight: null, completing: false });
  const [meetings, setMeetings] = useState([]);
  const [meetingQuery, setMeetingQuery] = useState('');
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [meetingInsight, setMeetingInsight] = useState({ loading: false, error: null, insight: null });

  const loadWeekly = async () => {
    setState({ loading: true, error: null, insight: null, completing: false });
    try {
      const insight = await api.getWeekly();
      setState({ loading: false, error: null, insight, completing: false });
    } catch (e) {
      setState({ loading: false, error: e, insight: null, completing: false });
    }
  };

  useEffect(() => {
    loadWeekly();
    api.notes().then((data) => setMeetings(Array.isArray(data) ? data : [])).catch(() => {});
  }, []);

  const filteredMeetings = useMemo(() => {
    const q = meetingQuery.trim().toLowerCase();
    if (!q) return meetings;
    return meetings.filter((m) => (m.title || '').toLowerCase().includes(q));
  }, [meetings, meetingQuery]);

  const selectMeeting = async (meeting) => {
    const key = meeting.public_id || meeting.id;
    setSelectedMeeting(meeting);
    setMeetingInsight({ loading: true, error: null, insight: null });
    try {
      const insight = await api.meetingInsight(key);
      setMeetingInsight({ loading: false, error: null, insight });
    } catch (e) {
      setMeetingInsight({ loading: false, error: e, insight: null });
    }
  };

  const completeAction = async () => {
    if (!state.insight?.micro_action_id) return;
    setState((prev) => ({ ...prev, completing: true }));
    try {
      await api.completeAction(state.insight.micro_action_id, 'completed');
      setState((prev) => ({ ...prev, completing: false }));
    } catch (e) {
      setState((prev) => ({ ...prev, completing: false, error: e }));
    }
  };

  const activeInsight = mode === 'week' ? state.insight : meetingInsight.insight;
  const activeLoading = mode === 'week' ? state.loading : meetingInsight.loading;
  const activeError = mode === 'week' ? state.error : meetingInsight.error;

  return (
    <div className="insights">
      <header className="insights__header">
        <div className="insights__titleGroup">
          <SparkleIcon />
          <h1 className="insights__title">Leadership insights</h1>
        </div>
        <div className="insights__toggle" role="tablist" aria-label="Insight scope">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'week'}
            className={`insights__tab ${mode === 'week' ? 'insights__tab--active' : ''}`}
            onClick={() => setMode('week')}
          >
            This week
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'meeting'}
            className={`insights__tab ${mode === 'meeting' ? 'insights__tab--active' : ''}`}
            onClick={() => setMode('meeting')}
          >
            By meeting
          </button>
        </div>
        {mode === 'week' && state.insight?.generated_at && (
          <p className="insights__date">Generated {formatDateTime(state.insight.generated_at)}</p>
        )}
      </header>

      {mode === 'meeting' && (
        <div className="meetingPicker">
          <div className="meetingPicker__search">
            <SearchIcon />
            <input
              type="search"
              value={meetingQuery}
              onChange={(e) => setMeetingQuery(e.target.value)}
              placeholder="Search your meetings…"
              aria-label="Search meetings"
            />
          </div>
          <div className="meetingPicker__list" role="listbox" aria-label="Meetings">
            {filteredMeetings.length === 0 && (
              <p className="meetingPicker__empty">
                {meetingQuery ? 'No meetings match that search.' : 'No meetings synced yet.'}
              </p>
            )}
            {filteredMeetings.map((meeting) => {
              const key = meeting.public_id || meeting.id;
              const selected = selectedMeeting && (selectedMeeting.public_id || selectedMeeting.id) === key;
              return (
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  key={key}
                  className={`meetingPicker__item ${selected ? 'meetingPicker__item--active' : ''}`}
                  onClick={() => selectMeeting(meeting)}
                >
                  <span className="meetingPicker__icon">
                    <NoteIcon />
                  </span>
                  <span className="meetingPicker__body">
                    <strong>{noteTitle(meeting)}</strong>
                    <small>{formatDateTime(noteDate(meeting))}</small>
                  </span>
                  <code className="meetingPicker__id">{meeting.public_id || meeting.id}</code>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {mode === 'meeting' && !selectedMeeting && !activeLoading && (
        <div className="empty">
          <h2 className="empty__title">Pick a meeting</h2>
          <p className="empty__text">
            Choose a meeting above and Scribe will build a coaching card from its observations.
          </p>
        </div>
      )}

      {activeLoading && <div className="detail__loading">Generating insight…</div>}

      {!activeLoading && activeError && (
        <div className="empty">
          <h2 className="empty__title">Couldn’t generate insights</h2>
          <p className="empty__text">{activeError.message}</p>
        </div>
      )}

      {!activeLoading && !activeError && activeInsight && (
        <InsightCards insight={activeInsight} completing={state.completing} onComplete={completeAction} />
      )}
    </div>
  );
}
