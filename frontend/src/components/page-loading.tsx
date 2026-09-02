export function SoftLoader({ label }: { label?: string }) {
  return (
    <div className="soft-loader" role="status" aria-label={label || "Loading"}>
      <span />
      <span />
      <span />
    </div>
  );
}
