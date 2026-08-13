export function HeroVisual() {
  return (
    <div
      className="relative h-full min-h-[280px] w-full sm:min-h-[340px] lg:min-h-[420px]"
      aria-hidden
    >
      <div className="absolute inset-[8%] rounded-[2rem] bg-gradient-to-br from-[#7c3aed]/55 via-[#a78bfa]/25 to-transparent blur-2xl" />

      <div className="glass absolute top-[12%] right-[8%] h-[58%] w-[72%] rounded-[1.75rem] p-4">
        <div className="mb-3 flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-[#ff5c7a]/90" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#c4b5fd]/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-white/35" />
        </div>
        <div className="space-y-2.5">
          <div className="h-3 w-[78%] rounded-full bg-white/25" />
          <div className="h-3 w-[62%] rounded-full bg-white/15" />
          <div className="mt-4 grid grid-cols-3 gap-2">
            <div className="h-16 rounded-xl bg-gradient-to-b from-[#c4b5fd]/50 to-[#7c3aed]/20" />
            <div className="h-16 rounded-xl bg-gradient-to-b from-[#ff7a59]/45 to-[#ff5c7a]/15" />
            <div className="h-16 rounded-xl bg-gradient-to-b from-white/25 to-white/5" />
          </div>
          <div className="mt-3 h-20 rounded-xl border border-white/10 bg-black/20" />
        </div>
      </div>

      <div className="glass glass-hover absolute bottom-[10%] left-[4%] w-[46%] rounded-2xl p-4">
        <div className="mb-2 flex items-end gap-1.5">
          <span className="w-2 rounded-sm bg-[#c4b5fd]" style={{ height: 18 }} />
          <span className="w-2 rounded-sm bg-[#a78bfa]" style={{ height: 28 }} />
          <span className="w-2 rounded-sm bg-[#ff5c7a]" style={{ height: 22 }} />
          <span className="w-2 rounded-sm bg-[#ff7a59]" style={{ height: 34 }} />
          <span className="w-2 rounded-sm bg-white/50" style={{ height: 14 }} />
        </div>
        <p className="display-font text-xs font-semibold tracking-wide text-white/80">
          SHIPPED WORK
        </p>
      </div>

      {/* Pixel accent — signature only */}
      <div
        className="absolute top-[6%] left-[12%] grid grid-cols-4 gap-0.5 opacity-90"
        style={{ imageRendering: "pixelated" }}
      >
        {[
          1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0,
        ].map((on, i) => (
          <span
            key={i}
            className={`h-2 w-2 ${on ? "bg-[#ff5c7a]" : "bg-transparent"}`}
          />
        ))}
      </div>
    </div>
  );
}
