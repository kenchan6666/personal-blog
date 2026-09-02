export function PixelSpinner({ label }: { label?: string }) {
  return (
    <span className="pixel-spinner" role="status" aria-label={label || "Loading"} />
  );
}

export function PageLoading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="page-loading" aria-busy="true" aria-live="polite">
      <div className="page-loading-copy">
        <PixelSpinner label={label} />
        <p>{label}</p>
      </div>
      <div className="skel skel-kicker" />
      <div className="skel skel-title" />
      <div className="skel skel-lead" />
      <div className="skel skel-panel" />
      <div className="skel skel-panel skel-panel-short" />
    </div>
  );
}
