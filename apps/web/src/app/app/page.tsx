"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { EvaluationSummary, ProgressSummary, StudyPlanItem, User } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { AttemptRow } from "@/components/ui/AttemptRow";
import { EmptyState, ErrorCard, PageHeader, PageSkeleton } from "@/components/ui/PageHeader";
import { BandGauge } from "@/components/charts/BandGauge";
import { BandTrendChart } from "@/components/charts/BandTrendChart";
import { drillHref, greeting, skillLabel } from "@/lib/labels";

export default function HomePage() {
  const [user, setUser] = useState<User | null>(null);
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [recent, setRecent] = useState<EvaluationSummary[]>([]);
  const [plan, setPlan] = useState<StudyPlanItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.me(), api.progress(), api.listEvaluations(), api.studyPlan()])
      .then(([profile, summary, rows, items]) => {
        setUser(profile);
        setProgress(summary);
        setRecent(rows.slice(0, 5));
        setPlan(items.filter((item) => item.status === "pending").slice(0, 3));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load your studio"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSkeleton />;
  if (error) {
    return (
      <ErrorCard message={error}>
        <Button href="/login" variant="secondary">
          Sign in again
        </Button>
      </ErrorCard>
    );
  }

  const firstRun = !progress?.attempt_count;
  const estimate = progress?.overall_estimate ?? progress?.latest_overall;
  const gap =
    estimate != null && progress?.target_band != null
      ? Math.round((progress.target_band - estimate) * 10) / 10
      : null;

  return (
    <div className="section-gap">
      <PageHeader
        eyebrow="Studio"
        title={greeting(user?.display_name)}
        lede={
            firstRun
            ? "Start with Listening — 40 questions, marked from keys. Then Reading, Writing, and Speaking."
            : gap != null && gap > 0
              ? `${gap.toFixed(1)} away from your target of ${progress?.target_band?.toFixed(1)}. These are practice estimates, not official IELTS scores.`
              : "Pick up where you left off. Charts are AI practice estimates, not official IELTS scores."
        }
        action={
          firstRun ? (
            <Button href="/app/listening">Start with Listening</Button>
          ) : (
            <div className="btn-row">
              <Button href="/app/mock">Full mock</Button>
              <Button href="/app/reading" variant="secondary">
                Reading
              </Button>
            </div>
          )
        }
      />

      {firstRun ? (
        <>
          <EmptyState
            title="Recommended first sit"
            body="Listening is the shortest path to a scorecard. Keys mark the paper. Then try Reading, or a Writing task."
          >
            <div className="btn-row">
              <Button href="/app/listening" size="lg">
                Listening
              </Button>
              <Button href="/app/reading" variant="secondary" size="lg">
                Reading
              </Button>
              <Button href="/app/writing" variant="secondary" size="lg">
                Writing Task 2
              </Button>
            </div>
          </EmptyState>
          <div className="card">
            <h2>How Northband scores</h2>
            <p className="muted">
              Listening and Reading are marked from answer keys. Writing and Speaking get a practice band with quoted
              evidence. Estimates are for practice only.
            </p>
          </div>
        </>
      ) : (
        <div className="stat-row">
          <div className="card stat-card">
            <p className="label">Overall estimate</p>
            <BandGauge latest={estimate ?? null} target={progress?.target_band ?? null} />
            {progress?.overall_confidence != null && (
              <p className="note muted">
                Confidence {(progress.overall_confidence * 100).toFixed(0)}%
                {(progress.missing_skills || []).length
                  ? ` · missing ${(progress.missing_skills || []).map(skillLabel).join(", ")}`
                  : ""}
              </p>
            )}
            {progress?.next_focus && <p className="note muted">Next focus: {progress.next_focus}</p>}
          </div>
          <div className="card stat-card">
            <p className="label">Band over time</p>
            {(progress?.series.length || 0) > 0 ? (
              <BandTrendChart series={progress?.series || []} />
            ) : (
              <p className="muted">Charts appear after you finish an attempt.</p>
            )}
          </div>
          <div className="card stat-card">
            <p className="label">This week</p>
            {plan.length === 0 ? (
              <p className="muted">Your next report will add study items here.</p>
            ) : (
              plan.map((item) => (
                <div className="plan-item" key={item.id}>
                  <strong>{item.title}</strong>
                  <p className="muted">{item.detail}</p>
                  {item.drill_prompt && (
                    <Button href={drillHref(item)} variant="secondary" size="sm">
                      Start drill
                    </Button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {!firstRun && (
        <>
          <div className="grid-2">
            {(progress?.skills || []).map((skill) => (
              <div className="card" key={skill.skill}>
                <h3>{skillLabel(skill.skill)}</h3>
                <p className="muted">
                  Latest {skill.latest_band?.toFixed(1) ?? "—"} · avg {skill.average_band?.toFixed(1) ?? "—"} ·{" "}
                  {skill.attempt_count} attempts
                </p>
              </div>
            ))}
          </div>
          <div className="card">
            <h2>Recent attempts</h2>
            {recent.length === 0 ? (
              <p className="muted">Nothing here yet.</p>
            ) : (
              recent.map((item) => <AttemptRow key={item.id} item={item} />)
            )}
          </div>
        </>
      )}
    </div>
  );
}
