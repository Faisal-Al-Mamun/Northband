"use client";

import { TaskVisual } from "@/components/TaskVisual";
import { parseExamPrompt } from "@/lib/examPrompt";
import { normalizeTaskVisual, type TaskVisualSpec } from "@/lib/taskVisuals";
import { Button } from "@/components/ui/Button";

export function ExamPrompt({
  skill,
  task,
  module,
  prompt,
  editing = false,
  onChange,
  onToggleEdit,
  editLabel = "Use a different question",
  compact = false,
  activeQuestion,
  examiner,
  visual,
}: {
  skill: "writing" | "speaking";
  task: string;
  module: string;
  prompt: string;
  editing?: boolean;
  onChange?: (value: string) => void;
  onToggleEdit?: () => void;
  editLabel?: string;
  compact?: boolean;
  activeQuestion?: number;
  examiner?: string;
  visual?: TaskVisualSpec | null;
}) {
  const parsed = parseExamPrompt(prompt, { skill, task, module });
  const chart = normalizeTaskVisual(visual) || parsed.visual;
  const interview = skill === "speaking" && (task === "part1" || task === "part3");
  const cueCard = skill === "speaking" && task === "part2";
  const heading = cueCard
    ? "Cue card"
    : task === "part1"
      ? "Part 1 — Interview"
      : task === "part3"
        ? "Part 3 — Discussion"
        : "Question";

  return (
    <aside className={`exam-paper${compact ? " is-compact" : ""}${cueCard ? " cue-card" : ""}`}>
      <div className="exam-paper-head">
        <h2>{heading}</h2>
        {parsed.minutes != null && (
          <p className="exam-kicker">You should spend about {parsed.minutes} minutes on this task.</p>
        )}
      </div>

      {examiner && <p className="examiner-line">{examiner}</p>}

      {editing && onChange ? (
        <textarea className="prompt-edit" value={prompt} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <div className="exam-question">
          {skill === "writing" && task === "task2" && <p className="exam-kicker">Write about the following topic:</p>}
          {parsed.topic && <p className="prompt-body">{parsed.topic}</p>}
          {chart && <TaskVisual spec={chart} />}
          {parsed.instruction && <p className="exam-instruction">{parsed.instruction}</p>}
          {parsed.bullets.length > 0 && (
            <>
              {parsed.bulletLead && <p className="exam-kicker">{parsed.bulletLead}</p>}
              {interview ? (
                <ol className="exam-questions">
                  {parsed.bullets.map((item, index) => (
                    <li key={item} className={index === activeQuestion ? "is-current" : undefined}>
                      {item}
                    </li>
                  ))}
                </ol>
              ) : (
                <ul className="cue-list">
                  {parsed.bullets.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
            </>
          )}
          {parsed.minWords != null && (
            <p className="exam-foot">Write at least {parsed.minWords} words.</p>
          )}
        </div>
      )}

      {onToggleEdit && (
        <div className="btn-row" style={{ marginTop: "0.9rem" }}>
          <Button variant="ghost" size="sm" onClick={onToggleEdit}>
            {editing ? "Done" : editLabel}
          </Button>
        </div>
      )}
    </aside>
  );
}
