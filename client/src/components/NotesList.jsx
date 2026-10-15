import { noteTitle, noteOwner, noteDate, summaryPreview, formatDateTime } from '../utils.js';
import { ChevronRight } from './icons.jsx';

function EmptyIllustration() {
  return (
    <svg width="140" height="96" viewBox="0 0 140 96" fill="none" aria-hidden="true">
      <rect x="8" y="14" width="86" height="68" rx="10" fill="var(--purple-soft)" />
      <rect x="20" y="28" width="38" height="7" rx="3.5" fill="var(--purple-line)" />
      <rect x="20" y="41" width="62" height="6" rx="3" fill="var(--purple-line)" />
      <rect x="20" y="53" width="50" height="6" rx="3" fill="var(--purple-line)" />
      <rect x="20" y="65" width="58" height="6" rx="3" fill="var(--purple-line)" />
      <circle cx="112" cy="40" r="16" fill="var(--purple)" />
      <path
        d="M106 40h12M112 34v12"
        stroke="#fff"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
      <rect x="86" y="62" width="46" height="20" rx="10" fill="#fff" stroke="var(--line)" />
      <rect x="94" y="69" width="22" height="6" rx="3" fill="var(--line)" />
      <circle cx="122" cy="72" r="3" fill="var(--purple)" />
    </svg>
  );
}
function initials(name) {
  if (!name) return '';
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

const AVATAR_HUES = [262, 288, 200, 168, 340];

function avatarStyle(note) {
  const text = `${note?.public_id || ''}${note?.title || ''}`;
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) hash = (hash * 31 + text.charCodeAt(i)) % 997;
  const hue = AVATAR_HUES[hash % AVATAR_HUES.length];
  return {
    background: `hsl(${hue} 70% 94%)`,
    color: `hsl(${hue} 55% 38%)`,
  };
}

export function NotesList({ notes, onOpen, onLoadMore, hasMore, loadingMore }) {
  return (
    <div className="meeting-home">
      {notes.length === 0 ? (
        <div className="empty">
          <div className="empty__art">
            <EmptyIllustration />
          </div>
          <h2 className="empty__title">No completed meetings yet</h2>
          <p className="empty__text">
            Schedule a capture above, or sync notes from Granola. The capture bot will appear in the meeting participants.
          </p>
        </div>
      ) : (
        <div className="list">
          {notes.map((note) => {
            const owner = noteOwner(note);
            const title = noteTitle(note);
            const letters = initials(owner) || initials(title) || 'M';
            return (
              <button key={note.id} className="note" onClick={() => onOpen(note.public_id || note.id)}>
                <div className="note__avatar" style={avatarStyle(note)}>
                  {letters}
                </div>
                <div className="note__body">
                  <div className="note__top">
                    <span className="note__title">{title}</span>
                    <span className="note__date">{formatDateTime(noteDate(note))}</span>
                  </div>
                  <div className="note__meta">
                    {owner && <span className="note__owner">{owner}</span>}
                    <span className="note__snippet">{summaryPreview(note)}</span>
                  </div>
                </div>
                <span className="note__chevron">
                  <ChevronRight />
                </span>
              </button>
            );
          })}

          {hasMore && (
            <div className="list__more">
              <button className="btn btn--outline" onClick={onLoadMore} disabled={loadingMore}>
                {loadingMore ? 'Loading…' : 'Load more'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
