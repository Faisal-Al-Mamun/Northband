"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ProgressSummary, StudyPlanItem } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorCard, PageHeader, PageSkeleton } from "@/components/ui/PageHeader";
import { BandTrendChart } from "@/components/charts/BandTrendChart";
import { drillHref, qtypeLabel, skillLabel } from "@/lib/labels";

export default function ProgressPage() {
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [plan, setPlan] = useState<StudyPlanItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    const [summary, items] = await Promise.all([api.progress(), api.studyPlan()]);
    setProgress(summary);
    setPlan(items);
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load progress"))
      .finally(() => setLoading(false));
  }, []);

  async function toggle(item: StudyPlanItem) {
    await api.updatePlanItem(item.id, item.status === "done" ? "pending" : "done");
    await load();
  }

  if (loading) return <PageSkeleton />;
  if (error) {
    return (
      <ErrorCard message={error}>
        <Button href="/app">Home</Button>
      </ErrorCard>
    );
  }

  const thin = (progress?.attempt_count || 0) < 2;
  const typeEntries = Object.entries(progress?.type_accuracy || {});

  return (
    <div className="section-gap">
      <PageHeader
        eyebrow="Review"
        title="Progress"
        lede="Four-skill practice estimates, question-type accuracy, and drills from your reports. These are not official IELTS scores."
      />
      <div className="card">
        <p className="muted">
          Overall is the mean of skills you have sat, half-banded. Missing skills lower confidence.
          Reading and Listening come from answer keys. Writing and Speaking are practice estimates with quoted
          evidence — not official IELTS scores.
        </p>
      </div>
      {thin ? (
        <EmptyState
          title="Trends appear after two scored attempts"
          body="Finish another skill attempt and this chart will compare them."
        >
          <div className="btn-row">
            <Button href="/app/listening">Listen</Button>
            <Button href="/app/reading" variant="secondary">
              Read
            </Button>
          </div>
        </EmptyState>
      ) : (
        <div className="card">
          <div className="score-number">{progress?.overall_estimate?.toFixed(1) ?? progress?.latest_overall?.toFixed(1) ?? "—"}</div>
          <p className="muted">
            Overall estimate · target {progress?.target_band?.toFixed(1) ?? "not set"}
            {progress?.overall_confidence != null
              ? ` · confidence ${(progress.overall_confidence * 100).toFixed(0)}%`
              : ""}
          </p>
          {(progress?.missing_skills || []).length > 0 && (
            <p className="muted">Missing: {progress?.missing_skills?.map(skillLabel).join(", ")}</p>
          )}
          <BandTrendChart series={progress?.series || []} />
        </div>
      )}
      <div className="grid-2">
        {(progress?.skills || []).map((skill) => (
          <div className="card" key={skill.skill}>
            <h3>{skillLabel(skill.skill)}</h3>
            <p className="muted">
              Average {skill.average_band?.toFixed(1) ?? "—"} · latest {skill.latest_band?.toFixed(1) ?? "—"} ·{" "}
              {skill.attempt_count} {skill.attempt_count === 1 ? "attempt" : "attempts"}
            </p>
          </div>
        ))}
      </div>
      {typeEntries.length > 0 && (
        <div className="card">
          <h2>Question-type accuracy</h2>
          {typeEntries.map(([qtype, stats]) => (
            <p key={qtype} className="muted">
              <strong>{qtypeLabel(qtype)}</strong>: {stats.correct}/{stats.total} (
              {stats.total ? Math.round((stats.correct / stats.total) * 100) : 0}%)
            </p>
          ))}
        </div>
      )}
      <div className="card section-gap">
        <h2>Study plan</h2>
        {plan.length === 0 ? (
          <p className="muted">Items appear after a completed report.</p>
        ) : (
          plan.map((item) => (
            <div key={item.id}>
              <label className={`plan-check${item.status === "done" ? " is-done" : ""}`}>
                <input type="checkbox" checked={item.status === "done"} onChange={() => toggle(item)} />
                <span>
                  <strong>{item.title}</strong>
                  <span className="muted"> · {item.skill_focus}</span>
                  <p className="muted">{item.detail}</p>
                </span>
              </label>
              {item.drill_prompt && item.status !== "done" && (
                <div className="btn-row" style={{ margin: "0.35rem 0 0.8rem 1.7rem" }}>
                  <Button href={drillHref(item)} variant="secondary" size="sm">
                    Start drill
                  </Button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
