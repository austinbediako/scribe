import { BrandMark, SearchIcon } from './icons.jsx';

export function TopBar({ query, onQueryChange, status, user, onRefresh, onSync, onLogout, onHome }) {
  return (
    <header className="topbar">
      <button className="topbar__brand topbar__brand--btn" onClick={onHome} aria-label="Scribe home">
        <BrandMark size={28} />
        <span className="topbar__name">Scribe</span>
      </button>

      <div className="topbar__search">
        <span className="topbar__searchIcon">
          <SearchIcon />
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search meetings"
          aria-label="Search meetings"
        />
      </div>

      <div className="topbar__right">
        <span className={`status ${status?.hasApiKey ? 'status--on' : 'status--off'}`}>
          <span className="status__dot" />
          {status?.hasApiKey ? 'Connected' : 'Not connected'}
        </span>

        {user?.email && <span className="topbar__user">{user.email}</span>}
        {onLogout && (
          <button className="btn btn--ghost" onClick={onLogout}>
            Log out
          </button>
        )}
      </div>
    </header>
  );
}
