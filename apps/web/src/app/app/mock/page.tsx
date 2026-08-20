"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MockBlueprint, MockSession } from "@/lib/types";
import { moduleLabel, skillLabel, statusLabel } from "@/lib/labels";
import { Button, Chip } from "@/components/ui/Button";
import { ErrorCard, PageHeader, PageSkeleton } from "@/components/ui/PageHeader";

const ORDER = ["listening", "reading", "writing", "speaking"] as const;

export default function MockPage() {
  const [module, setModule] = useState<"academic" | "general">("academic");
  const [blueprints, setBlueprints] = useState<MockBlueprint[]>([]);
  const [session, setSession] = useState<MockSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .me()
      .then((profile) => {
        setModule(profile.preferred_module);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api
      .listMockBlueprints(module)
      .then(setBlueprints)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load blueprints"));
  }, [module]);

  async function start(blueprintId?: string) {
    setPending(true);
    setError("");
    try {
      const next = await api.startMock({ module, blueprint_id: blueprintId });
      setSession(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start mock");
    } finally {
      setPending(false);
    }
  }

  async function refresh() {
    if (!session) return;
    const next = await api.refreshMock(session.id);
    setSession(next);
  }

  if (loading) return <PageSkeleton />;
  if (error && !blueprints.length) {
    return (
      <ErrorCard message={error}>
        <Button href="/app">Home</Button>
      </ErrorCard>
    );
  }

  const current = session?.current_skill || "listening";
  const currentIndex = ORDER.indexOf(current as (typeof ORDER)[number]);
  const hrefFor = (skill: string) => {
    if (!session) return "/app";
    if (skill === "listening") return `/app/listening?mock=${session.id}`;
    if (skill === "reading") return `/app/reading?mock=${session.id}`;
    if (skill === "writing") return `/app/writing?mock=${session.id}`;
    return `/app/speaking?mock=${session.id}`;
  };
  const skillComplete = (skill: string) => {
    if (!session) return false;
    if (skill === "writing") return Boolean(session.job_ids?.writing);
    return Boolean(session.job_ids?.[skill]);
  };

  return (
    <div className="section-gap">
      <PageHeader
        eyebrow="Full mock"
        title="Four-skill mock"
        lede="Sit the papers in order: Listening, Reading, Writing (Task 1 then Task 2), then Speaking. Writing overall weights Task 1 as one third and Task 2 as two thirds, then half-bands. Overall is the mean of the four skills, rounded to the nearest 0.5. Practice estimate only."
      />

      {!session && (
      <div className="chip-row">
        <Chip selected={module === "academic"} onClick={() => setModule("academic")}>
          Academic
        </Chip>
        <Chip selected={module === "general"} onClick={() => setModule("general")}>
          General Training
        </Chip>
      </div>
      )}

      {!session ? (
        <div className="card section-gap">
          <h2>Choose a blueprint</h2>
          <p className="muted">
            After you finish a mock, the next unused paper is offered first. Writing and speaking prompts rotate from
            the bank; Listening and Reading stay on published sets with answer keys.
          </p>
          <Button onClick={() => start()} loading={pending}>
            Start next unused mock
          </Button>
          {blueprints.length === 0 ? (
            <p className="muted">No published blueprints for {moduleLabel(module)}.</p>
          ) : (
            blueprints.map((bp) => (
              <div className="plan-item" key={bp.id}>
                <strong>{bp.title}</strong>
                <p className="muted">{moduleLabel(bp.module)}</p>
                <Button onClick={() => start(bp.id)} loading={pending} variant="secondary">
                  Start this mock
                </Button>
              </div>
            ))
          )}
          {error && <p className="error">{error}</p>}
        </div>
      ) : (
        <div className="section-gap">
          <div className="card">
            <h2>{session.blueprint?.title || "Mock in progress"}</h2>
            <p className="muted">
              Status: {statusLabel(session.status)} · current: {current === "done" ? "Complete" : skillLabel(current)}
            </p>
            {session.overall_band != null && (
              <p>
                Overall estimate <strong>{session.overall_band.toFixed(1)}</strong>
                {session.confidence != null
                  ? ` · confidence ${(session.confidence * 100).toFixed(0)}%`
                  : ""}
              </p>
            )}
            <div className="btn-row">
              <Button onClick={refresh} variant="secondary">
                Refresh scores
              </Button>
              <Button href="/app" variant="ghost">
                Home
              </Button>
            </div>
          </div>
          <div className="grid-2">
            {ORDER.map((skill) => {
              const band = session.skill_bands?.[skill];
              const jobId = skill === "writing" ? session.job_ids?.writing || session.job_ids?.writing_task1 : session.job_ids?.[skill];
              const index = ORDER.indexOf(skill);
              const isCurrent = current === skill;
              const locked = current !== "done" && (currentIndex < 0 || index > currentIndex);
              const done = skillComplete(skill);
              return (
                <div className="card" key={skill}>
                  <h3>{skillLabel(skill)}</h3>
                  <p className="muted">
                    {band != null ? `Band ${Number(band).toFixed(1)}` : done ? "Submitted" : "Not completed"}
                    {isCurrent ? " · up next" : locked ? " · sit the earlier papers first" : ""}
                    {skill === "writing" && session.job_ids?.writing_task1 && !session.job_ids?.writing
                      ? " · Task 2 remaining (Task 2 is two-thirds of the Writing band)"
                      : skill === "writing" && session.job_ids?.writing
                        ? " · Task 1 is 1/3, Task 2 is 2/3"
                        : ""}
                  </p>
                  <div className="btn-row">
                    <Button
                      href={locked ? undefined : hrefFor(skill)}
                      variant={isCurrent ? "primary" : "secondary"}
                      size="sm"
                      disabled={locked}
                    >
                      {done && !isCurrent ? "Review paper" : isCurrent ? "Start" : "Open"}
                    </Button>
                    {jobId && (
                      <Button href={`/app/results/${jobId}`} variant="ghost" size="sm">
                        Results
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
