type Props = {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
};

export function CmsCard({ title, action, children }: Props) {
  return (
    <section className="cms-card glass rounded-[var(--radius-panel)] p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="display-font text-xl font-bold">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function StatusPill({
  published,
  publishedLabel,
  draftLabel,
}: {
  published: boolean;
  publishedLabel: string;
  draftLabel: string;
}) {
  return (
    <span className={`status-pill ${published ? "status-pill-live" : ""}`}>
      {published ? publishedLabel : draftLabel}
    </span>
  );
}
