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

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  if (!children) return null;
  return (
    <>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </>
  );
}

export function ProfileSection({ content }: Props) {
  const avatarSrc = mediaUrl(content.avatarUrl);
  const hasBody =
    avatarSrc || content.bio || content.skills || content.experience;

  if (!hasBody) return null;

  return (
    <section id="profile" className="home-section">
      <div className="home-wrap">
        <div className="home-section-head">
          <h2>{content.title}</h2>
        </div>
        <div className="home-profile">
          {avatarSrc ? (
            <img
              src={avatarSrc}
              alt=""
              width={96}
              height={96}
              loading="lazy"
              decoding="async"
              className="home-profile-avatar"
            />
          ) : null}
          <dl className="home-profile-facts">
            <Row label={content.bioLabel}>{content.bio}</Row>
            <Row label={content.skillsLabel}>{content.skills}</Row>
            <Row label={content.experienceLabel}>{content.experience}</Row>
          </dl>
        </div>
      </div>
    </section>
  );
}
