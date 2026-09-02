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
    avatarSrc || content.bio || content.skills || content.experience;

  if (!hasBody) return null;

  return (
    <section
      id="profile"
      className="hairline-t px-5 py-14 sm:px-10 sm:py-16 lg:px-14"
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
      </div>
    </section>
  );
}
