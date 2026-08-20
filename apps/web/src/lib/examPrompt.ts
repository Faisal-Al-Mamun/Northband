import { findTaskVisual, type TaskVisualSpec } from "./taskVisuals";

export type ParsedExamPrompt = {
  minutes: number | null;
  minWords: number | null;
  topic: string;
  instruction: string;
  bullets: string[];
  bulletLead: string;
  visual: TaskVisualSpec | null;
};

const INSTRUCTION_RE =
  /^(summarise|summarize|give reasons|discuss both|write a letter|write about the following)/i;

function splitSentences(text: string) {
  return text
    .replace(/\s+/g, " ")
    .split(/(?<=[.?:])\s+(?=[A-Z“"])/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function extractInlineBullets(text: string) {
  const letter = text.match(/in your letter:\s*(.+)$/i);
  if (letter?.[1]) {
    return {
      lead: "In your letter:",
      bullets: letter[1]
        .split(/,\s*(?=(?:describe|explain|say|give|suggest|ask|apologise|apologize)\b)/i)
        .map((item) => item.replace(/^(and\s+)?/, "").replace(/\.$/, "").trim())
        .filter((item) => item.length > 1),
    };
  }
  const cue = text.match(/you should say:\s*(.+)$/i);
  if (cue?.[1]) {
    const rest = cue[1];
    const explain = rest.split(/\band explain\b/i);
    const items = (explain[0] || "")
      .split(/,\s*/)
      .map((item) => item.replace(/^(and\s+)?/, "").trim())
      .filter((item) => item.length > 1);
    if (explain[1]) items.push(`explain ${explain[1].replace(/\.$/, "").trim()}`);
    return { lead: "You should say:", bullets: items };
  }
  return null;
}

export function parseExamPrompt(
  prompt: string,
  opts: { skill: string; task: string; module: string },
): ParsedExamPrompt {
  const visual = findTaskVisual(prompt, opts);
  const minutes = opts.skill === "writing" ? (opts.task === "task1" ? 20 : 40) : null;
  const minWords = opts.skill === "writing" ? (opts.task === "task1" ? 150 : 250) : null;

  const lines = prompt
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !/^you should spend/i.test(line) && !/^write at least/i.test(line));

  const bullets: string[] = [];
  let bulletLead = "";
  const body: string[] = [];

  for (const line of lines) {
    if (/^(in your letter|you should say|include)\b/i.test(line) && !/^[-•]/.test(line)) {
      const inline = extractInlineBullets(line);
      if (inline && inline.bullets.length) {
        bulletLead = inline.lead;
        bullets.push(...inline.bullets);
        continue;
      }
      bulletLead = line.replace(/:$/, "") + ":";
      continue;
    }
    if (/^[-•*]/.test(line)) {
      const bullet = line.replace(/^[-•*]\s*/, "").replace(/\.$/, "").trim();
      if (bullet.length > 1) bullets.push(bullet);
      continue;
    }
    body.push(line);
  }

  if (!bullets.length && body.length) {
    const last = body[body.length - 1];
    const inline = extractInlineBullets(last);
    if (inline && inline.bullets.length) {
      bulletLead = inline.lead;
      bullets.push(...inline.bullets);
      body[body.length - 1] = last.replace(/\s*(In your letter|You should say)[:.].*$/i, "").trim();
      if (!body[body.length - 1]) body.pop();
    }
  }

  const sentences = body.flatMap(splitSentences);
  const instructionParts: string[] = [];
  const topicParts: string[] = [];
  for (const sentence of sentences) {
    if (INSTRUCTION_RE.test(sentence) || /make comparisons where relevant/i.test(sentence)) {
      instructionParts.push(sentence);
    } else {
      topicParts.push(sentence);
    }
  }

  const topicText = topicParts.join(" ").trim();
  return {
    minutes,
    minWords,
    topic: topicText || (bullets.length ? "" : (sentences[0] || prompt).trim()),
    instruction: instructionParts.join(" ").trim(),
    bullets,
    bulletLead,
    visual,
  };
}

export function formatWritingPrompt(parsed: {
  topic: string;
  instruction?: string;
  bullets?: string[];
  bulletLead?: string;
}) {
  const parts = [parsed.topic];
  if (parsed.instruction) parts.push(parsed.instruction);
  if (parsed.bullets?.length) {
    parts.push([parsed.bulletLead || "In your letter:", ...parsed.bullets.map((item) => `- ${item}`)].join("\n"));
  }
  return parts.join("\n\n");
}
