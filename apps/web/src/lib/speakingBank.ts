export type SpeakingPart = "part1" | "part2" | "part3";

export type SpeakingSet = {
  id: string;
  title: string;
  part1: { topic: string; examiner: string; questions: string[] };
  part2: { topic: string; examiner: string; bullets: string[]; explain: string };
  part3: { examiner: string; questions: string[] };
};

export const SPEAKING_SETS: SpeakingSet[] = [
  {
    id: "skills",
    title: "Hometown / learning a skill",
    part1: {
      topic: "Let's talk about your hometown.",
      examiner: "Now, in this first part, I'd like to ask you some questions about yourself.",
      questions: [
        "Where is your hometown?",
        "What do you like most about living there?",
        "Has your hometown changed much in recent years?",
        "Would you like to continue living there in the future?",
      ],
    },
    part2: {
      topic: "Describe a skill you would like to learn.",
      examiner:
        "Now, I'm going to give you a topic and I'd like you to talk about it for one to two minutes. Before you talk, you will have one minute to think about what you are going to say. You can make some notes if you wish. Do you understand?",
      bullets: ["what the skill is", "why you want to learn it", "how you would learn it"],
      explain: "how this skill would help you",
    },
    part3: {
      examiner:
        "We've been talking about learning a skill, and I'd like to discuss with you one or two more general questions related to this.",
      questions: [
        "Do you think schools should spend more time teaching practical skills? Why or why not?",
        "What skills do you think will be most useful in the future?",
        "Is it better to learn a new skill from a teacher or by yourself?",
        "Some people say we should keep learning throughout our lives. Do you agree?",
      ],
    },
  },
  {
    id: "travel",
    title: "Free time / a place to visit",
    part1: {
      topic: "Let's talk about what you do in your free time.",
      examiner: "Now, in this first part, I'd like to ask you some questions about yourself.",
      questions: [
        "What do you usually do in your free time?",
        "Did you have the same hobbies when you were a child?",
        "Do you prefer to spend free time alone or with other people?",
        "Is there a new hobby you would like to try?",
      ],
    },
    part2: {
      topic: "Describe a place you would like to visit.",
      examiner:
        "Now, I'm going to give you a topic and I'd like you to talk about it for one to two minutes. Before you talk, you will have one minute to think about what you are going to say. You can make some notes if you wish. Do you understand?",
      bullets: ["where it is", "how you would get there", "what you would do there"],
      explain: "why you would like to visit this place",
    },
    part3: {
      examiner:
        "We've been talking about a place you would like to visit, and I'd like to discuss with you one or two more general questions related to this.",
      questions: [
        "Why do you think people enjoy travelling to other countries?",
        "What are the advantages and disadvantages of tourism for a local area?",
        "Do you think it is better to travel independently or on an organised tour?",
        "How might travel change in the next twenty years?",
      ],
    },
  },
  {
    id: "work",
    title: "Work or study / a helpful person",
    part1: {
      topic: "Let's talk about your work or studies.",
      examiner: "Now, in this first part, I'd like to ask you some questions about yourself.",
      questions: [
        "Do you work or are you a student?",
        "What do you enjoy most about that?",
        "What is the most difficult part of your work or studies?",
        "What would you like to do in the future?",
      ],
    },
    part2: {
      topic: "Describe a person who has helped you in an important way.",
      examiner:
        "Now, I'm going to give you a topic and I'd like you to talk about it for one to two minutes. Before you talk, you will have one minute to think about what you are going to say. You can make some notes if you wish. Do you understand?",
      bullets: ["who this person is", "how they helped you", "when this happened"],
      explain: "why this help was important to you",
    },
    part3: {
      examiner:
        "We've been talking about a person who helped you, and I'd like to discuss with you one or two more general questions related to this.",
      questions: [
        "Do you think people are less willing to help others than in the past?",
        "Should helping others be taught in schools?",
        "What are the advantages of volunteering in the community?",
        "Some people prefer to solve problems alone. Is that a good approach?",
      ],
    },
  },
  {
    id: "media",
    title: "Daily news / an interesting book",
    part1: {
      topic: "Let's talk about news and the media.",
      examiner: "Now, in this first part, I'd like to ask you some questions about yourself.",
      questions: [
        "How do you usually get the news?",
        "Do you prefer reading the news or watching it?",
        "Is there too much news in daily life?",
        "Did you follow the news when you were younger?",
      ],
    },
    part2: {
      topic: "Describe a book that you found interesting.",
      examiner:
        "Now, I'm going to give you a topic and I'd like you to talk about it for one to two minutes. Before you talk, you will have one minute to think about what you are going to say. You can make some notes if you wish. Do you understand?",
      bullets: ["what the book was", "when you read it", "what it was about"],
      explain: "why you found it interesting",
    },
    part3: {
      examiner:
        "We've been talking about a book you found interesting, and I'd like to discuss with you one or two more general questions related to this.",
      questions: [
        "Do you think people read less than they used to? Why?",
        "Should children be encouraged to read more paper books than screens?",
        "What makes a book become a classic?",
        "How might reading habits change in the next twenty years?",
      ],
    },
  },
];

export const SPEAK_LIMITS: Record<SpeakingPart, number> = {
  part1: 5 * 60,
  part2: 2 * 60,
  part3: 5 * 60,
};

export function formatSpeakingPrompt(part: SpeakingPart, set: SpeakingSet): string {
  if (part === "part1") {
    return [set.part1.topic, ...set.part1.questions.map((item) => `- ${item}`)].join("\n");
  }
  if (part === "part2") {
    return [
      set.part2.topic,
      "You should say:",
      ...set.part2.bullets.map((item) => `- ${item}`),
      `- and explain ${set.part2.explain}`,
    ].join("\n");
  }
  return set.part3.questions.map((item) => `- ${item}`).join("\n");
}

export function examinerLine(part: SpeakingPart, set: SpeakingSet): string {
  if (part === "part1") return set.part1.examiner;
  if (part === "part2") return set.part2.examiner;
  return set.part3.examiner;
}

export function speakingQuestions(part: SpeakingPart, set: SpeakingSet): string[] {
  if (part === "part1") return set.part1.questions;
  if (part === "part3") return set.part3.questions;
  return [];
}

export function packFromCues(cues: unknown, fallback: SpeakingSet): SpeakingSet {
  if (!cues || typeof cues !== "object") return fallback;
  const raw = cues as Record<string, unknown>;
  const part1 = raw.part1;
  if (part1 && typeof part1 === "object" && !Array.isArray(part1) && "questions" in part1) {
    return {
      id: String(raw.id || fallback.id),
      title: String(raw.title || "Mock interview"),
      part1: part1 as SpeakingSet["part1"],
      part2: (raw.part2 as SpeakingSet["part2"]) || fallback.part2,
      part3: (raw.part3 as SpeakingSet["part3"]) || fallback.part3,
    };
  }
  const p1 = String(raw.part1 || "").trim();
  const p2 = String(raw.part2 || "").trim();
  const p3 = String(raw.part3 || "").trim();
  if (!p1 && !p2 && !p3) return fallback;
  const part2Topic = p2.split(/You should say/i)[0].trim() || fallback.part2.topic;
  return {
    id: "mock",
    title: "Mock interview",
    part1: {
      topic: p1 || fallback.part1.topic,
      examiner: fallback.part1.examiner,
      questions: p1 ? [p1] : fallback.part1.questions,
    },
    part2: {
      topic: part2Topic,
      examiner: fallback.part2.examiner,
      bullets: fallback.part2.bullets,
      explain: fallback.part2.explain,
    },
    part3: {
      examiner: fallback.part3.examiner,
      questions: p3 ? p3.split(/(?<=\?)\s+/).filter(Boolean) : fallback.part3.questions,
    },
  };
}

export function formatFullSpeakingPrompt(set: SpeakingSet): string {
  return [
    "Part 1 — Interview",
    formatSpeakingPrompt("part1", set),
    "",
    "Part 2 — Long turn",
    formatSpeakingPrompt("part2", set),
    "",
    "Part 3 — Discussion",
    formatSpeakingPrompt("part3", set),
  ].join("\n");
}
