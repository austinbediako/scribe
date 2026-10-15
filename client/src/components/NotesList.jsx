import { noteTitle, noteOwner, noteDate, summaryPreview } from '../utils.js';
import { ChevronLeft } from './icons.jsx';
function initials(name) {
  if (!name) return '?';
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

export function NotesList({ notes, onOpen, onLoadMore, hasMore, loadingMore }) {
  return (
    <div className="meeting-home">
      {notes.length === 0 ? (
        <div className="empty">
          <h2 className="empty__title">No completed meetings yet</h2>
          <p className="empty__text">
            Schedule a capture above, or sync notes from Granola. The capture bot will appear in the meeting participants.
          </p>
        </div>
      ) : (
        <div className="list">
          {notes.map((note) => {
            const owner = noteOwner(note);
            return (
              <button key={note.id} className="note" onClick={() => onOpen(note.id)}>
                <div className="note__avatar">{initials(owner)}</div>
                <div className="note__body">
                  <div className="note__top">
                    <span className="note__title">{noteTitle(note)}</span>
                    <span className="note__date">{noteDate(note)}</span>
                  </div>
                  <div className="note__meta">
                    {owner && <span className="note__owner">{owner}</span>}
                    <span className="note__snippet">{summaryPreview(note)}</span>
                  </div>
                </div>
                <span className="note__chevron">
                  <ChevronLeft />
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
