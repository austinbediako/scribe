import { useState } from 'react';
import { api, setToken } from '../api.js';
import { BrandMark } from './icons.jsx';

export function Auth({ onAuthenticated, initialMode = 'login' }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const isSignup = mode === 'signup';

  const submit = async (event) => {
    event.preventDefault();
    setError(null);

    if (isSignup && password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      const result = isSignup
        ? await api.signup({ email, password })
        : await api.login({ email, password });
      const authToken = result.token || result.access_token;
      setToken(authToken);
      onAuthenticated(result.user, authToken);
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth__card">
        <div className="auth__brand">
          <BrandMark size={32} />
          <span>Scribe</span>
        </div>

        <div className="auth__tabs" role="tablist" aria-label="Authentication">
          <button
            type="button"
            className={`auth__tab ${!isSignup ? 'auth__tab--active' : ''}`}
            onClick={() => {
              setError(null);
              setMode('login');
            }}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`auth__tab ${isSignup ? 'auth__tab--active' : ''}`}
            onClick={() => {
              setError(null);
              setMode('signup');
            }}
          >
            Sign up
          </button>
        </div>

        <h1 className="auth__title">
          {isSignup ? 'Create your account' : 'Welcome back'}
        </h1>
        <p className="auth__subtitle">
          {isSignup
            ? 'Start turning meetings into leadership coaching.'
            : 'Sign in to see your meetings, insights, and micro-actions.'}
        </p>

        <form className="auth__form" onSubmit={submit}>
          <label className="auth__field">
            <span>Email</span>
            <input
              className="auth__input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </label>

          <label className="auth__field">
            <span>Password</span>
            <input
              className="auth__input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              required
            />
          </label>

          {error && <div className="auth__error">{error}</div>}

          <button className="auth__submit" type="submit" disabled={loading}>
            {loading ? <span className="auth__spinner" aria-hidden="true" /> : isSignup ? 'Create account' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}