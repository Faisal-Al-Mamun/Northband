export function qtypeLabel(qtype: string) {
  const map: Record<string, string> = {
    tfng: "True / False / Not Given",
    ynng: "Yes / No / Not Given",
    mcq: "Multiple choice",
    short_answer: "Short answer",
    completion: "Sentence completion",
    matching: "Matching",
    matching_headings: "Matching headings",
    matching_features: "Matching features",
    matching_information: "Matching information",
    table_completion: "Table completion",
    diagram_label: "Diagram labelling",
    flowchart_completion: "Flow-chart completion",
    summary_completion: "Summary completion",
    note_completion: "Note completion",
    multi_blank: "Notes completion",
  };
  return map[qtype] || qtype.replace(/_/g, " ");
}

export function qtypeInstruction(qtype: string, skill: "reading" | "listening") {
  const source = skill === "listening" ? "the recording" : "the passage";
  const map: Record<string, string> = {
    tfng: `Do the following statements agree with the information given in ${source}?\nTRUE if the statement agrees with the information\nFALSE if the statement contradicts the information\nNOT GIVEN if there is no information on this`,
    ynng: `Do the following statements agree with the claims of the writer?\nYES if the statement agrees with the claims of the writer\nNO if the statement contradicts the claims of the writer\nNOT GIVEN if it is impossible to say what the writer thinks about this`,
    mcq: "Choose the correct letter, A, B, C or D.",
    short_answer: `Answer the questions below.\nChoose NO MORE THAN THREE WORDS AND/OR A NUMBER from ${source} for each answer.`,
    completion: `Complete the sentences below.\nChoose NO MORE THAN THREE WORDS from ${source} for each answer.`,
    matching: "Match each item with the correct option.",
    matching_headings:
      "The passage has several paragraphs. Choose the correct heading for each paragraph from the list of headings. You may use each heading only once.",
    matching_features: "Match each item with the correct option. You may use any option more than once.",
    matching_information:
      "Which paragraph contains the following information? You may use any letter more than once.",
    table_completion: `Complete the table below.\nChoose NO MORE THAN TWO WORDS AND/OR A NUMBER from ${source} for each answer.`,
    summary_completion: `Complete the summary below.\nChoose NO MORE THAN TWO WORDS from ${source} for each answer.`,
    note_completion: `Complete the notes below.\nChoose NO MORE THAN TWO WORDS AND/OR A NUMBER from ${source} for each answer.`,
  };
  return map[qtype] || qtypeLabel(qtype);
}

export function skillLabel(skill: string) {
  const map: Record<string, string> = {
    writing: "Writing",
    speaking: "Speaking",
    reading: "Reading",
    listening: "Listening",
  };
  return map[skill] || skill;
}

export function moduleLabel(module: string) {
  if (module === "general") return "General Training";
  if (module === "shared") return "Academic & GT";
  return "Academic";
}

export function taskLabel(skill: string, task: string) {
  if (skill === "speaking") {
    if (task === "part1") return "Part 1";
    if (task === "part3") return "Part 3";
    if (task === "full") return "Full test";
    return "Part 2";
  }
  if (skill === "reading" || skill === "listening") {
    return task === "set" ? "Full set" : "Drill";
  }
  return task === "task1" ? "Task 1" : "Task 2";
}

export function attemptTitle(skill: string, module: string, task: string) {
  if (skill === "reading" || skill === "listening") {
    return `${skillLabel(skill)} · ${moduleLabel(module)}`;
  }
  if (skill === "speaking") return `Speaking ${taskLabel(skill, task)}`;
  return `${moduleLabel(module)} Writing ${taskLabel(skill, task)}`;
}

export function statusLabel(status: string, stage?: string | null) {
  if (status === "queued") return "Queued";
  if (status === "running") return stageLabel(stage) || "Scoring";
  if (status === "completed") return "Ready";
  if (status === "failed") return "Failed";
  if (status === "in_progress") return "In progress";
  return status.replace(/_/g, " ");
}

export function stageLabel(stage?: string | null) {
  const map: Record<string, string> = {
    queued: "In the queue",
    ingest: "Loading your attempt",
    tools: "Checking length and coverage",
    plan: "Choosing which agents to run",
    transcribe: "Transcribing audio",
    analyzing: "Reading language and criteria",
    verify: "Checking evidence quotes",
    grading: "Marking against keys",
    scoring: "Finalising bands",
    coaching: "Building your study list",
    coach_loop: "Investigating missed items",
    synthesize: "Writing explanations",
    persisting: "Saving the report",
    completed: "Ready",
    failed: "Failed",
  };
  if (!stage) return "";
  return map[stage] || stage.replace(/_/g, " ");
}

export function statusTone(status: string): "ok" | "warn" | "danger" | "muted" {
  if (status === "completed") return "ok";
  if (status === "queued" || status === "running") return "warn";
  if (status === "failed") return "danger";
  return "muted";
}

export function shortDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function wordCount(text: string) {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

export function greeting(name?: string) {
  const hour = new Date().getHours();
  const hello = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const first = name?.trim().split(/\s+/)[0];
  return first ? `${hello}, ${first}` : hello;
}

export function criterionShort(name: string) {
  const map: Record<string, string> = {
    "Task Achievement": "TA",
    "Task Response": "TR",
    "Coherence and Cohesion": "CC",
    "Lexical Resource": "LR",
    "Grammatical Range and Accuracy": "GRA",
    "Fluency and Coherence": "FC",
    Pronunciation: "Pron.",
    "Objective accuracy": "Acc.",
  };
  return map[name] || name.replace(" and ", " & ");
}

export function recommendedMinutes(skill: string, task: string) {
  if (skill === "writing") return task === "task1" ? 20 : task === "full" ? 60 : 40;
  if (skill === "reading") return 60;
  if (skill === "listening") return 30;
  if (task === "part2") return 2;
  return 4;
}

export function formatClock(totalSeconds: number) {
  const sign = totalSeconds < 0 ? "-" : "";
  const abs = Math.abs(totalSeconds);
  const minutes = Math.floor(abs / 60);
  const seconds = abs % 60;
  return `${sign}${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function bandMeaning(skill: string, band: number) {
  const whole = Math.min(9, Math.max(5, Math.round(band)));
  const writing: Record<number, string> = {
    5: "Partial task coverage, limited development, noticeable language errors.",
    6: "Addresses the task; ideas are generally clear; errors rarely block meaning.",
    7: "Clear position, developed ideas, flexible vocabulary, frequent error-free sentences.",
    8: "Fully developed, precise vocabulary, mostly error-free, natural cohesion.",
    9: "Expert user: fully addresses the task with accurate, flexible language.",
  };
  const speaking: Record<number, string> = {
    5: "Can keep going on familiar topics, but hesitation and errors are frequent.",
    6: "Willing to speak at length; generally coherent; some unclear wording.",
    7: "Speaks at length with little effort; flexible vocabulary; easy to follow.",
    8: "Fluent, precise, and easy to understand throughout, with only occasional slips.",
    9: "Expert user: fully operational command, fully appropriate and accurate.",
  };
  const objective: Record<number, string> = {
    5: "Modest user — around half the items. Watch TFNG traps and spelling.",
    6: "Competent user — typically mid-20s / 40. Paraphrase and numbers still cost marks.",
    7: "Good user — typically ~30 / 40 Academic Reading or Listening.",
    8: "Very good user — only a few misses, often Not Given or spelling.",
    9: "Expert user — near-full paper.",
  };
  const table = skill === "speaking" ? speaking : skill === "writing" ? writing : objective;
  return {
    whole,
    meaning: table[whole] || table[6],
  };
}

export function drillHref(item: {
  drill_prompt?: string | null;
  drill_task?: string | null;
  drill_skill?: string | null;
  detail?: string;
  id?: string;
}) {
  const skill = item.drill_skill || "writing";
  const prompt = item.drill_prompt || item.detail || "";
  const task = item.drill_task || (skill === "speaking" ? "part2" : skill === "writing" ? "task2" : "set");
  const path =
    skill === "speaking"
      ? "/app/speaking"
      : skill === "reading"
        ? "/app/reading"
        : skill === "listening"
          ? "/app/listening"
          : "/app/writing";
  const qs = new URLSearchParams();
  if (prompt) qs.set("prompt", prompt);
  if (task) qs.set("task", task);
  if (item.id) qs.set("item", item.id);
  return `${path}?${qs.toString()}`;
}
