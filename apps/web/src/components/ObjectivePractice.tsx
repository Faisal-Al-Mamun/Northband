"use client";

import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { ContentQuestion, ContentSetDetail, ContentSetSummary, NextSet } from "@/lib/types";
import { formatClock, moduleLabel, qtypeInstruction, qtypeLabel } from "@/lib/labels";
import { Button, Chip } from "@/components/ui/Button";
import { EmptyState, ErrorCard, PageHeader, PageSkeleton } from "@/components/ui/PageHeader";
import { ListeningDesk } from "@/components/ListeningDesk";

type Mode = "exam" | "practice";

function splitChoice(choice: string, index: number) {
  const roman = choice.trim().match(/^(x|ix|iv|v?i{0,3})\s+(.+)$/i);
  if (roman && roman[1] && /[ivx]/i.test(roman[1])) {
    return { letter: roman[1].toLowerCase(), text: roman[2] };
  }
  const match = choice.trim().match(/^([A-Ha-h])(?:[).:\-]|)\s+(.*)$/);
  if (match) return { letter: match[1].toUpperCase(), text: match[2] };
  const lead = choice.trim().match(/^([A-Ha-h])\b(.*)$/);
  if (lead && lead[2]) return { letter: lead[1].toUpperCase(), text: lead[2].trim() };
  return { letter: String.fromCharCode(65 + index), text: choice };
}

function storedAnswer(qtype: string, letter: string, text: string) {
  if (qtype === "tfng" || qtype === "ynng") return text;
  return letter;
}

function isChoiceQuestion(qtype: string, choices: string[]) {
  return (
    choices.length > 0 ||
    ["mcq", "tfng", "ynng", "matching", "matching_headings", "matching_features", "matching_information"].includes(
      qtype,
    )
  );
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function StemText({ stem, blank }: { stem: string; blank?: ReactNode }) {
  const parts = stem.split(/_{2,}/);
  if (parts.length === 1) return <>{stem}</>;
  return (
    <>
      {parts.map((part, index) => (
        <Fragment key={`${part}-${index}`}>
          {part}
          {index < parts.length - 1 &&
            (blank ?? <span className="blank-gap" aria-label="blank" />)}
        </Fragment>
      ))}
    </>
  );
}

function hasInlineBlank(stem: string) {
  return /_{2,}/.test(stem);
}

function wordLimitLabel(limit: number) {
  return `${limit} word${limit === 1 ? "" : "s"} max`;
}

function groupQuestions(questions: ContentQuestion[]) {
  const groups: { qtype: string; start: number; end: number; items: ContentQuestion[] }[] = [];
  for (const question of questions) {
    const last = groups[groups.length - 1];
    if (last && last.qtype === question.qtype) {
      last.items.push(question);
      last.end = question.number;
      continue;
    }
    groups.push({
      qtype: question.qtype,
      start: question.number,
      end: question.number,
      items: [question],
    });
  }
  return groups;
}

function AnswerInput({
  question,
  value,
  onChange,
  locked,
  compact = false,
}: {
  question: ContentQuestion;
  value: string;
  onChange: (next: string) => void;
  locked: boolean;
  compact?: boolean;
}) {
  const choices = question.options?.choices || [];
  if (isChoiceQuestion(question.qtype, choices)) {
    const options =
      choices.length > 0
        ? choices
        : question.qtype === "ynng"
          ? ["Yes", "No", "Not Given"]
          : ["True", "False", "Not Given"];
    return (
      <div className="option-list" role="radiogroup" aria-label={`Question ${question.number}`}>
        {options.map((choice, index) => {
          const { letter, text } = splitChoice(choice, index);
          const stored = storedAnswer(question.qtype, letter, text);
          const selected = value === stored || value === letter || value === choice || value.toLowerCase() === text.toLowerCase();
          const hideLetter = question.qtype === "tfng" || question.qtype === "ynng";
          return (
            <button
              key={`${letter}-${text}`}
              type="button"
              className={`option-row${selected ? " is-on" : ""}`}
              role="radio"
              aria-checked={selected}
              disabled={locked}
              onClick={() => !locked && onChange(stored)}
            >
              {!hideLetter && <span className="option-letter">{letter}</span>}
              <span>{text}</span>
            </button>
          );
        })}
      </div>
    );
  }
  return (
    <input
      className={`answer-field${compact ? " is-blank" : ""}`}
      value={value}
      disabled={locked}
      onChange={(event) => onChange(event.target.value)}
      placeholder={
        compact
          ? ""
          : question.word_limit
            ? `NO MORE THAN ${question.word_limit} WORD${question.word_limit === 1 ? "" : "S"}`
            : "Your answer"
      }
      aria-label={`Answer for question ${question.number}`}
    />
  );
}

function PassageBody({ body }: { body: string }) {
  const [highlights, setHighlights] = useState<string[]>([]);
  const paragraphs = body
    .split(/\n+/)
    .map((part) => part.trim())
    .filter(Boolean);

  function onMouseUp() {
    const selected = window.getSelection()?.toString().replace(/\s+/g, " ").trim() || "";
    if (selected.length < 4 || selected.length > 220) return;
    setHighlights((prev) => (prev.includes(selected) ? prev : [...prev, selected]));
  }

  function renderParagraph(paragraph: string) {
    if (highlights.length === 0) return paragraph;
    const pattern = new RegExp(`(${highlights.map(escapeRegExp).join("|")})`, "gi");
    const parts = paragraph.split(pattern);
    return parts.map((part, index) => {
      const hit = highlights.some((item) => item.toLowerCase() === part.toLowerCase());
      if (!hit) return <Fragment key={`${part}-${index}`}>{part}</Fragment>;
      return (
        <mark
          key={`${part}-${index}`}
          className="passage-mark"
          onClick={(event) => {
            event.stopPropagation();
            setHighlights((prev) => prev.filter((item) => item.toLowerCase() !== part.toLowerCase()));
          }}
        >
          {part}
        </mark>
      );
    });
  }

  return (
    <div className="passage-body" onMouseUp={onMouseUp}>
      <p className="passage-hint muted">Select text to highlight — click a highlight to remove it. Same as computer-delivered IELTS.</p>
      {paragraphs.map((paragraph, index) => (
        <p key={`${index}-${paragraph.slice(0, 32)}`}>
          <span className="para-letter" aria-hidden="true">
            {String.fromCharCode(65 + index)}
          </span>
          {renderParagraph(paragraph)}
        </p>
      ))}
    </div>
  );
}

export function ObjectivePractice({ skill }: { skill: "reading" | "listening" }) {
  const router = useRouter();
  const [module, setModule] = useState<"academic" | "general">("academic");
  const [sets, setSets] = useState<ContentSetSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [nextSet, setNextSet] = useState<NextSet | null>(null);
  const [detail, setDetail] = useState<ContentSetDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [flagged, setFlagged] = useState<Record<string, boolean>>({});
  const [confirmBlanks, setConfirmBlanks] = useState(false);
  const [mode, setMode] = useState<Mode>("exam");
  const [remaining, setRemaining] = useState(0);
  const [running, setRunning] = useState(false);
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const [passageIndex, setPassageIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const mockSessionId =
    typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("mock") : null;
  const submittedRef = useRef(false);

  useEffect(() => {
    api
      .me()
      .then((user) => setModule(user.preferred_module))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    const mockId =
      typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("mock") : null;
    Promise.all([
      api.listContentSets(skill, skill === "listening" ? undefined : module),
      api.nextSet(skill, skill === "listening" ? undefined : module).catch(() => null),
      mockId ? api.getMock(mockId).catch(() => null) : Promise.resolve(null),
    ])
      .then(([rows, assigned, mock]) => {
        const ordered = [...rows].sort((a, b) => {
          const ak = a.kind === "drill" ? 1 : 0;
          const bk = b.kind === "drill" ? 1 : 0;
          if (ak !== bk) return ak - bk;
          return b.question_count - a.question_count;
        });
        setSets(ordered);
        setNextSet(assigned);
        const mockSetId =
          skill === "listening" ? mock?.blueprint?.listening_set_id : mock?.blueprint?.reading_set_id;
        if (mockSetId && ordered.some((item) => item.id === mockSetId)) {
          setSelectedId(mockSetId);
          return;
        }
        if (assigned?.id && ordered.some((item) => item.id === assigned.id)) {
          setSelectedId(assigned.id);
          return;
        }
        if (ordered[0]) setSelectedId(ordered[0].id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load sets"))
      .finally(() => setLoading(false));
  }, [skill, module]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    api
      .getContentSet(selectedId, false)
      .then(async (set) => {
        if (cancelled) return;
        setDetail(set);
        setAnswers({});
        setFlagged({});
        setConfirmBlanks(false);
        setRemaining(set.time_limit_sec);
        setRunning(false);
        setActiveSectionId(set.audio_assets[0]?.id ?? null);
        setPassageIndex(0);
        submittedRef.current = false;
        if (mockSessionId) setMode("exam");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not open set"));
    return () => {
      cancelled = true;
    };
  }, [selectedId, skill]);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => setRemaining((value) => value - 1), 1000);
    return () => window.clearInterval(id);
  }, [running]);

  useEffect(() => {
    if (submittedRef.current || !detail) return;
    if (running && remaining <= 0) {
      submittedRef.current = true;
      setRunning(false);
      void submit(true);
    }
  }, [remaining, running, detail]);

  useEffect(() => {
    if (mode === "exam" && detail) setRunning(true);
  }, [mode, detail?.id]);

  const locked = mode === "exam" && remaining <= 0;
  const groups = useMemo(() => {
    if (!detail) return [];
    const sourceQuestions =
      skill === "reading" && detail.passages.length > 1
        ? detail.questions.filter((question) => question.passage_id === detail.passages[passageIndex]?.id)
        : detail.questions;
    if (skill !== "listening") return groupQuestions(sourceQuestions);
    const bySection: { qtype: string; start: number; end: number; items: ContentQuestion[] }[] = [];
    const assets = [...detail.audio_assets].sort((a, b) => a.order_index - b.order_index);
    for (const asset of assets) {
      const items = detail.questions.filter((question) => question.audio_asset_id === asset.id);
      if (!items.length) continue;
      bySection.push({
        qtype: asset.section_label,
        start: items[0].number,
        end: items[items.length - 1].number,
        items,
      });
    }
    const leftover = detail.questions.filter((question) => !question.audio_asset_id);
    if (leftover.length) {
      bySection.push(...groupQuestions(leftover));
    }
    return bySection.length ? bySection : groupQuestions(detail.questions);
  }, [detail, skill, passageIndex]);

  const progress = useMemo(() => {
    if (!detail) return 0;
    const filled = detail.questions.filter((q) => (answers[q.id] || "").trim()).length;
    return detail.questions.length ? Math.round((filled / detail.questions.length) * 100) : 0;
  }, [answers, detail]);

  const unanswered = useMemo(() => {
    if (!detail) return [];
    return detail.questions.filter((question) => !(answers[question.id] || "").trim());
  }, [answers, detail]);

  function scrollToQuestion(id: string) {
    if (detail) {
      const question = detail.questions.find((item) => item.id === id);
      if (question?.passage_id) {
        const idx = detail.passages.findIndex((passage) => passage.id === question.passage_id);
        if (idx >= 0) setPassageIndex(idx);
      }
    }
    window.setTimeout(() => {
      document.getElementById(`q-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }

  function toggleFlag(id: string) {
    setFlagged((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  async function submit(force = false) {
    if (!detail) return;
    if (!force && unanswered.length > 0) {
      setConfirmBlanks(true);
      scrollToQuestion(unanswered[0].id);
      return;
    }
    setConfirmBlanks(false);
    setPending(true);
    setError("");
    try {
      const body = {
        content_set_id: detail.id,
        module: detail.module === "shared" ? module : detail.module,
        mode,
        answers,
        mock_session_id: mockSessionId || undefined,
      };
      const job =
        skill === "reading" ? await api.createReading(body) : await api.createListening(body);
      if (mockSessionId) {
        try {
          await api.attachMockJob(mockSessionId, skill, job.id);
        } catch {
          /* non-fatal */
        }
      }
      router.push(`/app/results/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
      setPending(false);
    }
  }

  if (loading) return <PageSkeleton />;
  if (error && !detail) {
    return (
      <ErrorCard message={error}>
        <Button href="/app" variant="secondary">
          Home
        </Button>
      </ErrorCard>
    );
  }

  const questionPanel = detail ? (
    <div className="questions-pane">
      <div className="paper-nav" role="navigation" aria-label="Question navigator">
        {detail.questions.map((question) => {
          const filled = Boolean((answers[question.id] || "").trim());
          const isFlagged = Boolean(flagged[question.id]);
          return (
            <button
              key={question.id}
              type="button"
              className={`nav-dot${filled ? " is-filled" : ""}${isFlagged ? " is-flagged" : ""}`}
              onClick={() => scrollToQuestion(question.id)}
              title={`Question ${question.number}${filled ? " · answered" : " · unanswered"}${isFlagged ? " · flagged" : ""}`}
            >
              {question.number}
            </button>
          );
        })}
      </div>
      {confirmBlanks && unanswered.length > 0 && (
        <div className="blank-banner">
          <p>
            {unanswered.length} question{unanswered.length === 1 ? "" : "s"} still blank. In the exam those score zero.
          </p>
          <div className="btn-row">
            <Button size="sm" variant="secondary" onClick={() => scrollToQuestion(unanswered[0].id)}>
              Go to first blank
            </Button>
            <Button size="sm" onClick={() => void submit(true)} loading={pending}>
              Submit anyway
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setConfirmBlanks(false)}>
              Keep answering
            </Button>
          </div>
        </div>
      )}
      {groups.map((group) => (
        <section
          className={`question-group${
            group.items.some((question) => question.audio_asset_id && question.audio_asset_id === activeSectionId)
              ? " is-live"
              : ""
          }`}
          key={`${group.qtype}-${group.start}`}
        >
          <header className="question-group-head">
            <h3>
              {skill === "listening" && /^section/i.test(group.qtype)
                ? `${group.qtype.replace(/section/i, "Section ")} · Questions ${group.start}${group.end !== group.start ? `–${group.end}` : ""}`
                : group.start === group.end
                  ? `Question ${group.start}`
                  : `Questions ${group.start}–${group.end}`}
            </h3>
            <p className="muted">
              {skill === "listening" && /^section/i.test(group.qtype)
                ? "Answer as you listen"
                : qtypeLabel(group.qtype)}
            </p>
          </header>
          {!(skill === "listening" && /^section/i.test(group.qtype)) && (
            <p className="q-instruction">{qtypeInstruction(group.qtype, skill)}</p>
          )}
          {group.items.map((question) => {
            const choices = question.options?.choices || [];
            const isChoice = isChoiceQuestion(question.qtype, choices);
            const stemHasBlank = hasInlineBlank(question.stem);
            const inlineBlank = !isChoice && (stemHasBlank || skill === "listening");
            const field = (
              <AnswerInput
                question={question}
                value={answers[question.id] || ""}
                locked={locked}
                compact={inlineBlank}
                onChange={(next) => setAnswers((prev) => ({ ...prev, [question.id]: next }))}
              />
            );
            return (
            <article key={question.id} id={`q-${question.id}`} className={`question-card${flagged[question.id] ? " is-flagged" : ""}`}>
              <div className={`question-stem${inlineBlank ? " has-blank" : ""}`}>
                <span className="question-num">{question.number}</span>
                <span>
                  <StemText stem={question.stem} blank={stemHasBlank ? field : undefined} />
                  {inlineBlank && !stemHasBlank ? field : null}
                  {question.word_limit && !inlineBlank ? (
                    <span className="word-limit"> ({wordLimitLabel(question.word_limit)})</span>
                  ) : null}
                </span>
                <button
                  type="button"
                  className={`flag-btn${flagged[question.id] ? " is-on" : ""}`}
                  onClick={() => toggleFlag(question.id)}
                  aria-pressed={Boolean(flagged[question.id])}
                >
                  {flagged[question.id] ? "Flagged" : "Flag"}
                </button>
              </div>
              {!inlineBlank && field}
            </article>
            );
          })}
        </section>
      ))}
      {error && <p className="error">{error}</p>}
      <div className="btn-row sticky-actions">
        <Button onClick={submit} loading={pending} disabled={locked && progress === 0}>
          Submit for marking
        </Button>
        <Button href="/app" variant="ghost">
          Cancel
        </Button>
      </div>
    </div>
  ) : null;

  return (
    <div className="section-gap">
      <PageHeader
        eyebrow={skill === "reading" ? "Reading" : "Listening"}
        title={detail?.title || (skill === "reading" ? "Reading" : "Listening")}
        lede={
          skill === "reading"
            ? "Read the passage, then answer the questions. Marks come from the answer key. Explanations appear after you submit."
            : detail
              ? `${detail.audio_assets.length || 4} section${(detail.audio_assets.length || 4) === 1 ? "" : "s"}, ${detail.questions.length} questions. In exam mode each section plays once.`
              : "Four sections, 40 questions. In exam mode each section plays once. Marks come from the answer key."
        }
      />
      {nextSet && nextSet.total > 0 && (
        <p className="muted">
          {nextSet.recycled
            ? "You have sat every published set in this bank — this paper is a re-sit."
            : `${nextSet.completed} set${nextSet.completed === 1 ? "" : "s"} completed · ${nextSet.remaining} unused left. The next unused paper is selected for you.`}
        </p>
      )}

      <div className="chip-row">
        {skill === "reading" && (
          <>
            <Chip selected={module === "academic"} onClick={() => !mockSessionId && setModule("academic")} disabled={Boolean(mockSessionId)}>
              Academic
            </Chip>
            <Chip selected={module === "general"} onClick={() => !mockSessionId && setModule("general")} disabled={Boolean(mockSessionId)}>
              General Training
            </Chip>
          </>
        )}
        <Chip selected={mode === "practice"} onClick={() => !mockSessionId && setMode("practice")} disabled={Boolean(mockSessionId)}>
          Practice
        </Chip>
        <Chip selected={mode === "exam"} onClick={() => setMode("exam")}>
          Exam mode
        </Chip>
      </div>

      {sets.length === 0 ? (
        <EmptyState title="No published sets yet" body="Seed content on the API, then refresh." />
      ) : (
        <div className="set-picker">
          {(["exam", "drill"] as const).map((kind) => {
            const rows = sets.filter((item) => (item.kind === "drill" ? "drill" : "exam") === kind);
            if (!rows.length) return null;
            return (
              <Fragment key={kind}>
                <p className="set-picker-label">{kind === "exam" ? "Exam papers" : "Skill drills"}</p>
                {rows.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`set-chip${selectedId === item.id ? " is-on" : ""}`}
                    onClick={() => !mockSessionId && setSelectedId(item.id)}
                    disabled={Boolean(mockSessionId)}
                  >
                    <strong>{item.title}</strong>
                    <span>
                      {item.question_count} questions · {moduleLabel(item.module)}
                      {kind === "drill" ? " · drill" : ""}
                      {nextSet?.completed_ids.includes(item.id) ? " · sat" : nextSet?.id === item.id ? " · next" : ""}
                    </span>
                  </button>
                ))}
              </Fragment>
            );
          })}
        </div>
      )}

      {detail && (
        <>
          {skill === "reading" && (
          <div className="tool-strip">
            <span className="timer-readout">{formatClock(Math.max(0, remaining))}</span>
            <span>
              {Object.values(answers).filter((value) => value.trim()).length}/{detail.questions.length} answered
              {unanswered.length > 0 ? ` · ${unanswered.length} blank` : ""}
            </span>
            {mode !== "exam" && (
            <Button size="sm" variant="secondary" onClick={() => setRunning((value) => !value)}>
              {running ? "Pause timer" : "Start timer"}
            </Button>
            )}
          </div>
          )}

          {skill === "listening" && (
            <>
              <ListeningDesk
                detail={detail}
                mode={mode}
                remaining={remaining}
                running={running}
                setRunning={setRunning}
                onSectionChange={setActiveSectionId}
              />
              <p className="muted">
                {Object.values(answers).filter((value) => value.trim()).length}/{detail.questions.length} answered
                {unanswered.length > 0 ? ` · ${unanswered.length} blank` : ""}
                {activeSectionId ? " · scroll to the highlighted section as the recording plays" : ""}
              </p>
            </>
          )}

          {skill === "reading" ? (
            <div className="exam-split">
              <aside className="passage-pane">
                {detail.passages.length > 1 && (
                  <div className="chip-row">
                    {detail.passages.map((passage, index) => (
                      <Chip key={passage.id} selected={passageIndex === index} onClick={() => setPassageIndex(index)}>
                        Passage {index + 1}
                      </Chip>
                    ))}
                  </div>
                )}
                {(detail.passages.length > 1 ? [detail.passages[passageIndex]] : detail.passages).map((passage) => (
                  <article key={passage.id}>
                    <p className="eyebrow">Passage {passageIndex + 1}</p>
                    <h2>{passage.title || "Reading passage"}</h2>
                    <PassageBody body={passage.body} />
                  </article>
                ))}
              </aside>
              {questionPanel}
            </div>
          ) : (
            questionPanel
          )}
        </>
      )}
    </div>
  );
}
