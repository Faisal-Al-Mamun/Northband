"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { fetchAuthedBlobUrl, api } from "@/lib/api";
import type { ContentSetDetail } from "@/lib/types";
import { formatClock } from "@/lib/labels";
import { Button } from "@/components/ui/Button";

type Mode = "exam" | "practice";

const PREVIEW_SEC = 30;

function sectionTitle(label: string, index: number) {
  const match = label.match(/(\d+)/);
  const n = match ? match[1] : String(index + 1);
  return `Section ${n}`;
}

export function ListeningDesk({
  detail,
  mode,
  remaining,
  running,
  setRunning,
  onSectionChange,
}: {
  detail: ContentSetDetail;
  mode: Mode;
  remaining: number;
  running: boolean;
  setRunning: (next: boolean | ((value: boolean) => boolean)) => void;
  onSectionChange?: (assetId: string | null) => void;
}) {
  const assets = useMemo(
    () => [...detail.audio_assets].sort((a, b) => a.order_index - b.order_index),
    [detail.audio_assets],
  );
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<"idle" | "preparing" | "ready" | "preview" | "playing" | "done">("idle");
  const [played, setPlayed] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  const [previewLeft, setPreviewLeft] = useState(PREVIEW_SEC);
  const audioNodes = useRef<Record<string, HTMLAudioElement | null>>({});
  const urlsRef = useRef<Record<string, string>>({});

  const current = assets[index];
  const exam = mode === "exam";
  const src = current ? urls[current.id] : "";

  useEffect(() => {
    onSectionChange?.(phase === "playing" ? current?.id ?? null : null);
  }, [current?.id, phase, onSectionChange]);

  useEffect(() => {
    let cancelled = false;
    const previous = urlsRef.current;
    Object.values(previous).forEach((url) => URL.revokeObjectURL(url));
    urlsRef.current = {};
    setUrls({});
    setIndex(0);
    setPlayed({});
    setProgress(0);
    setPhase("preparing");
    setError("");

    (async () => {
      try {
        const prepared = await api.prepareListeningAudio(detail.id);
        const next: Record<string, string> = {};
        const files = prepared.assets.length
          ? prepared.assets.map((asset) => ({ id: asset.id, path: `/content/audio/${asset.filename}` }))
          : assets.map((asset) => ({ id: asset.id, path: asset.url }));
        for (const item of files) {
          next[item.id] = await fetchAuthedBlobUrl(item.path);
        }
        if (cancelled) {
          Object.values(next).forEach((url) => URL.revokeObjectURL(url));
          return;
        }
        urlsRef.current = next;
        setUrls(next);
        setPhase("ready");
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not prepare the recording");
          setPhase("idle");
        }
      }
    })();

    return () => {
      cancelled = true;
      Object.values(urlsRef.current).forEach((url) => URL.revokeObjectURL(url));
      urlsRef.current = {};
    };
  }, [detail.id, assets]);

  function playAt(assetIndex: number) {
    const asset = assets[assetIndex];
    if (!asset) return;
    const node = audioNodes.current[asset.id];
    if (!node) return;
    Object.entries(audioNodes.current).forEach(([id, other]) => {
      if (other && id !== asset.id) {
        other.pause();
        other.currentTime = 0;
      }
    });
    setIndex(assetIndex);
    setProgress(0);
    setPhase("playing");
    setRunning(true);
    node.currentTime = 0;
    void node.play().catch(() => setError("The browser blocked playback. Click Play Section to try again."));
  }

  function startPreview(assetIndex: number) {
    setIndex(assetIndex);
    setProgress(0);
    setPreviewLeft(PREVIEW_SEC);
    setPhase("preview");
    setRunning(true);
  }

  function startTest() {
    setError("");
    setPlayed({});
    setProgress(0);
    if (exam) {
      startPreview(0);
      return;
    }
    playAt(0);
  }

  function onEnded(assetId: string) {
    setPlayed((prev) => ({ ...prev, [assetId]: true }));
    const endedIndex = assets.findIndex((item) => item.id === assetId);
    const next = endedIndex + 1;
    if (next > 0 && next < assets.length) {
      if (exam) startPreview(next);
      else playAt(next);
      return;
    }
    setPhase("done");
  }

  useEffect(() => {
    if (phase !== "preview") return;
    const id = window.setInterval(() => setPreviewLeft((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  useEffect(() => {
    if (phase !== "preview" || previewLeft > 0) return;
    playAt(index);
  }, [phase, previewLeft, index]);

  const durationLabel = current
    ? current.duration_sec >= 12
      ? `${Math.round(current.duration_sec / 60)} min ${Math.round(current.duration_sec % 60)}s`
      : "Full section"
    : "";

  return (
    <div className="card listen-desk">
      <div className="listen-desk-head">
        <div>
          <p className="eyebrow">Listening paper</p>
          <h3>{current ? sectionTitle(current.section_label, index) : "Recording"}</h3>
          <p className="muted">
            {assets.length} sections · {detail.questions.length} questions · {durationLabel}
            {current?.accent ? ` · ${current.accent}` : ""}
          </p>
        </div>
        <span className="timer-readout">{formatClock(Math.max(0, remaining))}</span>
      </div>

      {phase === "preparing" && (
        <p className="muted">
          Preparing the recording (Pocket TTS). The first run downloads the voice model and can take a few
          minutes; later visits reuse the saved WAV files.
        </p>
      )}
      {error && <p className="error">{error}</p>}

      {phase === "ready" && (
        <div className="listen-instructions">
          <p>
            You will hear each section once{exam ? "" : " (replay is allowed in practice)"}. Answer as you listen.
            {exam
              ? " You have 30 seconds to look at the questions before each section. Computer-delivered IELTS does not give extra transfer time after the recording."
              : " Computer-delivered IELTS does not give extra transfer time — keep typing while the recording plays."}
          </p>
          <Button onClick={startTest} disabled={!src}>
            {exam ? "Begin listening paper" : `Play Section ${assets.findIndex((item) => item.id === current?.id) + 1 || 1}`}
          </Button>
        </div>
      )}

      {phase === "preview" && current && (
        <div className="listen-instructions">
          <p className="elapsed">{formatClock(previewLeft)}</p>
          <p>
            Look at questions{" "}
            {detail.questions.filter((question) => question.audio_asset_id === current.id).length
              ? `${detail.questions.filter((question) => question.audio_asset_id === current.id)[0]?.number}–${
                  detail.questions.filter((question) => question.audio_asset_id === current.id).at(-1)?.number
                }`
              : "for this section"}
            . The recording starts automatically.
          </p>
          <Button size="sm" variant="secondary" onClick={() => playAt(index)}>
            Skip wait and play
          </Button>
        </div>
      )}

      {phase === "done" && (
        <p className="muted">The recording has finished. Check your answers, then submit.</p>
      )}

      {src && (
        <div className="listen-player">
          {assets.map((asset) => (
            <audio
              key={asset.id}
              ref={(node) => {
                audioNodes.current[asset.id] = node;
              }}
              className="audio-player"
              src={urls[asset.id]}
              controls={!exam && phase !== "ready" && asset.id === current?.id}
              hidden={phase === "ready" || phase === "preview" || asset.id !== current?.id}
              onEnded={() => onEnded(asset.id)}
              onPlay={() => {
                setIndex(assets.findIndex((item) => item.id === asset.id));
                setPhase("playing");
              }}
              onTimeUpdate={(event) => {
                if (asset.id !== current?.id) return;
                const el = event.currentTarget;
                if (el.duration && Number.isFinite(el.duration)) {
                  setProgress(el.currentTime / el.duration);
                }
              }}
            />
          ))}
          {phase !== "ready" && phase !== "preview" && (
            <>
              <div className="listen-progress" aria-hidden="true">
                <span style={{ width: `${Math.round(progress * 100)}%` }} />
              </div>
              <div className="btn-row">
                {!exam && (
                  <Button size="sm" variant="secondary" onClick={() => playAt(index)} disabled={!src}>
                    {phase === "playing" ? "Playing…" : "Play"}
                  </Button>
                )}
                {!exam && (
                  <Button size="sm" variant="ghost" onClick={() => setRunning((value) => !value)}>
                    {running ? "Pause timer" : "Start timer"}
                  </Button>
                )}
              </div>
              {exam && (
                <p className="muted">
                  Exam mode: each section plays once. Answers stay open until you submit or time runs out.
                </p>
              )}
            </>
          )}
        </div>
      )}

      {assets.length > 1 && (
        <div className="chip-row">
          {assets.map((asset, assetIndex) => (
            <button
              key={asset.id}
              type="button"
              className={`set-chip${assetIndex === index ? " is-on" : ""}`}
              disabled={exam}
              onClick={() => {
                if (exam) return;
                setIndex(assetIndex);
                setProgress(0);
                setPhase("ready");
              }}
            >
              <strong>{sectionTitle(asset.section_label, assetIndex)}</strong>
              <span>
                {played[asset.id] ? "Played · " : ""}
                {detail.questions.filter((q) => q.audio_asset_id === asset.id).length || "—"} questions
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
