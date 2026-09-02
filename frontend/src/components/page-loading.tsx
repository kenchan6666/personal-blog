export function SoftLoader({ label }: { label?: string }) {
  return (
    <div className="soft-loader" role="status" aria-label={label} aria-busy="true">
      <span />
      <span />
      <span />
    </div>
  );
}
