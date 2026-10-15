import { BrandMark } from './icons.jsx';

export function ConnectState() {
  return (
    <div className="connect">
      <div className="connect__card">
        <BrandMark size={44} />
        <h1 className="connect__title">Connect Granola</h1>
        <p className="connect__text">
          Scribe reads your meetings directly from the Granola API. Add your API key to the server
          and restart it — Scribe will pick it up automatically.
        </p>

        <ol className="connect__steps">
          <li>
            Open <code>server/.env</code> and set <code>GRANOLA_API_KEY</code> to your key.
          </li>
          <li>
            Restart the server with <code>npm run dev</code>.
          </li>
          <li>Press Refresh in the top bar.</li>
        </ol>

        <p className="connect__note">
          Keys come from the Granola desktop app under Settings, then Connectors. A Business or
          Enterprise workspace is required.
        </p>
      </div>
    </div>
  );
}
