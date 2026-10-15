import { BrandMark, SparkleIcon, NoteIcon, FolderIcon, CheckIcon } from './icons.jsx';

const features = [
  {
    icon: <SparkleIcon />,
    title: 'Evidence-led coaching',
    text:
      'Scribe mines transcripts for the moments that matter — questions, instructions, and recognition — and ties every insight to real evidence.',
  },
  {
    icon: <NoteIcon />,
    title: 'One clear next step',
    text:
      'Each cycle delivers one strength, one growth area, and one micro-action you can try in your very next conversation.',
  },
  {
    icon: <FolderIcon />,
    title: 'Private by design',
    text:
      'Your meeting patterns stay yours. Encrypted in transit and owner-scoped at rest — never sent to your manager.',
  },
];

function MeetingOrbit() {
  return (
    <div className="hero__visual" aria-hidden="true">
      <div className="hero__halo" />
      <div className="hero__card hero__card--main">
        <div className="hero__cardTop">
          <span className="hero__pill">Insight card</span>
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
            <stop offset="0%" stopColor="rgba(139,92,246,0.45)" />
            <stop offset="50%" stopColor="rgba(168,85,247,0.95)" />
            <stop offset="100%" stopColor="rgba(236,72,153,0.65)" />
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
          stroke="rgba(139,92,246,0.18)"
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

      <section className="hero hero--premium">
        <div className="hero__grid">
          <div className="hero__copy">
            <p className="hero__eyebrow">Leadership coaching from meeting data</p>
            <h1 className="hero__title">
              Lead with more
              <br />
              <span className="hero__titleAccent">intention.</span>
            </h1>
            <p className="hero__text">
              Scribe listens to the meetings you already have, surfaces the moments that
              shape your leadership, and turns them into one small, repeatable action.
            </p>
            <div className="hero__actions">
              <button className="btn btn--primary btn--lg" onClick={onSignUp}>
                Start coaching
              </button>
              <button className="btn btn--outline btn--lg" onClick={onOpen}>
                Sign in
              </button>
            </div>
            <ul className="hero__meta">
              <li>
                <CheckIcon /> No training from scratch
              </li>
              <li>
                <CheckIcon /> Private by default
              </li>
              <li>
                <CheckIcon /> Grounded in real evidence
              </li>
            </ul>
          </div>
          <MeetingOrbit />
        </div>
      </section>

      <section className="features features--premium" id="features">
        {features.map((feature) => (
          <article className="feature feature--premium" key={feature.title}>
            <span className="feature__icon">{feature.icon}</span>
            <h3 className="feature__title">{feature.title}</h3>
            <p className="feature__text">{feature.text}</p>
          </article>
        ))}
      </section>

      <footer className="landing__footer">
        <p>
          Powered by Granola and Recall.ai. Works with Google Meet, Zoom, Teams, and Webex.
        </p>
      </footer>
    </div>
  );
}