import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { SparkleIcon } from './icons.jsx';
import { formatDateTime } from '../utils.js';

export function Insights() {
  const [state, setState] = useState({ loading: true, error: null, insight: null, completing: false });

  const load = async () => {
    setState({ loading: true, error: null, insight: null, completing: false });
    try {
      const insight = await api.getWeekly();
      setState({ loading: false, error: null, insight, completing: false });
    } catch (e) {
      setState({ loading: false, error: e, insight: null, completing: false });
    }
  };

  useEffect(() => {
    load();
  }, []);

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

  return (
    <div className="insights">
      <header className="insights__header">
        <div className="insights__titleGroup">
          <SparkleIcon />
          <h1 className="insights__title">Weekly leadership insights</h1>
        </div>
        {state.insight?.generated_at && (
          <p className="insights__date">Generated {formatDateTime(state.insight.generated_at)}</p>
        )}
      </header>

      {state.loading && <div className="detail__loading">Analyzing your week...</div>}

      {state.error && (
        <div className="empty">
          <h2 className="empty__title">Couldn’t generate insights</h2>
          <p className="empty__text">{state.error.message}</p>
        </div>
      )}

      {state.insight && state.insight.status === 'insufficient_evidence' && (
        <div className="empty">
          <h2 className="empty__title">Not enough evidence yet</h2>
          <p className="empty__text">
            {state.insight.growth_area ||
              'Sync or capture a few more meetings this week and Scribe will generate your first coaching card.'}
          </p>
        </div>
      )}

      {state.insight && state.insight.status !== 'insufficient_evidence' && (
        <div className="insightCards">
          <div className="insightCard insightCard--strength">
            <div className="insightCard__badge">Strength</div>
            <p className="insightCard__text">{state.insight.strength}</p>
          </div>

          <div className="insightCard insightCard--growth">
            <div className="insightCard__badge">Growth area</div>
            <p className="insightCard__text">{state.insight.growth_area}</p>
          </div>

          <div className="insightCard">
            <div className="insightCard__badge">Evidence</div>
            <p className="insightCard__text">{state.insight.evidence_summary}</p>
          </div>

          <div className="insightCard insightCard--action">
            <div className="insightCard__badge">Micro-action</div>
            <p className="insightCard__text">{state.insight.micro_action}</p>
            {state.insight.micro_action_id && (
              <button className="btn btn--outline" onClick={completeAction} disabled={state.completing}>
                {state.completing ? 'Saving…' : 'Mark complete'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}