import { mediaUrl } from "@/lib/api";

type ProfileLink = {
  label: string;
  url: string;
  order: number;
};

export type ProfileContent = {
  title: string;
  bioLabel: string;
  skillsLabel: string;
  experienceLabel: string;
  emailLabel: string;
  linksLabel: string;
  bio: string;
  skills: string;
  experience: string;
  publicEmail: string;
  avatarUrl: string;
  links: ProfileLink[];
};

type Props = {
  content: ProfileContent;
};

function Block({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  if (!children) return null;
  return (
    <div className="mb-8">
      <h3 className="mb-2 text-xs font-semibold tracking-[0.18em] text-[var(--accent-link)] uppercase">
        {label}
      </h3>
      <div className="whitespace-pre-wrap text-base leading-relaxed text-[var(--text-primary)]">
        {children}
      </div>
    </div>
  );
}

export function ProfileSection({ content }: Props) {
  const avatarSrc = mediaUrl(content.avatarUrl);
  const hasBody =
    avatarSrc ||
    content.bio ||
    content.skills ||
    content.experience ||
    content.publicEmail ||
    content.links.length > 0;

  if (!hasBody) return null;

  return (
    <section
      id="profile"
      className="border-t border-white/10 px-6 py-16 sm:px-10 lg:px-14"
    >
      <div className="mx-auto max-w-3xl">
        <h2 className="display-font mb-10 text-3xl font-bold tracking-tight">
          {content.title}
        </h2>
        {avatarSrc ? (
          <div className="mb-10">
            <img
              src={avatarSrc}
              alt=""
              width={128}
              height={128}
              className="avatar-frame h-32 w-32 object-cover"
            />
          </div>
        ) : null}
        <Block label={content.bioLabel}>{content.bio}</Block>
        <Block label={content.skillsLabel}>{content.skills}</Block>
        <Block label={content.experienceLabel}>{content.experience}</Block>
        <Block label={content.emailLabel}>
          {content.publicEmail ? (
            <a
              href={`mailto:${content.publicEmail}`}
              className="text-[var(--accent-link)] hover:underline"
            >
              {content.publicEmail}
            </a>
          ) : null}
        </Block>
        {content.links.length > 0 ? (
          <div>
            <h3 className="mb-3 text-xs font-semibold tracking-[0.18em] text-[var(--accent-link)] uppercase">
              {content.linksLabel}
            </h3>
            <ul className="flex flex-col gap-2">
              {content.links.map((link) => (
                <li key={`${link.order}-${link.url}`}>
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[var(--text-primary)] underline decoration-white/20 underline-offset-4 transition-colors hover:text-[var(--accent-link)] hover:decoration-[var(--accent-link)]"
                  >
                    {link.label || link.url}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}
