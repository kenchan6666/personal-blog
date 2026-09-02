"use client";

import { useRef } from "react";
import { mediaUrl, type OwnerSite } from "@/lib/api";

type Labels = {
  fieldHeroVisual: string;
  uploadHeroVisual: string;
  uploadingHeroVisual: string;
  clearHeroVisual: string;
  heroVisualHint: string;
  heroVisualPosX: string;
  heroVisualPosY: string;
  heroVisualScale: string;
  heroVisualBlur: string;
  noHeroVisual: string;
};

type Props = {
  site: OwnerSite;
  labels: Labels;
  uploading: boolean;
  onUpload: (file: File) => void;
  onClear: () => void;
  onChange: (patch: Partial<OwnerSite>) => void;
};

function clamp(value: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, value));
}

export function HeroVisualEditor({
  site,
  labels,
  uploading,
  onUpload,
  onClear,
  onChange,
}: Props) {
  const stageRef = useRef<HTMLDivElement>(null);

  function placeFromEvent(event: React.PointerEvent<HTMLDivElement>) {
    const box = stageRef.current?.getBoundingClientRect();
    if (!box) return;
    onChange({
      heroVisualPosX: clamp(((event.clientX - box.left) / box.width) * 100, 0, 100),
      heroVisualPosY: clamp(((event.clientY - box.top) / box.height) * 100, 0, 100),
    });
  }

  return (
    <div className="mb-8">
      <p className="mb-2 text-sm font-semibold">{labels.fieldHeroVisual}</p>
      <p className="mb-3 text-xs text-[var(--text-muted)]">{labels.heroVisualHint}</p>
      <div className="hero-visual-editor">
        <div
          ref={stageRef}
          className={`hero-visual-stage${site.heroVisualUrl ? " is-live" : ""}`}
          onPointerDown={(event) => {
            if (!site.heroVisualUrl) return;
            event.currentTarget.setPointerCapture(event.pointerId);
            placeFromEvent(event);
          }}
          onPointerMove={(event) => {
            if (!site.heroVisualUrl || event.buttons === 0) return;
            placeFromEvent(event);
          }}
        >
          {site.heroVisualUrl ? (
            <img
              src={mediaUrl(site.heroVisualUrl)}
              alt=""
              draggable={false}
              style={{
                transform: `translate(${(site.heroVisualPosX - 50) * 0.4}%, ${(site.heroVisualPosY - 50) * 0.4}%) scale(${site.heroVisualScale / 100})`,
                filter: site.heroVisualBlur
                  ? `blur(${site.heroVisualBlur}px)`
                  : undefined,
              }}
            />
          ) : (
            <p>{labels.noHeroVisual}</p>
          )}
        </div>
        <div className="hero-visual-controls">
          <div className="flex flex-wrap gap-2">
            <label className="btn-ghost cursor-pointer text-sm">
              {uploading ? labels.uploadingHeroVisual : labels.uploadHeroVisual}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="sr-only"
                disabled={uploading}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.target.value = "";
                  if (file) onUpload(file);
                }}
              />
            </label>
            {site.heroVisualUrl ? (
              <button
                type="button"
                className="btn-ghost text-sm"
                onClick={onClear}
              >
                {labels.clearHeroVisual}
              </button>
            ) : null}
          </div>
          {site.heroVisualUrl ? (
            <div className="hero-visual-sliders">
              <Slider
                label={labels.heroVisualPosX}
                value={site.heroVisualPosX}
                min={0}
                max={100}
                onChange={(heroVisualPosX) => onChange({ heroVisualPosX })}
              />
              <Slider
                label={labels.heroVisualPosY}
                value={site.heroVisualPosY}
                min={0}
                max={100}
                onChange={(heroVisualPosY) => onChange({ heroVisualPosY })}
              />
              <Slider
                label={labels.heroVisualScale}
                value={site.heroVisualScale}
                min={80}
                max={180}
                onChange={(heroVisualScale) => onChange({ heroVisualScale })}
              />
              <Slider
                label={labels.heroVisualBlur}
                value={site.heroVisualBlur}
                min={0}
                max={48}
                onChange={(heroVisualBlur) => onChange({ heroVisualBlur })}
              />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="hero-visual-slider">
      <span>
        {label}
        <em>{Math.round(value)}</em>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
