import type { ReactNode } from "react";
import {
  detectContactKind,
  isExternalContactHref,
  normalizeContactHref,
  type ContactKind,
} from "@/lib/contact-link";

type ProfileLink = {
  label: string;
  url: string;
  order: number;
};

type Contact = {
  href: string;
  label: string;
  kind: ContactKind;
  external: boolean;
};

const icons: Record<ContactKind, ReactNode> = {
  email: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <rect x="3.2" y="5.2" width="17.6" height="13.6" rx="2" />
      <path d="m4.2 7.1 7.8 6.2 7.8-6.2" />
    </svg>
  ),
  phone: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  ),
  github: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path
        className="icon-solid"
        d="M12 2C6.48 2 2 6.58 2 12.26c0 4.52 2.87 8.36 6.84 9.72.5.1.68-.22.68-.49 0-.24-.01-.87-.01-1.71-2.78.62-3.37-1.37-3.37-1.37-.45-1.18-1.11-1.5-1.11-1.5-.91-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.89 1.57 2.34 1.12 2.91.85.09-.67.35-1.12.63-1.37-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.7 0 0 .84-.27 2.75 1.05A9.3 9.3 0 0 1 12 6.84c.85 0 1.71.12 2.51.35 1.9-1.32 2.74-1.05 2.74-1.05.55 1.4.2 2.44.1 2.7.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.8-4.58 5.06.36.32.68.94.68 1.9 0 1.37-.01 2.47-.01 2.8 0 .27.18.6.69.49A10.05 10.05 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z"
      />
    </svg>
  ),
  x: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path
        className="icon-solid"
        d="M16.6 3.2h3.1l-6.8 7.77 8 10.83h-6.26l-4.9-6.4-5.6 6.4H1.04l7.27-8.31L.64 3.2h6.42l4.42 5.85 5.12-5.85Zm-1.1 16.7h1.72L6.58 4.94H4.74l10.76 14.96Z"
      />
    </svg>
  ),
  telegram: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M21.2 4.6 3.7 11.3c-1.2.46-1.19 1.1-.22 1.39l4.5 1.4 1.74 5.34c.23.7.12.97.8.97.42 0 .6-.19.83-.42l2-1.94 4.16 3.07c.76.42 1.31.2 1.5-.71l2.72-12.82c.28-1.12-.43-1.63-1.53-1.28Z" />
      <path d="m10.1 14.05.4 4.18s.2.82.8 0l1.92-1.84" />
    </svg>
  ),
  whatsapp: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path
        className="icon-solid"
        d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"
      />
    </svg>
  ),
  rss: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <circle cx="6.4" cy="17.6" r="1.7" className="icon-solid" />
      <path d="M4.6 10.2a9.2 9.2 0 0 1 9.2 9.2" />
      <path d="M4.6 5.4A14 14 0 0 1 18.6 19.4" />
    </svg>
  ),
  linkedin: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <rect x="3.4" y="3.4" width="17.2" height="17.2" rx="2.2" />
      <path d="M8.2 10.2v6.6M8.2 7.5v.2M11.6 16.8v-4.1c0-1.4.8-2.1 1.9-2.1s1.9.8 1.9 2.1v4.1" />
    </svg>
  ),
  instagram: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <rect x="3.6" y="3.6" width="16.8" height="16.8" rx="5" />
      <circle cx="12" cy="12" r="3.6" />
      <circle cx="17.1" cy="6.9" r="0.9" className="icon-solid" />
    </svg>
  ),
  youtube: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <rect x="2.6" y="6.2" width="18.8" height="11.6" rx="3.2" />
      <path className="icon-solid" d="M10.4 9.6v4.8l4.4-2.4z" />
    </svg>
  ),
  discord: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M8.4 7.2c1.4-.6 2.7-.8 3.6-.85.9.05 2.2.25 3.6.85 1.7.7 2.8 1.85 3.3 3.15.7 1.85.9 3.65.95 5.15 0 .15-.05.3-.15.4-1.05.9-2.1 1.5-3.1 1.9-.2.08-.42 0-.52-.18l-.55-1.05c1.05-.35 1.9-.85 2.55-1.4.15-.12.16-.34.02-.48-.12-.12-.32-.14-.47-.05-1.55.95-3.25 1.5-5.08 1.5s-3.53-.55-5.08-1.5c-.15-.09-.35-.07-.47.05-.14.14-.13.36.02.48.65.55 1.5 1.05 2.55 1.4l-.55 1.05c-.1.18-.32.26-.52.18-1-.4-2.05-1-3.1-1.9-.1-.1-.15-.25-.15-.4.05-1.5.25-3.3.95-5.15.5-1.3 1.6-2.45 3.3-3.15Z" />
      <circle cx="9.4" cy="12.4" r="1.15" className="icon-solid" />
      <circle cx="14.6" cy="12.4" r="1.15" className="icon-solid" />
    </svg>
  ),
  resume: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M7.2 3.6h7.1L19 8.4v12c0 .9-.7 1.6-1.6 1.6H7.2c-.9 0-1.6-.7-1.6-1.6V5.2c0-.9.7-1.6 1.6-1.6Z" />
      <path d="M14.2 3.8V8h4.6M8.4 12.2h7.2M8.4 15.4h7.2M8.4 18.5h4.6" />
    </svg>
  ),
  link: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M10.2 13.8a4.2 4.2 0 0 0 6 0l2.4-2.4a4.2 4.2 0 0 0-6-6l-1.4 1.4" />
      <path d="M13.8 10.2a4.2 4.2 0 0 0-6 0L5.4 12.6a4.2 4.2 0 1 0 6 6l1.4-1.4" />
    </svg>
  ),
};

function toContacts(email: string, links: ProfileLink[]): Contact[] {
  const items: Contact[] = [];
  const trimmed = email.trim();
  if (trimmed) {
    items.push({
      href: `mailto:${trimmed}`,
      label: trimmed,
      kind: "email",
      external: false,
    });
  }
  for (const link of [...links].sort((a, b) => a.order - b.order)) {
    const raw = link.url.trim();
    if (!raw) continue;
    const label = link.label.trim() || raw;
    const href = normalizeContactHref(raw, label);
    items.push({
      href,
      label,
      kind: detectContactKind(href, label),
      external: isExternalContactHref(href),
    });
  }
  return items;
}

export function ProfileContacts({
  email,
  links,
}: {
  email: string;
  links: ProfileLink[];
}) {
  const contacts = toContacts(email, links);
  if (contacts.length === 0) return null;

  return (
    <ul className="profile-contacts">
      {contacts.map((contact) => (
        <li key={`${contact.kind}-${contact.href}`}>
          <a
            href={contact.href}
            className="profile-contact"
            aria-label={contact.label}
            title={contact.label}
            {...(contact.external
              ? { target: "_blank", rel: "noreferrer" }
              : {})}
          >
            {icons[contact.kind]}
          </a>
        </li>
      ))}
    </ul>
  );
}
