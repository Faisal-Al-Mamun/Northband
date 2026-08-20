"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { EvaluationDetail, RevisionResult } from "@/lib/types";
import { attemptTitle, bandMeaning, criterionShort, drillHref, qtypeLabel, shortDate, skillLabel, stageLabel } from "@/lib/labels";
import { Button, Tab } from "@/components/ui/Button";
import { CriteriaBars, CriteriaRadar } from "@/components/charts/CriteriaCharts";
import { ErrorCard, PageSkeleton } from "@/components/ui/PageHeader";
import { EvidenceText } from "@/components/EvidenceText";
import { ExamPrompt } from "@/components/ExamPrompt";

export default function ResultsPage() {
  const params = usePathnameId();
  const [item, setItem] = useState<EvaluationDetail | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"score" | "feedback" | "language" | "text" | "answers">("score");
  const [elapsed, setElapsed] = useState(0);
  const [revising, setRevising] = useState(false);
  const [revision, setRevision] = useState<RevisionResult | null>(null);
  const [reviewFilter, setReviewFilter] = useState<"all" | "missed" | "correct">("all");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const data = await api.getEvaluation(params);
        if (!active) return;
        setItem(data);
        const pending = data.status === "queued" || data.status === "running";
        if (pending) window.setTimeout(load, 1500);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Could not load result");
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [params]);

  useEffect(() => {
    if (!item || (item.status !== "queued" && item.status !== "running")) return;
    const id = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(id);
  }, [item]);

  const quotes = useMemo(() => collectQuotes(item), [item]);
  const integrity = useMemo(() => quoteIntegrity(item), [item]);
  const isObjective = item?.skill === "reading" || item?.skill === "listening";

  if (error) {
    return (
      <ErrorCard message={error}>
        <Button href="/app" variant="secondary">
          Home
        </Button>
      </ErrorCard>
    );
  }
  if (!item) return <PageSkeleton />;

  const waiting = item.status === "queued" || item.status === "running";
  const scores = item.report?.scores;
  const grammar = item.report?.grammar;
  const feedback = item.report?.feedback;
  const tools = item.report?.tools;
  const delta = item.report?.delta;
  const objective = item.report?.objective;
  const again =
    item.skill === "speaking"
      ? "/app/speaking"
      : item.skill === "reading"
        ? "/app/reading"
        : item.skill === "listening"
          ? "/app/listening"
          : "/app/writing";
  const retryHref = item.attempt_id
    ? `${again}?parent=${encodeURIComponent(item.attempt_id)}&prompt=${encodeURIComponent(item.prompt || "")}`
    : again;
  const latestRevision = revision || item.report?.revisions?.at(-1) || null;

  async function onRevise() {
    setRevising(true);
    setError("");
    try {
      const result = await api.reviseEvaluation(params);
      setRevision(result);
      setTab("text");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not rewrite a span");
    } finally {
      setRevising(false);
    }
  }

  return (
    <div className="section-gap">
      <div className="results-hero">
        <div>
          <p className="eyebrow">{attemptTitle(item.skill, item.module, item.task)}</p>
          <div className="score-number lg">{scores?.overall_band?.toFixed(1) ?? "—"}</div>
          {scores ? (
            <p className="muted">
              {objective?.is_drill || scores.overall_band == null
                ? "Drill — marks only, not converted to a paper band"
                : "Practice estimate"}
              {objective?.earned_marks != null
                ? ` · ${objective.earned_marks}/${objective.max_marks ?? 40} marks`
                : ""}
              {item.created_at ? ` · ${shortDate(item.created_at)}` : ""} · not an official IELTS score
              {scores.confidence != null && scores.overall_band != null
                ? ` · confidence ${(scores.confidence * 100).toFixed(0)}%`
                : ""}
              {integrity ? ` · ${integrity.kept}/${integrity.total} evidence quotes kept` : ""}
            </p>
          ) : (
            <p className="muted">{waiting ? stageLabel(item.stage) || "Scoring in progress" : "No band yet"}</p>
          )}
        </div>
      </div>

      {waiting && (
        <div className="card scoring-wait">
          <h2>{stageLabel(item.stage) || "Reading your answer"}</h2>
          <p className="muted">
            {isObjective
              ? "Key marking is instant; explanations may follow for missed items."
              : "Language notes appear first, then criteria and a study list."}{" "}
            {elapsed}s elapsed.
          </p>
          <div className="progress-track" aria-hidden="true">
            <div className="progress-fill" />
          </div>
        </div>
      )}

      {delta?.overall_delta != null && (
        <div className="card">
          <h2>Compared with last time on this prompt</h2>
          <p>
            Overall {delta.previous_overall?.toFixed(1) ?? "—"} → {delta.current_overall?.toFixed(1)} (
            {formatDelta(delta.overall_delta)})
          </p>
        </div>
      )}

      {integrity && !isObjective && (
        <div className="integrity-banner">
          <strong>Evidence is checked against your answer.</strong>
          <span className="muted">
            {integrity.dropped === 0
              ? ` Comments are checked against your answer. All ${integrity.total} quoted spans were found in your text.`
              : ` Comments are checked against your answer. ${integrity.dropped} of ${integrity.total} quoted spans were removed because they were not in your text.`}
            {integrity.hitRate != null ? ` Hit rate ${(integrity.hitRate * 100).toFixed(0)}%.` : ""}
          </span>
        </div>
      )}

      {tools && !isObjective && (
        <div className="tool-strip">
          {tools.word_count != null && (
            <span>
              {tools.word_count} words
              {tools.expected_min_words ? ` · ${tools.expected_min_words}+ expected` : ""}
              {tools.under_length ? " · under length" : ""}
            </span>
          )}
          {tools.linker_count != null && <span>{tools.linker_count} linking phrases</span>}
          {tools.overview_present === false && <span>No overview detected</span>}
          {tools.words_per_minute != null && <span>{Math.round(tools.words_per_minute)} words/min</span>}
          {tools.duration_seconds != null && <span>{Math.round(tools.duration_seconds)}s spoken</span>}
          {tools.pronunciation_is_proxy && <span>Pronunciation is a text proxy</span>}
        </div>
      )}

      {item.status === "failed" && (
        <div className="card section-gap">
          <p className="error">{item.error || "Scoring failed. Try the task again."}</p>
          <div className="btn-row">
            <Button href={again}>Try again</Button>
            <Button href="/app" variant="ghost">
              Home
            </Button>
          </div>
        </div>
      )}

      {(scores || grammar || objective) && (
        <>
          {scores && (
            <div className="trf-grid">
              {scores.criteria.map((row) => (
                <div className="trf-cell" key={row.criterion}>
                  <span>{criterionShort(row.criterion)}</span>
                  <strong>{row.band.toFixed(1)}</strong>
                </div>
              ))}
            </div>
          )}

          <div className="tabs" role="tablist">
            <Tab selected={tab === "score"} onClick={() => setTab("score")}>
              {isObjective ? "Scorecard" : "Criteria"}
            </Tab>
            <Tab selected={tab === "feedback"} onClick={() => setTab("feedback")}>
              Feedback
            </Tab>
            {isObjective ? (
              <Tab selected={tab === "answers"} onClick={() => setTab("answers")}>
                Explanations
              </Tab>
            ) : (
              <Tab selected={tab === "language"} onClick={() => setTab("language")}>
                Language
              </Tab>
            )}
            <Tab selected={tab === "text"} onClick={() => setTab("text")}>
              {isObjective ? "Review" : "Your answer"}
            </Tab>
          </div>

          {tab === "score" && scores && (
            <div className="grid-2">
              {isObjective && objective ? (
                <div className="card section-gap">
                  <h2>{objective.content_title || skillLabel(item.skill)}</h2>
                  <p>
                    Raw score <strong>{objective.earned_marks}/{objective.max_marks}</strong>
                    {objective.is_drill || scores.overall_band == null
                      ? " — drill accuracy only, not a paper band"
                      : ` → band ${scores.overall_band.toFixed(1)}`}
                  </p>
                  {Object.entries(objective.by_type || {}).map(([qtype, stats]) => (
                    <p key={qtype} className="muted">
                      {qtypeLabel(qtype)}: {stats.correct}/{stats.total}
                    </p>
                  ))}
                </div>
              ) : (
                <div className="card">
                  <h2>Criteria map</h2>
                  <CriteriaRadar rows={scores.criteria} />
                </div>
              )}
              <div className="card">
                <h2>{isObjective ? "Band note" : "Band by criterion"}</h2>
                {!isObjective && <CriteriaBars rows={scores.criteria} />}
                <div className="rationale-list">
                  {scores.criteria.map((row) => (
                    <p key={row.criterion} className="muted">
                      <strong>
                        {row.criterion} {row.band.toFixed(1)}
                      </strong>
                      {" — "}
                      {row.rationale}
                    </p>
                  ))}
                </div>
                {scores.overall_band != null && (() => {
                  const note = bandMeaning(item.skill, scores.overall_band);
                  return (
                  <p className="muted">
                    Around band {note.whole}: {note.meaning} Public descriptors are whole bands;
                    your {scores.overall_band.toFixed(1)} sits on that scale as a practice estimate.
                  </p>
                  );
                })()}
              </div>
            </div>
          )}

          {tab === "feedback" && feedback && (
            <div className="card section-gap">
              <p>{feedback.examiner_summary}</p>
              <div className="grid-2">
                <div>
                  <h3>Strengths</h3>
                  {feedback.strengths.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
                <div>
                  <h3>To improve</h3>
                  {feedback.weaknesses.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              </div>
              <h3>Recommended next work</h3>
              {feedback.actions.map((action) => {
                const href = drillHref({
                  drill_prompt: action.drill_prompt,
                  drill_task: action.drill_task,
                  drill_skill: action.drill_skill || item.skill,
                  detail: action.detail,
                });
                return (
                  <div className="plan-item" key={action.title}>
                    <strong>{action.title}</strong>
                    <p className="muted">
                      {action.skill_focus} — {action.detail}
                    </p>
                    <Button href={href} variant="secondary" size="sm">
                      Start this drill
                    </Button>
                  </div>
                );
              })}
            </div>
          )}

          {tab === "score" && scores?.examiner_first_impression && !isObjective && (
            <div className="card">
              <h2>Examiner first impression</h2>
              <p className="muted">{scores.examiner_first_impression}</p>
              {(scores.exam_ceilings || []).length > 0 && (
                <ul>
                  {(scores.exam_ceilings || []).map((line) => (
                    <li key={line} className="muted">
                      {line}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {tab === "answers" && objective && (
            <div className="card section-gap">
              <h2>Missed items</h2>
              {(objective.explanations || []).length === 0 ? (
                <p className="muted">No explanations — either all correct or coach still finishing.</p>
              ) : (
                (objective.explanations || []).map((row) => {
                  const itemRow = objective.per_item?.find((entry) => entry.question_id === row.question_id);
                  return (
                  <div className="issue-card" key={row.question_id}>
                    <strong>
                      Q{itemRow?.number ?? ""} {row.skill_tag || "Tip"}
                      {row.trap_type ? ` · trap: ${row.trap_type.replace(/_/g, " ")}` : ""}
                    </strong>
                    {itemRow?.stem && <p>{itemRow.stem}</p>}
                    {itemRow && (
                      <p className="muted">
                        You answered {displayAnswer(itemRow.given, itemRow.qtype)} · key{" "}
                        {displayAnswer(itemRow.canonical, itemRow.qtype)}
                      </p>
                    )}
                    <p>{row.explanation}</p>
                    {row.tip && <p className="muted">{row.tip}</p>}
                  </div>
                  );
                })
              )}
            </div>
          )}

          {tab === "language" && grammar && (
            <div className="card section-gap">
              <p>{grammar.lexical_range_notes}</p>
              {grammar.issues.map((issue) => (
                <div className="issue-card" key={`${issue.span}-${issue.issue_type}`}>
                  <strong>
                    {issue.issue_type}
                    {issue.cefr_tag ? ` · ${issue.cefr_tag}` : ""}
                  </strong>
                  <p className="quote">
                    “{issue.span}” → {issue.correction}
                  </p>
                  <p className="muted">{issue.explanation}</p>
                </div>
              ))}
            </div>
          )}

          {tab === "text" && (
            <div className="section-gap">
              {item.prompt && (item.skill === "writing" || item.skill === "speaking") && (
                <ExamPrompt
                  skill={item.skill === "speaking" ? "speaking" : "writing"}
                  task={item.task}
                  module={item.module}
                  prompt={item.prompt}
                />
              )}
              <div className="card section-gap">
              {item.prompt && item.skill !== "writing" && item.skill !== "speaking" && (
                <p className="muted">{item.prompt}</p>
              )}
              {isObjective && objective?.transcripts && objective.transcripts.length > 0 && (
                <>
                  <h3>Transcript (unlocked after attempt)</h3>
                  {objective.transcripts.map((row) => (
                    <div key={row.section}>
                      <strong>{row.section}</strong>
                      <p className="answer-block">{row.transcript}</p>
                    </div>
                  ))}
                </>
              )}
              {isObjective && objective?.per_item ? (
                <div className="review-list">
                  <div className="chip-row">
                    <Tab selected={reviewFilter === "all"} onClick={() => setReviewFilter("all")}>
                      All
                    </Tab>
                    <Tab selected={reviewFilter === "missed"} onClick={() => setReviewFilter("missed")}>
                      Missed
                    </Tab>
                    <Tab selected={reviewFilter === "correct"} onClick={() => setReviewFilter("correct")}>
                      Correct
                    </Tab>
                  </div>
                  {objective.per_item
                    .filter((row) => {
                      if (reviewFilter === "missed") return !row.correct;
                      if (reviewFilter === "correct") return Boolean(row.correct);
                      return true;
                    })
                    .map((row) => {
                      const tip = objective.explanations?.find((entry) => entry.question_id === row.question_id);
                      return (
                    <div key={row.question_id} className={`review-row${row.correct ? " is-ok" : " is-miss"}`}>
                      <span className="question-num">{row.number}</span>
                      <div>
                        {row.stem && <p>{row.stem}</p>}
                        <p>
                          You answered <strong>{displayAnswer(row.given, row.qtype)}</strong>
                          {row.correct ? "" : ` · key ${displayAnswer(row.canonical, row.qtype)}`}
                        </p>
                        <p className="muted">{row.qtype ? qtypeLabel(row.qtype) : ""}</p>
                        {tip?.explanation && <p className="muted">{tip.explanation}</p>}
                        {tip?.tip && <p className="muted">{tip.tip}</p>}
                      </div>
                    </div>
                      );
                    })}
                </div>
              ) : (
                <EvidenceText text={item.input_text || item.transcript || ""} quotes={quotes} />
              )}
              {item.skill === "writing" && (
                <Button onClick={onRevise} loading={revising} variant="secondary">
                  Rewrite weakest span (+0.5)
                </Button>
              )}
              {latestRevision && (
                <div className="revision-block">
                  <h3>Suggested rewrite · band {latestRevision.target_band.toFixed(1)}</h3>
                  <p className="muted">{latestRevision.original_span}</p>
                  <p className="answer-block">{latestRevision.rewritten}</p>
                </div>
              )}
              </div>
            </div>
          )}

          {item.report?.agent_trace && !isObjective && (
            <details className="practice-tools">
              <summary>How this score was made</summary>
              <AgentTraceCard trace={item.report.agent_trace} />
            </details>
          )}

          <div className="btn-row">
            <Button href={again}>Next unused paper</Button>
            <Button href={retryHref} variant="secondary">
              Practice this again
            </Button>
            <Button href="/app/progress" variant="ghost">
              See progress
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function usePathnameId() {
  const params = useParams<{ id: string }>();
  return params.id;
}

function formatDelta(value: number) {
  if (value > 0) return `+${value.toFixed(1)}`;
  return value.toFixed(1);
}

function quoteIntegrity(item: EvaluationDetail | null) {
  if (!item?.report) return null;
  const block = (item.report.writing || item.report.speaking) as
    | { quote_hit_rate?: number; evidence_quote_dropped?: number; evidence_quote_kept?: number; evidence_quote_total?: number }
    | undefined;
  if (!block || block.quote_hit_rate == null) return null;
  const total = block.evidence_quote_total ?? (block.evidence_quote_kept || 0) + (block.evidence_quote_dropped || 0);
  return {
    hitRate: block.quote_hit_rate,
    dropped: block.evidence_quote_dropped || 0,
    kept: block.evidence_quote_kept ?? Math.max(0, total - (block.evidence_quote_dropped || 0)),
    total,
  };
}

function AgentTraceCard({ trace }: { trace: NonNullable<EvaluationDetail["report"]>["agent_trace"] }) {
  if (!trace) return null;
  const stages = trace.stages || [];
  const calls = trace.calls || [];
  const skipped = trace.plan?.skipped || [];
  return (
    <div className="card section-gap">
      <p className="muted">{trace.thesis || "Quoted evidence from your answer is used to estimate a band."}</p>
      {skipped.length > 0 && (
        <p className="muted">
          Cost-aware plan skipped {skipped.map((row) => `${row.agent} (${row.reason.replace(/_/g, " ")})`).join(", ")}.
        </p>
      )}
      <ol className="agent-trace">
        {stages.map((stage, index) => (
          <li key={`${stage.name}-${index}`} className="trace-row">
            <span>
              <span className="trace-kind">{stage.kind}</span> {stage.name}
              {stage.reason ? ` · ${stage.reason.replace(/_/g, " ")}` : ""}
              {stage.quote_hit_rate != null ? ` · quote hit ${(stage.quote_hit_rate * 100).toFixed(0)}%` : ""}
            </span>
          </li>
        ))}
      </ol>
      {calls.length > 0 && (
        <div className="trace-calls">
          {calls.map((call, index) => (
            <p key={`${call.agent}-${index}`} className="muted">
              {call.agent} · {call.provider}/{call.model} · {call.latency_ms}ms
              {call.prompt_tokens != null ? ` · ${call.prompt_tokens + (call.completion_tokens || 0)} tokens` : ""}
              {call.success ? "" : " · failed"}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function displayAnswer(given: unknown, qtype?: string) {
  const raw = String(given ?? "").trim();
  if (!raw) return "—";
  const upper = raw.toUpperCase();
  if (qtype === "tfng") {
    if (upper === "A") return "True";
    if (upper === "B") return "False";
    if (upper === "C") return "Not Given";
  }
  if (qtype === "ynng") {
    if (upper === "A") return "Yes";
    if (upper === "B") return "No";
    if (upper === "C") return "Not Given";
  }
  return raw;
}

function collectQuotes(item: EvaluationDetail | null) {
  if (!item?.report) return [];
  const quotes: string[] = [];
  for (const block of [item.report.writing, item.report.speaking]) {
    if (!block) continue;
    for (const value of Object.values(block)) {
      if (value && typeof value === "object" && "evidence" in value) {
        const evidence = (value as { evidence?: { quote?: string }[] }).evidence || [];
        for (const note of evidence) {
          if (note.quote) quotes.push(note.quote);
        }
      }
    }
  }
  for (const issue of item.report.grammar?.issues || []) {
    if (issue.span) quotes.push(issue.span);
  }
  return quotes;
}
