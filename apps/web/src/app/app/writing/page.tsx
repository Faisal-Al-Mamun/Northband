"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { NextPaper } from "@/lib/types";
import { formatClock, recommendedMinutes, wordCount } from "@/lib/labels";
import { formatWritingPrompt } from "@/lib/examPrompt";
import { normalizeTaskVisual, type TaskVisualSpec } from "@/lib/taskVisuals";
import { Button, Chip } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { ExamPrompt } from "@/components/ExamPrompt";

const bank = {
  academic: {
    task1: formatWritingPrompt({
      topic:
        "The chart below shows the percentage of households in owned and rented accommodation in England and Wales between 1918 and 2011.",
      instruction: "Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
    }),
    task2: formatWritingPrompt({
      topic:
        "Some people believe that unpaid community service should be a compulsory part of high school programmes. To what extent do you agree or disagree?",
      instruction:
        "Give reasons for your answer and include any relevant examples from your own knowledge or experience.",
    }),
  },
  general: {
    task1: formatWritingPrompt({
      topic:
        "You recently stayed in a hotel and had several problems with the room and service. Write a letter to the hotel manager.",
      bulletLead: "In your letter:",
      bullets: [
        "describe the problems",
        "explain how they affected your stay",
        "say what you would like the manager to do",
      ],
    }),
    task2: formatWritingPrompt({
      topic:
        "In many countries, people are living longer. What problems does this cause for individuals and society? What measures could be taken to address these problems?",
      instruction:
        "Give reasons for your answer and include any relevant examples from your own knowledge or experience.",
    }),
  },
};

export default function WritingPage() {
  const router = useRouter();
  const [module, setModule] = useState<"academic" | "general">("academic");
  const [task, setTask] = useState<"task1" | "task2">("task2");
  const [fullPaper, setFullPaper] = useState(false);
  const [prompt, setPrompt] = useState(bank.academic.task2);
  const [editingPrompt, setEditingPrompt] = useState(false);
  const [essay, setEssay] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [running, setRunning] = useState(false);
  const [remaining, setRemaining] = useState(recommendedMinutes("writing", "task2") * 60);
  const [spellcheck, setSpellcheck] = useState(false);
  const [parentId, setParentId] = useState<string | undefined>();
  const [studyItemId, setStudyItemId] = useState<string | undefined>();
  const [mockSessionId, setMockSessionId] = useState<string | null>(null);
  const [mockTask2, setMockTask2] = useState<string>("");
  const [bankItemId, setBankItemId] = useState<string | undefined>();
  const [paperMeta, setPaperMeta] = useState<NextPaper | null>(null);
  const [paperVisual, setPaperVisual] = useState<TaskVisualSpec | null>(null);
  const promptLocked = useRef(false);
  const submittedRef = useRef(false);
  const paperSeq = useRef(0);
  const keepClockRef = useRef(false);
  const target = task === "task1" ? 150 : 250;
  const words = wordCount(essay);
  const minutes = recommendedMinutes("writing", fullPaper ? "full" : task);

  function applyPaper(paper: NextPaper, nextModule: "academic" | "general", nextTask: "task1" | "task2") {
    setPrompt(paper.prompt || bank[nextModule][nextTask]);
    setBankItemId(paper.id || undefined);
    setPaperMeta(paper);
    setPaperVisual(normalizeTaskVisual(paper.visual));
    setEditingPrompt(false);
  }

  async function loadPaper(nextModule: "academic" | "general", nextTask: "task1" | "task2", excludeId?: string) {
    const seq = ++paperSeq.current;
    try {
      const paper = await api.nextPrompt("writing", nextTask, nextModule, excludeId);
      if (seq !== paperSeq.current) return;
      if (paper.task && paper.task !== nextTask) {
        /* requested Task 1 must never render a Task 2 essay */
      } else if (paper.prompt) {
        applyPaper(paper, nextModule, nextTask);
        return;
      }
    } catch {
      /* fall back to the static starter */
    }
    if (seq !== paperSeq.current) return;
    setPrompt(bank[nextModule][nextTask]);
    setBankItemId(undefined);
    setPaperMeta(null);
    setPaperVisual(null);
  }

  function chooseModule(next: "academic" | "general") {
    if (mockSessionId) return;
    promptLocked.current = false;
    setModule(next);
    void loadPaper(next, fullPaper ? "task1" : task);
  }

  function chooseTask(next: "task1" | "task2") {
    if (mockSessionId) return;
    promptLocked.current = false;
    setFullPaper(false);
    setTask(next);
    void loadPaper(module, next);
  }

  function chooseFullPaper() {
    if (mockSessionId) return;
    promptLocked.current = false;
    setFullPaper(true);
    setTask("task1");
    setEssay("");
    setRemaining(recommendedMinutes("writing", "full") * 60);
    void loadPaper(module, "task1");
  }

  useEffect(() => {
    api
      .me()
      .then((user) => setModule(user.preferred_module))
      .catch(() => undefined);
    const params = new URLSearchParams(window.location.search);
    const queryPrompt = params.get("prompt");
    const queryTask = params.get("task");
    const queryParent = params.get("parent");
    const queryItem = params.get("item");
    const queryMock = params.get("mock");
    const initialTask = queryTask === "task1" || queryTask === "task2" ? queryTask : "task2";
    if (queryTask === "task1" || queryTask === "task2") setTask(queryTask);
    if (queryPrompt) {
      setPrompt(queryPrompt);
      promptLocked.current = true;
      setEditingPrompt(false);
    }
    if (queryParent) setParentId(queryParent);
    if (queryItem) setStudyItemId(queryItem);
    if (queryMock) {
      setMockSessionId(queryMock);
      api
        .getMock(queryMock)
        .then((session) => {
          setModule(session.module === "general" ? "general" : "academic");
          setMockTask2(session.blueprint?.writing_task2_prompt || "");
          const doneTask1 = Boolean(session.job_ids?.writing_task1);
          const t2 = session.blueprint?.writing_task2_prompt;
          const t1 = session.blueprint?.writing_task1_prompt;
          if (doneTask1 && t2 && !queryPrompt) {
            setTask("task2");
            setPrompt(t2);
            promptLocked.current = true;
            setRemaining(recommendedMinutes("writing", "task2") * 60);
            setRunning(true);
            return;
          }
          if (t1 && !queryPrompt) {
            setTask("task1");
            setPrompt(t1);
            promptLocked.current = true;
            setRemaining(recommendedMinutes("writing", "task1") * 60);
            setRunning(true);
          }
        })
        .catch(() => undefined);
      return;
    }
    if (!queryPrompt) {
      api
        .me()
        .then((user) => {
          const nextModule = user.preferred_module;
          setModule(nextModule);
          return loadPaper(nextModule, initialTask);
        })
        .catch(() => loadPaper("academic", initialTask));
    }
  }, []);

  useEffect(() => {
    if (promptLocked.current) return;
    if (keepClockRef.current) {
      keepClockRef.current = false;
      return;
    }
    setRemaining(recommendedMinutes("writing", fullPaper ? "full" : task) * 60);
    setRunning(false);
  }, [module, task, fullPaper]);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => setRemaining((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(id);
  }, [running]);

  useEffect(() => {
    if (submittedRef.current || pending) return;
    if (running && remaining <= 0 && words >= 20) {
      submittedRef.current = true;
      setRunning(false);
      void submit();
    }
  }, [remaining, running, pending, words]);

  useEffect(() => {
    const dirty = essay.trim().length > 0;
    if (!dirty) return;
    const onLeave = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onLeave);
    return () => window.removeEventListener("beforeunload", onLeave);
  }, [essay]);

  async function submit() {
    setPending(true);
    setError("");
    try {
      const job = await api.createWriting({
        module,
        task,
        prompt,
        essay,
        parent_attempt_id: parentId,
        study_item_id: studyItemId,
        bank_item_id: bankItemId,
      });
      if (mockSessionId) {
        const attachAs = task === "task1" ? "writing_task1" : "writing";
        try {
          await api.attachMockJob(mockSessionId, attachAs, job.id);
        } catch {
          /* non-fatal */
        }
        if (task === "task1") {
          const next = mockTask2 || bank[module].task2;
          setEssay("");
          setTask("task2");
          setPrompt(next);
          promptLocked.current = true;
          setRemaining(recommendedMinutes("writing", "task2") * 60);
          setRunning(true);
          submittedRef.current = false;
          window.history.replaceState(null, "", `/app/writing?mock=${mockSessionId}&task=task2`);
          return;
        }
      }
      if (fullPaper && task === "task1") {
        keepClockRef.current = true;
        promptLocked.current = false;
        setEssay("");
        setTask("task2");
        setPaperMeta(null);
        setPaperVisual(null);
        submittedRef.current = false;
        void loadPaper(module, "task2");
        return;
      }
      router.push(`/app/results/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start evaluation");
    } finally {
      setPending(false);
    }
  }

  const showChart = module === "academic" && task === "task1";

  return (
    <div>
      <PageHeader
        eyebrow="Writing"
        title={
          fullPaper
            ? `Full paper · ${task === "task1" ? "Task 1" : "Task 2"}${paperMeta?.title ? ` · ${paperMeta.title}` : ""}`
            : paperMeta?.title
              ? `${task === "task1" ? "Task 1" : "Task 2"} · ${paperMeta.title}`
              : task === "task1"
                ? "Task 1"
                : "Task 2"
        }
        lede={`${module === "academic" ? "Academic" : "General Training"} · write at least ${target} words · ${fullPaper ? "60 minutes for both tasks" : `${minutes} minutes`}. ${mockSessionId ? (task === "task1" ? "Task 2 follows this paper." : "Last writing task of the mock.") : fullPaper ? (task === "task1" ? "Task 2 uses the remaining time after you hand this in." : "Last task of this paper.") : paperMeta ? `${paperMeta.completed} done · ${paperMeta.remaining} new papers left in this bank.` : "Practice estimate — not an official IELTS score."}`}
      />

      <div className="studio-bar">
        {!mockSessionId && (
        <div className="section-gap">
          <div>
            <p className="field-label">Module</p>
            <div className="chip-row">
              <Chip selected={module === "academic"} onClick={() => chooseModule("academic")}>
                Academic
              </Chip>
              <Chip selected={module === "general"} onClick={() => chooseModule("general")}>
                General Training
              </Chip>
            </div>
          </div>
          <div>
            <p className="field-label">Task</p>
            <div className="chip-row">
              <Chip selected={!fullPaper && task === "task1"} onClick={() => chooseTask("task1")}>
                Task 1
              </Chip>
              <Chip selected={!fullPaper && task === "task2"} onClick={() => chooseTask("task2")}>
                Task 2
              </Chip>
              <Chip selected={fullPaper} onClick={chooseFullPaper}>
                Full paper
              </Chip>
            </div>
          </div>
        </div>
        )}
        <div className={`timer${remaining <= 0 ? " is-over" : ""}`}>
          <span className="timer-readout">{formatClock(Math.max(0, remaining))}</span>
          {!mockSessionId && (
          <div className="btn-row">
            <Button variant="ghost" size="sm" onClick={() => setRunning((value) => !value)}>
              {running ? "Pause" : remaining === minutes * 60 ? "Start timer" : "Resume"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                promptLocked.current = false;
                void loadPaper(module, task, bankItemId);
              }}
            >
              Next unused paper
            </Button>
          </div>
          )}
        </div>
      </div>

      <div className={showChart ? "exam-stack" : "studio-grid"}>
        <ExamPrompt
          skill="writing"
          task={task}
          module={module}
          prompt={prompt}
          visual={paperVisual}
          editing={editingPrompt}
          onChange={mockSessionId ? undefined : setPrompt}
          onToggleEdit={mockSessionId ? undefined : () => setEditingPrompt((value) => !value)}
        />
        <div className="card section-gap">
          <label>
            Your answer
            <textarea
              className="exam-editor"
              value={essay}
              onChange={(event) => setEssay(event.target.value)}
              placeholder={
                task === "task1" && module === "general"
                  ? "Write your letter here."
                  : "Write your answer here."
              }
              maxLength={8000}
              spellCheck={spellcheck && !mockSessionId}
              autoCorrect={spellcheck && !mockSessionId ? "on" : "off"}
              autoCapitalize={spellcheck && !mockSessionId ? "sentences" : "off"}
              autoComplete="off"
            />
          </label>
          <div className="word-meter">
            <span className="helper">
              <strong className={words >= target ? "ok" : words > 0 ? "warn" : ""}>{words}</strong> words · {target}+
              expected
            </span>
            <Button onClick={submit} loading={pending} disabled={words < 20}>
              {mockSessionId && task === "task1"
                ? "Hand in Task 1"
                : fullPaper && task === "task1"
                  ? "Hand in Task 1"
                  : "Submit for scoring"}
            </Button>
          </div>
          {words > 0 && words < target && (
            <p className="muted">The exam expects at least {target} words. You can still submit, but the Task score may be limited.</p>
          )}
          {!mockSessionId && (
            <label className="spell-toggle">
              <input
                type="checkbox"
                checked={spellcheck}
                onChange={(event) => setSpellcheck(event.target.checked)}
              />
              Allow spellcheck (computer-delivered IELTS does not)
            </label>
          )}
          {remaining <= 0 && words < 20 && (
            <p className="error">Time is up. Add a little more text (20+ words) to submit this paper.</p>
          )}
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    </div>
  );
}
