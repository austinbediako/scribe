import { useCallback, useEffect, useRef, useState } from 'react';
import { api, setToken, clearToken, wsUrl } from './api.js';
import { TopBar } from './components/TopBar.jsx';
import { Sidebar } from './components/Sidebar.jsx';
import { NotesList } from './components/NotesList.jsx';
import { NoteDetail } from './components/NoteDetail.jsx';
import { MeetingCapturePanel } from './components/MeetingCapturePanel.jsx';
import { Auth } from './components/Auth.jsx';
import { Landing } from './components/Landing.jsx';
import { Insights } from './components/Insights.jsx';
import { CalendarIcon, NoteIcon, SparkleIcon } from './components/icons.jsx';
import { Loader } from './components/Loader.jsx';

function notesFrom(data) {
  return Array.isArray(data) ? data : data?.notes || data?.results || [];
}

function currentPath() {
  return window.location.pathname || '/';
}

function normalizePath(path) {
  if (path === '/signin' || path === '/signup') return path;
  if (path === '/app' || path === '/app/meetings' || path === '/app/insights' || path === '/app/captures') return path;
  if (/^\/app\/meetings\/[^/]+$/.test(path)) return path;
  if (path === '/landing' || path === '/') return '/';
  return '/';
}

export default function App() {
  const [path, setPath] = useState(() => normalizePath(currentPath()));
  const [token, setTokenState] = useState(() => localStorage.getItem('scribe_token'));
  const wsRef = useRef(null);
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(null);
  const [notes, setNotes] = useState([]);
  const [captures, setCaptures] = useState([]);
  const [query, setQuery] = useState('');
  const [selectedNoteId, setSelectedNoteId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('list');

  const navigate = useCallback((to) => {
    const next = normalizePath(to);
    if (next !== window.location.pathname) {
      window.history.pushState({}, '', next);
    }
    setPath(next);
  }, []);

  useEffect(() => {
    const onPopState = () => setPath(normalizePath(currentPath()));
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    if (path === '/app/insights') setActiveView('insights');
    else if (path === '/app/captures') setActiveView('captures');
    else setActiveView('list');
  }, [path]);
  useEffect(() => {
    const match = path.match(/^\/app\/meetings\/([^/]+)$/);
    setSelectedNoteId(match ? decodeURIComponent(match[1]) : null);
  }, [path]);

  const loadNotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, data, me, captureData] = await Promise.all([
        api.status().catch(() => ({ hasApiKey: true, demo_mode: true })),
        api.notes(),
        api.me().catch(() => null),
        api.captures(),
      ]);
      setStatus(s);
      setNotes(notesFrom(data));
      setUser(me);
      setCaptures(Array.isArray(captureData) ? captureData : []);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const syncNotes = async () => {
    setLoading(true);
    setError(null);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'sync' }));
      return;
    }
    try {
      await api.sync();
      await loadNotes();
    } catch (e) {
      setError(e);
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token || path !== '/app') return undefined;

    setLoading(true);
    setError(null);

    const socket = new WebSocket(wsUrl(token));
    wsRef.current = socket;

    socket.onopen = () => {
      socket.send(JSON.stringify({ type: 'sync' }));
    };

    const syncInterval = window.setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'sync' }));
      }
    }, 30000);

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'connected') {
          setNotes(Array.isArray(message.meetings) ? message.meetings : []);
          setLoading(false);
        } else if (message.type === 'meetings.updated') {
          setNotes(Array.isArray(message.meetings) ? message.meetings : []);
          setLoading(false);
        } else if (message.type === 'capture.updated' && message.capture) {
          setCaptures((current) => [
            message.capture,
            ...current.filter((capture) => capture.id !== message.capture.id),
          ]);
        }
      } catch (err) {
        setError({ message: 'Received an invalid real-time update.' });
        setLoading(false);
      }
    };

    socket.onerror = () => {
      setError({ message: 'Real-time connection failed; falling back to manual refresh.' });
      loadNotes();
      setLoading(false);
    };

    socket.onclose = () => {
      wsRef.current = null;
    };

    return () => {
      window.clearInterval(syncInterval);
      socket.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, path]);

  useEffect(() => {
    if (!token) return;
    api.status().then(setStatus).catch(() => setStatus({ hasApiKey: true, demo_mode: true }));
    api.me().then(setUser).catch(() => setUser(null));
  }, [token]);

  useEffect(() => {
    if (!token && path === '/app') {
      navigate('/signin');
    }
  }, [token, path, navigate]);

  const handleAuthenticated = (authUser, authToken) => {
    if (authToken) setTokenState(authToken);
    else setTokenState(localStorage.getItem('scribe_token'));
    setUser(authUser);
    navigate('/app');
  };

  const handleLogout = () => {
    clearToken();
    setTokenState(null);
    setUser(null);
    setNotes([]);
    navigate('/');
  };

  useEffect(() => {
    const onExpired = () => handleLogout();
    window.addEventListener('scribe:unauthorized', onExpired);
    return () => window.removeEventListener('scribe:unauthorized', onExpired);
  }, []);

  const isAuthPath = path === '/signin' || path === '/signup';
  const authMode = path === '/signup' ? 'signup' : 'login';
  const showLanding = path === '/';

  if (showLanding) {
    return (
      <Landing
        onOpen={() => navigate('/signin')}
        onSignUp={() => navigate('/signup')}
      />
    );
  }

  if (isAuthPath) {
    return (
      <Auth
        initialMode={authMode}
        onAuthenticated={handleAuthenticated}
      />
    );
  }

  if (path !== '/app' && path !== '/app/meetings' && path !== '/app/insights' && path !== '/app/captures' && !/^\/app\/meetings\/[^/]+$/.test(path)) {
    return null;
  }

  const visibleNotes = notes.filter((note) =>
    (note.title || '').toLowerCase().includes(query.trim().toLowerCase())
  );

  return (
    <div className="app app--premium">
      <TopBar
        query={query}
        onQueryChange={setQuery}
        status={status || (user ? { hasApiKey: true } : null)}
        user={user}
        onLogout={handleLogout}
        onHome={() => navigate('/')}
      />

      {loading && (
        <div className="app__loading">
          <Loader label="Loading your meetings" />
        </div>
      )}

      {error && (
        <div className="banner banner--error">
          {error.code === 'NO_API_KEY'
            ? 'No API key configured on the server.'
            : `Couldn’t load meetings — ${error.message}`}
        </div>
      )}

      <div className="workspace">
        <Sidebar
          folders={[]}
          activeFolder={null}
          onSelectFolder={() => {}}
          totalCount={notes.length}
          activeView={activeView}
          onSelectAll={() => {
            setSelectedNoteId(null);
            navigate('/app');
          }}
          onSelectInsights={() => {
            setSelectedNoteId(null);
            navigate('/app/insights');
          }}
          onSelectCaptures={() => {
            setSelectedNoteId(null);
            navigate('/app/captures');
          }}
          capturesCount={captures.length}
        />

        <main className="content">
          {selectedNoteId ? (
            <NoteDetail noteId={selectedNoteId} onBack={() => navigate('/app')} />
          ) : activeView === 'captures' ? (
            <MeetingCapturePanel captures={captures} onChanged={loadNotes} />
          ) : activeView === 'insights' ? (
            <Insights />
          ) : (
            <NotesList
              notes={visibleNotes}
              onOpen={(id) => navigate(`/app/meetings/${encodeURIComponent(id)}`)}
              onLoadMore={() => {}}
              hasMore={false}
              loadingMore={false}
            />
          )}
        </main>
      </div>

      <nav className="tabbar" aria-label="Primary">
        <button
          type="button"
          className={`tabbar__item ${activeView === 'list' && !selectedNoteId ? 'tabbar__item--active' : ''}`}
          onClick={() => {
            setSelectedNoteId(null);
            navigate('/app');
          }}
        >
          <NoteIcon />
          <span>Meetings</span>
        </button>
        <button
          type="button"
          className={`tabbar__item ${activeView === 'captures' ? 'tabbar__item--active' : ''}`}
          onClick={() => {
            setSelectedNoteId(null);
            navigate('/app/captures');
          }}
        >
          <CalendarIcon />
          <span>Captures</span>
        </button>
        <button
          type="button"
          className={`tabbar__item ${activeView === 'insights' ? 'tabbar__item--active' : ''}`}
          onClick={() => {
            setSelectedNoteId(null);
            navigate('/app/insights');
          }}
        >
          <SparkleIcon />
          <span>Insights</span>
        </button>
      </nav>
    </div>
  );
}