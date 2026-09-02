import { mediaUrl, type HeroVisual as HeroVisualConfig } from "@/lib/api";

type Props = {
  visual?: HeroVisualConfig | null;
};

export function HeroVisual({ visual }: Props) {
  if (visual?.url) {
    const src = mediaUrl(visual.url);
    const scale = Math.max(0.8, (visual.scale || 100) / 100);
    const blur = Math.max(0, visual.blur || 0);
    return (
      <div className="hero-photo">
        <img
          src={src}
          alt=""
          style={{
            transform: `translate(${(visual.posX - 50) * 0.4}%, ${(visual.posY - 50) * 0.4}%) scale(${scale})`,
            filter: blur ? `blur(${blur}px)` : undefined,
          }}
        />
      </div>
    );
  }

  return (
    <div
      className="relative h-full min-h-[220px] w-full sm:min-h-[340px] lg:min-h-[420px]"
      aria-hidden
    >
      <div className="absolute inset-[8%] rounded-[2.5rem] bg-gradient-to-br from-[#c4b5fd]/40 via-[#9fd4ff]/22 to-[#ffd6c8]/18 blur-3xl" />
    </div>
  );
}
