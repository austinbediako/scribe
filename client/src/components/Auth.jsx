import { useState } from 'react';
import { api, setToken } from '../api.js';
import { BrandMark, CheckIcon } from './icons.jsx';

function AuthIllustration() {
  return (
    <svg viewBox="0 0 440 380" fill="none" aria-hidden="true" className="authArt">
      {/* soft backdrop */}
      <rect x="24" y="30" width="392" height="320" rx="28" fill="var(--purple-soft)" />

      {/* meeting document */}
      <rect x="64" y="76" width="212" height="236" rx="16" fill="#ffffff" stroke="var(--line)" />
      <rect x="84" y="98" width="80" height="10" rx="5" fill="var(--ink)" fillOpacity="0.85" />
      <rect x="84" y="116" width="46" height="7" rx="3.5" fill="var(--muted-2)" />

      {/* transcript lines */}
      <rect x="84" y="140" width="150" height="8" rx="4" fill="var(--line-soft)" />
      <rect x="84" y="156" width="172" height="8" rx="4" fill="var(--line-soft)" />
      <rect x="84" y="172" width="120" height="8" rx="4" fill="var(--line-soft)" />

      {/* highlighted evidence line */}
      <rect x="78" y="192" width="184" height="30" rx="8" fill="var(--purple-soft)" />
      <rect x="88" y="202" width="128" height="8" rx="4" fill="var(--purple)" fillOpacity="0.55" />
      <circle cx="240" cy="207" r="8" fill="var(--purple)" />
      <path d="M236.5 207.5l2.4 2.4 4.2-4.6" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />

      <rect x="84" y="236" width="156" height="8" rx="4" fill="var(--line-soft)" />
      <rect x="84" y="252" width="134" height="8" rx="4" fill="var(--line-soft)" />
      <rect x="84" y="268" width="160" height="8" rx="4" fill="var(--line-soft)" />

      {/* connector */}
      <path d="M276 200 C 306 200 300 168 330 168" stroke="var(--purple-line)" strokeWidth="2.5" strokeDasharray="5 6" strokeLinecap="round" />

      {/* insight card */}
      <g filter="drop-shadow(0 10px 24px rgba(93,40,217,0.14))">
        <rect x="292" y="128" width="108" height="118" rx="14" fill="#ffffff" stroke="var(--purple-line)" />
      </g>
      <rect x="304" y="142" width="58" height="9" rx="4.5" fill="var(--purple)" />
      <rect x="304" y="162" width="84" height="7" rx="3.5" fill="var(--line)" />
      <rect x="304" y="176" width="72" height="7" rx="3.5" fill="var(--line)" />
      <rect x="304" y="196" width="84" height="36" rx="9" fill="var(--purple-soft)" />
      <rect x="312" y="208" width="46" height="7" rx="3.5" fill="var(--purple)" fillOpacity="0.7" />
      <circle cx="382" cy="214" r="9" fill="var(--purple)" />
      <path d="M378 214.5l3 3 5-5.4" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />

      {/* waveform */}
      <g stroke="var(--purple)" strokeLinecap="round">
        <path d="M300 296v10M310 288v26M320 294v14M330 282v38M340 292v18M350 286v30M360 296v10M370 290v22M380 298v6" strokeWidth="3.4" opacity="0.75" />
      </g>

      {/* speaker dots */}
      <circle cx="64" cy="330" r="10" fill="#0ea5e9" fillOpacity="0.25" stroke="#0ea5e9" />
      <circle cx="92" cy="338" r="7" fill="#0ea5e9" fillOpacity="0.5" />
      <circle cx="390" cy="80" r="9" fill="var(--purple)" fillOpacity="0.18" stroke="var(--purple)" strokeOpacity="0.6" />
      <circle cx="412" cy="98" r="6" fill="var(--purple)" fillOpacity="0.4" />
    </svg>
  );
}

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
      <div className="auth__panel">
        <aside className="auth__aside">
          <div className="auth__asideBrand">
            <BrandMark size={30} />
            <span>Scribe</span>
          </div>
          <div className="auth__asideCopy">
            <h2>Your meetings, turned into coaching.</h2>
            <p>
              Scribe reads the transcript, flags the leadership moments, and hands you
              one small thing to try next time.
            </p>
          </div>
          <AuthIllustration />
          <ul className="auth__asidePoints">
            <li>
              <CheckIcon /> Evidence-linked insights
            </li>
            <li>
              <CheckIcon /> Owner-private by default
            </li>
          </ul>
        </aside>

        <div className="auth__main">
          <div className="auth__card">
            <div className="auth__brand auth__brand--mobile">
              <BrandMark size={30} />
              <span>Scribe</span>
            </div>

            <div className="auth__tabs" role="tablist" aria-label="Authentication">
              <button
                type="button"
                role="tab"
                aria-selected={!isSignup}
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
                role="tab"
                aria-selected={isSignup}
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

              {error && (
                <div className="auth__error" role="alert">
                  {error}
                </div>
              )}

              <button className="auth__submit" type="submit" disabled={loading}>
                {loading ? (
                  <span className="auth__spinner" aria-hidden="true" />
                ) : isSignup ? (
                  'Create account'
                ) : (
                  'Sign in'
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
