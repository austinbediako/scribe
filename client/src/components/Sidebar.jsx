import { CalendarIcon, FolderIcon, NoteIcon, SparkleIcon } from './icons.jsx';

export function Sidebar({ folders, activeFolder, onSelectFolder, totalCount, activeView, onSelectInsights, onSelectCaptures, onSelectAll, capturesCount }) {
  return (
    <aside className="sidebar">
      <nav className="sidebar__group">
        <button
          className={`navitem ${activeView === 'list' && activeFolder === null ? 'navitem--active' : ''}`}
          onClick={onSelectAll}
        >
          <span className="navitem__icon">
            <NoteIcon />
          </span>
          <span className="navitem__label">All meetings</span>
          {typeof totalCount === 'number' && <span className="navitem__count">{totalCount}</span>}
        </button>

        {folders.length > 0 && <div className="sidebar__heading">Folders</div>}

        {folders.map((folder) => (
          <button
            key={folder.id}
            className={`navitem ${activeFolder === folder.id ? 'navitem--active' : ''}`}
            onClick={() => onSelectFolder(folder.id)}
          >
            <span className="navitem__icon">
              <FolderIcon />
            </span>
            <span className="navitem__label">{folder.title}</span>
          </button>
        ))}
        <button
          className={`navitem ${activeView === 'captures' ? 'navitem--active' : ''}`}
          onClick={onSelectCaptures}
        >
          <span className="navitem__icon">
            <CalendarIcon />
          </span>
          <span className="navitem__label">Captures</span>
          {typeof capturesCount === 'number' && capturesCount > 0 && (
            <span className="navitem__count">{capturesCount}</span>
          )}
        </button>

        <button
          className={`navitem ${activeView === 'insights' ? 'navitem--active' : ''}`}
          onClick={onSelectInsights}
        >
          <span className="navitem__icon">
            <SparkleIcon />
          </span>
          <span className="navitem__label">Insights</span>
        </button>
      </nav>
    </aside>
  );
}
