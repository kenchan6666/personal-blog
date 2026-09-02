import Link from "next/link";

type Back = {
  href: string;
  label: string;
};

type FrameProps = {
  title: string;
  lead?: string;
  back?: Back;
  narrow?: boolean;
  children: React.ReactNode;
};

export function PageFrame({ title, lead, back, narrow, children }: FrameProps) {
  return (
    <section className="page-frame">
      <div className={`page-frame-inner${narrow ? " is-narrow" : ""}`}>
        {back ? (
          <Link href={back.href} className="page-back">
            ← {back.label}
          </Link>
        ) : null}
        <h1 className="page-title display-font">{title}</h1>
        {lead ? <p className="page-lead">{lead}</p> : null}
        {children}
      </div>
    </section>
  );
}

type PanelProps = {
  label?: string;
  children: React.ReactNode;
};

export function PagePanel({ label, children }: PanelProps) {
  return (
    <div className="page-panel glass">
      {label ? <p className="page-panel-label">{label}</p> : null}
      {children}
    </div>
  );
}
