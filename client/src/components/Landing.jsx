import { BrandMark, CheckIcon } from './icons.jsx';

const points = [
  'Every insight links to a real transcript moment',
  'One micro-action per week, not a report',
  'Your data stays yours — owner-scoped, never shared',
];

function MeetingOrbit() {
  return (
    <div className="hero__visual" aria-hidden="true">
      <div className="hero__card hero__card--main">
        <div className="hero__cardTop">
          <span className="hero__pill">This week</span>
          <span className="hero__dot" />
        </div>
        <div className="hero__cardTitle">Strength</div>
        <div className="hero__bar hero__bar--strong" />
        <div className="hero__bar hero__bar--soft" />
        <div className="hero__cardTitle hero__cardTitle--growth">Growth area</div>
        <div className="hero__bar hero__bar--growth" />
        <div className="hero__micro">
          <span className="hero__microIcon">↗</span>
          <span>Try inviting one new perspective</span>
        </div>
      </div>

      <div className="hero__chip hero__chip--left">
        <span className="hero__chipIcon">?</span>
        <span>Open-ended question</span>
      </div>
      <div className="hero__chip hero__chip--right">
        <span className="hero__chipIcon">
          <CheckIcon />
        </span>
        <span>Contribution recognized</span>
      </div>

      <svg className="hero__wave" viewBox="0 0 420 260" preserveAspectRatio="none">
        <defs>
          <linearGradient id="waveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(109,40,217,0.35)" />
            <stop offset="50%" stopColor="rgba(109,40,217,0.85)" />
            <stop offset="100%" stopColor="rgba(91,33,182,0.55)" />
          </linearGradient>
        </defs>
        <path
          className="hero__wavePath"
          d="M0 150 C 40 100, 80 200, 120 140 S 180 60, 240 130 S 300 210, 360 130 S 400 120, 420 150"
          fill="none"
          stroke="url(#waveGrad)"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <path
          className="hero__wavePath hero__wavePath--soft"
          d="M0 180 C 50 130, 90 230, 140 170 S 200 90, 260 160 S 320 230, 380 160 S 410 150, 420 180"
          fill="none"
          stroke="rgba(109,40,217,0.15)"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}

export function Landing({ onOpen, onSignUp }) {
  return (
    <div className="landing landing--premium">
      <header className="landing__nav">
        <div className="landing__brand">
          <BrandMark size={30} />
          <span className="landing__brandName">Scribe</span>
        </div>
        <div className="landing__navActions">
          <button className="btn btn--ghost" onClick={onOpen}>
            Sign in
          </button>
          <button className="btn btn--primary" onClick={onSignUp}>
            Sign up
          </button>
        </div>
      </header>

      <main className="hero hero--premium">
        <div className="hero__grid">
          <div className="hero__copy">
            <p className="hero__eyebrow">Leadership coaching from meeting data</p>
            <h1 className="hero__title">
              Your meetings already
              <br />
              <span className="hero__titleAccent">know how you lead.</span>
            </h1>
            <p className="hero__text">
              Scribe reads the transcripts of meetings you already run, finds the
              moments that shaped the room, and turns them into one coaching action
              each week.
            </p>
            <div className="hero__actions">
              <button className="btn btn--primary btn--lg" onClick={onSignUp}>
                Get your first insight
              </button>
              <button className="btn btn--outline btn--lg" onClick={onOpen}>
                Sign in
              </button>
            </div>
            <p className="hero__footnote">
              Powered by Recall.ai — works with Google Meet, Zoom, Teams, and Webex.
            </p>
          </div>
          <MeetingOrbit />
        </div>
      </main>

      <footer className="landing__strip">
        <ul className="landing__points">
          {points.map((point) => (
            <li key={point}>
              <CheckIcon />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </footer>
    </div>
  );
}
