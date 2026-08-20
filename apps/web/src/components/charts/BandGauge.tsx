"use client";

export function BandGauge({ latest, target }: { latest: number | null; target: number | null }) {
  const percent = Math.max(0, Math.min(100, ((latest ?? 0) / 9) * 100));
  return (
    <div className="gauge">
      <div className="gauge-ring" style={{ ["--p" as string]: percent }} aria-hidden="true">
        <span>
          <strong className="score-number">{latest?.toFixed(1) ?? "—"}</strong>
        </span>
      </div>
      <p className="muted">Target {target?.toFixed(1) ?? "not set"}</p>
    </div>
  );
}
