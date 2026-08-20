"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { formatClock } from "@/lib/labels";
import { Button, Chip, RecordButton } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { ExamPrompt } from "@/components/ExamPrompt";
import {
  SPEAKING_SETS,
  SPEAK_LIMITS,
  examinerLine,
  packFromCues,
  formatFullSpeakingPrompt,
  formatSpeakingPrompt,
  speakingQuestions,
  type SpeakingPart,
  type SpeakingSet,
} from "@/lib/speakingBank";
import type { NextPaper } from "@/lib/types";

type Mode = "exam" | "upload" | "transcript";
type Phase = "intro" | "prep" | "speak" | "done";

const PART_COPY: Record<SpeakingPart, { title: string; lede: string }> = {
  part1: { title: "Part 1 — Interview", lede: "Familiar topics. About 4–5 minutes." },
  part2: { title: "Part 2 — Long turn", lede: "One minute to prepare, then speak for 1–2 minutes." },
  part3: { title: "Part 3 — Discussion", lede: "Abstract questions. About 4–5 minutes." },
};

function pickMime(): string {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return types.find((type) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) || "";
}

export default function SpeakingPage() {
  const router = useRouter();
  const [module, setModule] = useState<"academic" | "general">("academic");
  const [task, setTask] = useState<SpeakingPart>("part1");
  const [fullTest, setFullTest] = useState(true);
  const [pack, setPack] = useState<SpeakingSet>(SPEAKING_SETS[0]);
  const [prompt, setPrompt] = useState(formatSpeakingPrompt("part1", SPEAKING_SETS[0]));
  const [bankItemId, setBankItemId] = useState<string | undefined>();
  const [paperMeta, setPaperMeta] = useState<NextPaper | null>(null);
  const [customPrompt, setCustomPrompt] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState(false);
  const [mode, setMode] = useState<Mode>("exam");
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [stageOffset, setStageOffset] = useState(0);
  const [prepLeft, setPrepLeft] = useState(60);
  const [phase, setPhase] = useState<Phase>("intro");
  const [qIndex, setQIndex] = useState(0);
  const [parentId, setParentId] = useState<string | undefined>();
  const [mockSessionId, setMockSessionId] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const starting = useRef(false);
  const questions = speakingQuestions(task, pack);
  const speakLimit = SPEAK_LIMITS[task];
  const stageElapsed = Math.max(0, elapsed - stageOffset);
  const remaining = (() => {
    if (task === "part2" && phase === "prep") return prepLeft;
    if (recording) return Math.max(0, speakLimit - stageElapsed);
    return speakLimit;
  })();

  useEffect(() => {
    api
      .me()
      .then((user) => setModule(user.preferred_module))
      .catch(() => undefined);
    const params = new URLSearchParams(window.location.search);
    const queryPrompt = params.get("prompt");
    const queryTask = params.get("task");
    const queryParent = params.get("parent");
    const queryMock = params.get("mock");
    if (queryMock) {
      setMockSessionId(queryMock);
      setFullTest(true);
      setTask("part1");
      api
        .getMock(queryMock)
        .then((session) => {
          const next = packFromCues(session.blueprint?.speaking_cues, SPEAKING_SETS[0]);
          setPack(next);
          if (!queryPrompt) setPrompt(formatSpeakingPrompt("part1", next));
        })
        .catch(() => {
          if (!queryPrompt) setPrompt(formatSpeakingPrompt("part1", SPEAKING_SETS[0]));
        });
    }
    if (queryTask === "part1" || queryTask === "part2" || queryTask === "part3") {
      setFullTest(false);
      setTask(queryTask);
      if (!queryPrompt) setPrompt(formatSpeakingPrompt(queryTask, SPEAKING_SETS[0]));
    }
    if (queryPrompt) {
      setPrompt(queryPrompt);
      setCustomPrompt(true);
      setEditingPrompt(false);
    }
    if (queryParent) setParentId(queryParent);
    if (!queryPrompt && !queryMock) {
      void loadPack(queryTask === "part1" || queryTask === "part2" || queryTask === "part3" ? queryTask : "full");
    }
  }, []);

  useEffect(() => {
    if (!audioBlob) {
      setAudioUrl(null);
      return;
    }
    const url = URL.createObjectURL(audioBlob);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [audioBlob]);

  useEffect(() => {
    if (!recording) return;
    const id = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(id);
  }, [recording]);

  useEffect(() => {
    if (task !== "part2" || phase !== "prep" || prepLeft <= 0) return;
    const id = window.setInterval(() => setPrepLeft((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(id);
  }, [task, phase, prepLeft]);

  useEffect(() => {
    if (task !== "part2" || phase !== "prep" || prepLeft > 0) return;
    if (fullTest && recording) {
      setPhase("speak");
      setStageOffset(elapsed);
      return;
    }
    if (recording || audioBlob) return;
    void beginRecording();
  }, [prepLeft, phase, task, recording, audioBlob, fullTest, elapsed]);

  useEffect(() => {
    if (!recording) return;
    if (phase === "prep") return;
    if (stageElapsed < speakLimit) return;
    if (fullTest && task !== "part3") {
      continueInterview();
      return;
    }
    recorder.current?.stop();
    setRecording(false);
    setPhase("done");
  }, [stageElapsed, recording, speakLimit, fullTest, task, phase]);

  function resetAttempt() {
    recorder.current?.stop();
    setRecording(false);
    setAudioBlob(null);
    setFile(null);
    setElapsed(0);
    setStageOffset(0);
    setPrepLeft(60);
    setPhase("intro");
    setQIndex(0);
    setNotes("");
    setError("");
    starting.current = false;
  }

  function applyPack(next: SpeakingSet, nextTask: SpeakingPart | "full", paper?: NextPaper | null) {
    setPack(next);
    setPaperMeta(paper || null);
    setBankItemId(paper?.id || undefined);
    if (!customPrompt) {
      setPrompt(nextTask === "full" || fullTest ? formatSpeakingPrompt("part1", next) : formatSpeakingPrompt(nextTask, next));
    }
  }

  async function loadPack(nextTask: SpeakingPart | "full", excludeId?: string) {
    try {
      const paper = await api.nextPrompt("speaking", nextTask === "full" ? "full" : nextTask, module, excludeId);
      if (paper.speaking) {
        const nextPack: SpeakingSet = {
          id: paper.speaking.id,
          title: paper.speaking.title,
          part1: paper.speaking.part1,
          part2: paper.speaking.part2,
          part3: paper.speaking.part3,
        };
        applyPack(nextPack, nextTask, paper);
        return;
      }
    } catch {
      /* local fallback */
    }
    const fallback = SPEAKING_SETS.find((item) => item.id !== excludeId) || SPEAKING_SETS[0];
    applyPack(fallback, nextTask, null);
  }

  function setPart(next: SpeakingPart) {
    if (mockSessionId) return;
    setFullTest(false);
    setTask(next);
    if (!customPrompt) setPrompt(formatSpeakingPrompt(next, pack));
    setEditingPrompt(false);
    resetAttempt();
  }

  function chooseFullTest() {
    if (mockSessionId && fullTest) return;
    setFullTest(true);
    setTask("part1");
    if (!customPrompt) setPrompt(formatSpeakingPrompt("part1", pack));
    setEditingPrompt(false);
    resetAttempt();
  }

  function nextTopic() {
    setCustomPrompt(false);
    setEditingPrompt(false);
    resetAttempt();
    void loadPack(fullTest ? "full" : task, bankItemId);
  }

  async function beginRecording() {
    if (starting.current || audioBlob) return;
    if (recorder.current && recorder.current.state === "recording") {
      setPhase("speak");
      starting.current = false;
      return;
    }
    if (recording) return;
    starting.current = true;
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = pickMime();
      const media = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      chunks.current = [];
      media.ondataavailable = (event) => {
        if (event.data.size) chunks.current.push(event.data);
      };
      media.onstop = () => {
        setAudioBlob(new Blob(chunks.current, { type: media.mimeType || "audio/webm" }));
        stream.getTracks().forEach((track) => track.stop());
        setPhase("done");
        starting.current = false;
      };
      recorder.current = media;
      media.start(1000);
      setElapsed(0);
      setStageOffset(0);
      setRecording(true);
      setPhase("speak");
      starting.current = false;
    } catch {
      starting.current = false;
      setPhase("speak");
      setError("Microphone access was denied. Use practice options to upload a file or paste a transcript.");
    }
  }

  function stopRecording() {
    recorder.current?.stop();
    setRecording(false);
  }

  function continueInterview() {
    if (task === "part1") {
      setTask("part2");
      setPhase("prep");
      setPrepLeft(60);
      setQIndex(0);
      setStageOffset(elapsed);
      if (!customPrompt) setPrompt(formatSpeakingPrompt("part2", pack));
      return;
    }
    if (task === "part2") {
      setTask("part3");
      setPhase("speak");
      setQIndex(0);
      setStageOffset(elapsed);
      if (!customPrompt) setPrompt(formatSpeakingPrompt("part3", pack));
    }
  }

  function toggleRecord() {
    if (recording) {
      if (fullTest && task !== "part3") {
        continueInterview();
        return;
      }
      stopRecording();
      return;
    }
    if (task === "part2" && phase === "intro" && !fullTest) {
      setPhase("prep");
      setPrepLeft(60);
      return;
    }
    void beginRecording();
  }

  function canSubmit() {
    if (mode === "exam") return Boolean(audioBlob);
    if (mode === "upload") return Boolean(file?.size);
    return transcript.trim().length > 8;
  }

  async function submit() {
    if (file && file.size > 15 * 1024 * 1024) {
      setError("Audio must be 15 MB or smaller.");
      return;
    }
    const form = new FormData();
    form.set("module", module);
    form.set("task", fullTest ? "full" : task);
    form.set("prompt", fullTest && !customPrompt ? formatFullSpeakingPrompt(pack) : prompt);
    if (parentId) form.set("parent_attempt_id", parentId);
    if (bankItemId) form.set("bank_item_id", bankItemId);
    if (mode === "transcript") form.set("transcript", transcript.trim());
    if (mode === "exam" && audioBlob) form.set("audio", audioBlob, "recording.webm");
    if (mode === "upload" && file) form.set("audio", file);
    setPending(true);
    setError("");
    try {
      const job = await api.createSpeaking(form);
      if (mockSessionId) {
        try {
          await api.attachMockJob(mockSessionId, "speaking", job.id);
        } catch {
          /* non-fatal */
        }
      }
      router.push(`/app/results/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start evaluation");
    } finally {
      setPending(false);
    }
  }

  const copy = PART_COPY[task];
  const showPrep = task === "part2" && (phase === "intro" || phase === "prep") && !audioBlob && mode === "exam";
  const showSpeak =
    mode === "exam" && (task !== "part2" || recording || Boolean(audioBlob) || phase === "speak" || phase === "done");
  const currentQuestion = questions[qIndex];
  const title = fullTest ? "Full speaking test" : copy.title;
  const lede = fullTest
    ? "Parts 1–3 in one sitting, about 11–14 minutes. Same test for Academic and General Training. Practice estimate — not an official IELTS score."
    : paperMeta
      ? `${pack.title} · ${paperMeta.completed} done · ${paperMeta.remaining} new topics left.`
      : "The speaking test is the same for Academic and General Training. About 11–14 minutes in the exam. Practice estimate — not an official IELTS score.";

  return (
    <div>
      <PageHeader eyebrow="Speaking" title={title} lede={lede} />

      <div className="studio-bar">
        <div>
          <p className="field-label">Part</p>
          <div className="chip-row">
            <Chip selected={fullTest} onClick={chooseFullTest} disabled={Boolean(mockSessionId) && fullTest}>
              Full test
            </Chip>
            <Chip selected={!fullTest && task === "part1"} onClick={() => setPart("part1")} disabled={Boolean(mockSessionId)}>
              Part 1
            </Chip>
            <Chip selected={!fullTest && task === "part2"} onClick={() => setPart("part2")} disabled={Boolean(mockSessionId)}>
              Part 2
            </Chip>
            <Chip selected={!fullTest && task === "part3"} onClick={() => setPart("part3")} disabled={Boolean(mockSessionId)}>
              Part 3
            </Chip>
          </div>
        </div>
        <div className={`timer${recording && remaining <= 10 ? " is-over" : ""}`}>
          <span className="timer-readout">{formatClock(mode === "exam" ? remaining : elapsed)}</span>
          <span className="muted">
            {fullTest ? `Part ${task === "part1" ? "1" : task === "part2" ? "2" : "3"} · ` : ""}
            {task === "part2" && phase === "prep"
              ? "Preparation"
              : recording
                ? "Speaking"
                : copy.lede}
          </span>
        </div>
      </div>

      <div className="studio-grid">
        <ExamPrompt
          skill="speaking"
          task={task}
          module={module}
          prompt={prompt}
          editing={editingPrompt}
          onChange={mockSessionId ? undefined : setPrompt}
          examiner={customPrompt ? undefined : examinerLine(task, pack)}
          activeQuestion={recording || phase === "speak" ? qIndex : undefined}
        />

        <div className="card section-gap">
          {mode === "exam" && (
            <div className="record-stage">
              {fullTest && phase === "intro" && !recording && !audioBlob && (
                <>
                  <p className="muted">
                    The examiner will take you through Part 1, a cue-card long turn with one minute to prepare, then
                    Part 3. The microphone stays on for the whole interview.
                  </p>
                  <Button onClick={() => void beginRecording()}>Start the interview</Button>
                </>
              )}

              {showPrep && (!fullTest || recording || phase === "prep") && (
                <>
                  {phase === "intro" && !fullTest && (
                    <>
                      <p className="muted">The examiner will give you a cue card and one minute to prepare. You may write notes. You cannot use a dictionary.</p>
                      <Button onClick={() => setPhase("prep")}>Begin preparation</Button>
                    </>
                  )}
                  {phase === "prep" && (
                    <>
                      <p className="elapsed">{formatClock(prepLeft)}</p>
                      <p className="muted">You have one minute to prepare. Make notes if you wish.</p>
                      <label className="prep-notes">
                        Notes (not marked)
                        <textarea
                          value={notes}
                          onChange={(event) => setNotes(event.target.value)}
                          placeholder="Keywords only — as in the exam."
                          maxLength={800}
                        />
                      </label>
                      {prepLeft <= 50 && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            if (fullTest && recording) {
                              setPhase("speak");
                              setStageOffset(elapsed);
                              return;
                            }
                            void beginRecording();
                          }}
                        >
                          I&apos;m ready to speak
                        </Button>
                      )}
                    </>
                  )}
                </>
              )}

              {showSpeak && !(fullTest && phase === "intro" && !recording && !audioBlob) && (
                <>
                  {recording && phase !== "prep" && (
                    <>
                      <p className="elapsed">{formatClock(stageElapsed)}</p>
                      {task === "part2" ? (
                        <p className="examiner-line">You may speak for one to two minutes. I will tell you when the time is up.</p>
                      ) : currentQuestion ? (
                        <p className="examiner-line">{currentQuestion}</p>
                      ) : null}
                    </>
                  )}
                  {audioBlob && !recording && (
                    <>
                      <p className="examiner-line">Thank you.</p>
                      <p className="elapsed">{formatClock(elapsed)}</p>
                    </>
                  )}
                  {!fullTest && !audioBlob && !recording && task !== "part2" && (
                    <p className="muted">Answer in turn. Use Next question when you have finished each answer. The part stops at {Math.round(speakLimit / 60)} minutes.</p>
                  )}
                  {!fullTest && !audioBlob && (task !== "part2" || phase === "speak") && (
                    <RecordButton recording={recording} onClick={toggleRecord} />
                  )}
                  {fullTest && recording && phase !== "prep" && (
                    <Button variant="secondary" onClick={task === "part3" ? stopRecording : continueInterview}>
                      {task === "part3" ? "Finish interview" : task === "part1" ? "Continue to Part 2" : "Continue to Part 3"}
                    </Button>
                  )}
                  {recording && task !== "part2" && qIndex < questions.length - 1 && (
                    <Button variant="secondary" size="sm" onClick={() => setQIndex((value) => value + 1)}>
                      Next question
                    </Button>
                  )}
                  {audioUrl && !recording && (
                    <audio className="audio-player" controls src={audioUrl}>
                      Your browser cannot play this recording.
                    </audio>
                  )}
                  {audioBlob && !recording && !mockSessionId && (
                    <Button variant="ghost" size="sm" onClick={resetAttempt}>
                      Record again
                    </Button>
                  )}
                </>
              )}
            </div>
          )}

          {mode === "upload" && (
            <label>
              Audio file
              <input
                type="file"
                accept="audio/webm,audio/wav,audio/mpeg,audio/mp4,audio/ogg,.webm,.wav,.mp3,.m4a,.ogg"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
              <span className="helper">WebM, WAV, MP3, M4A, or OGG. 15 MB maximum.</span>
              {file && (
                <span className="file-name">
                  {file.name} · {Math.round(file.size / 1024)} KB
                </span>
              )}
            </label>
          )}

          {mode === "transcript" && (
            <label>
              Transcript
              <textarea
                value={transcript}
                onChange={(event) => setTranscript(event.target.value)}
                maxLength={12000}
                placeholder="Paste what you said. Pronunciation will be marked as a text proxy."
              />
            </label>
          )}

          {error && <p className="error">{error}</p>}
          <div className="sticky-actions">
            <span className="muted">
              {canSubmit()
                ? "Hand in this recording for scoring."
                : mode === "exam"
                  ? fullTest
                    ? "Finish all three parts to continue."
                    : "Complete the recording to continue."
                  : "Add a file or transcript."}
            </span>
            <Button onClick={submit} loading={pending} disabled={!canSubmit()}>
              Hand in
            </Button>
          </div>

          {!mockSessionId && (
          <details className="practice-tools">
            <summary>Practice options</summary>
            <div className="chip-row">
              <Chip selected={mode === "exam"} onClick={() => setMode("exam")}>
                Exam recording
              </Chip>
              <Chip selected={mode === "upload"} onClick={() => setMode("upload")}>
                Upload
              </Chip>
              <Chip selected={mode === "transcript"} onClick={() => setMode("transcript")}>
                Transcript
              </Chip>
            </div>
            <div className="btn-row">
              <Button variant="ghost" size="sm" onClick={nextTopic}>
                Next unused topic ({pack.title})
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setCustomPrompt(true);
                  setEditingPrompt((value) => !value);
                }}
              >
                {editingPrompt ? "Done editing cue" : "Edit cue"}
              </Button>
            </div>
          </details>
          )}
        </div>
      </div>
    </div>
  );
}
