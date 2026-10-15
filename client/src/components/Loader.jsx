export function Loader({ label }) {
  return (
    <div className="loader" role="status" aria-label={label || 'Loading'}>
      <span className="loader__tile" aria-hidden="true">
        <span className="loader__bars">
          <i />
          <i />
          <i />
          <i />
          <i />
        </span>
      </span>
      {label && <span className="loader__label">{label}</span>}
    </div>
  );
}
