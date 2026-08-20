export type User = {
  id: string;
  email: string;
  display_name: string;
  target_band: number | null;
  preferred_module: "academic" | "general";
};

export type EvaluationSummary = {
  id: string;
  skill: string;
  module: string;
  task: string;
  status: string;
  error: string | null;
  overall_band: number | null;
  created_at: string;
  stage?: string | null;
};

export type EvaluationDetail = EvaluationSummary & {
  prompt: string | null;
  input_text: string | null;
  transcript: string | null;
  speaking_mode: string | null;
  attempt_id?: string | null;
  stage?: string | null;
  report: Report | null;
};

export type CriterionNote = {
  criterion: string;
  proposed_band?: number;
  band?: number;
  summary?: string;
  rationale?: string;
  evidence?: { quote: string; comment: string }[];
};

export type ObjectiveReport = {
  earned_marks?: number;
  max_marks?: number;
  by_type?: Record<string, { correct: number; total: number }>;
  per_item?: {
    question_id: string;
    number?: number;
    qtype?: string;
    stem?: string;
    correct?: boolean;
    given?: unknown;
    canonical?: string;
  }[];
  misses?: { question_id: string; number?: number; stem?: string; canonical?: string }[];
  explanations?: {
    question_id: string;
    explanation?: string;
    tip?: string;
    skill_tag?: string;
    trap_type?: string;
  }[];
  transcripts?: { section: string; transcript: string }[];
  content_title?: string;
  mode?: string;
  table_id?: string;
  is_drill?: boolean;
  overall_band?: number | null;
};

export type Report = {
  disclaimer?: string;
  stage?: string;
  objective?: ObjectiveReport;
  tools?: {
    word_count?: number;
    expected_min_words?: number | null;
    under_length?: boolean;
    linker_count?: number;
    linkers_found?: string[];
    overview_present?: boolean | null;
    filler_count?: number;
    pronunciation_is_proxy?: boolean;
    duration_seconds?: number | null;
    words_per_minute?: number | null;
    task_coverage?: { coverage_ratio?: number | null; missing?: string[] };
  };
  writing?: Record<string, unknown>;
  speaking?: Record<string, unknown>;
  grammar?: {
    issues: {
      span: string;
      issue_type: string;
      correction: string;
      explanation: string;
      cefr_tag?: string | null;
    }[];
    recurring_patterns: string[];
    lexical_range_notes: string;
    vocabulary_upgrades: string[];
  };
  scores?: {
    criteria: { criterion: string; band: number; rationale: string }[];
    overall_band: number | null;
    confidence: number;
    scoring_notes: string;
    exam_ceilings?: string[];
    examiner_first_impression?: string;
  };
  feedback?: {
    strengths: string[];
    weaknesses: string[];
    actions: {
      title: string;
      detail: string;
      skill_focus: string;
      drill_prompt?: string;
      drill_task?: string;
      drill_skill?: string;
    }[];
    examiner_summary: string;
  };
  performance?: {
    trends: { label: string; direction: string; note: string }[];
    plateau: boolean;
    next_focus: string;
    comparison_note: string;
  };
  delta?: {
    parent_attempt_id?: string;
    previous_overall?: number | null;
    current_overall?: number;
    overall_delta?: number | null;
    criteria?: { criterion: string; previous?: number | null; current: number; delta?: number | null }[];
  };
  revisions?: {
    original_span: string;
    rewritten: string;
    changes: string[];
    target_band: number;
    notes: string;
  }[];
  warnings?: string[];
  agent_trace?: {
    thesis?: string;
    plan?: {
      run_specialist?: boolean;
      run_grammar?: boolean;
      run_feedback?: boolean;
      run_performance?: boolean;
      use_cache?: boolean;
      skipped?: { agent: string; reason: string }[];
    };
    stages?: {
      name: string;
      kind: string;
      reason?: string;
      quote_hit_rate?: number;
      quotes_dropped?: number;
      quotes_kept?: number;
      skipped?: { agent: string; reason: string }[];
      scoring_llm?: boolean;
    }[];
    calls?: {
      agent: string;
      provider: string;
      model: string;
      latency_ms: number;
      prompt_tokens?: number | null;
      completion_tokens?: number | null;
      success: boolean;
    }[];
  };
};

export type ProgressSummary = {
  target_band: number | null;
  latest_overall: number | null;
  attempt_count: number;
  series: {
    attempt_id: string;
    skill: string;
    module: string;
    task: string;
    overall_band: number;
    created_at: string;
  }[];
  skills: {
    skill: string;
    average_band: number | null;
    attempt_count: number;
    latest_band: number | null;
  }[];
  next_focus: string | null;
  overall_estimate?: number | null;
  overall_confidence?: number | null;
  missing_skills?: string[];
  type_accuracy?: Record<string, { correct: number; total: number }>;
};

export type StudyPlanItem = {
  id: string;
  title: string;
  detail: string;
  skill_focus: string;
  status: string;
  drill_prompt?: string | null;
  drill_task?: string | null;
  drill_skill?: string | null;
  created_at: string;
};

export type RevisionResult = {
  original_span: string;
  rewritten: string;
  changes: string[];
  target_band: number;
  notes: string;
};

export type ContentSetSummary = {
  id: string;
  skill: string;
  module: string;
  slug: string;
  title: string;
  difficulty: string;
  time_limit_sec: number;
  question_count: number;
  review_status: string;
  kind?: "exam" | "drill" | string;
};

export type ContentQuestion = {
  id: string;
  number: number;
  qtype: string;
  stem: string;
  options: { choices?: string[]; [key: string]: unknown };
  skill_tags: string[];
  marks: number;
  word_limit: number | null;
  passage_id: string | null;
  audio_asset_id: string | null;
};

export type ContentSetDetail = ContentSetSummary & {
  passages: { id: string; order_index: number; title: string; body: string }[];
  audio_assets: {
    id: string;
    order_index: number;
    section_label: string;
    url: string;
    duration_sec: number;
    accent: string;
    transcript: string | null;
  }[];
  questions: ContentQuestion[];
};

export type MockBlueprint = {
  id: string;
  module: string;
  title: string;
  listening_set_id: string | null;
  reading_set_id: string | null;
  writing_task1_prompt?: string;
  writing_task2_prompt?: string;
  speaking_cues?: Record<string, unknown>;
};

export type MockSession = {
  id: string;
  module: string;
  status: string;
  current_skill: string;
  job_ids: Record<string, string>;
  skill_bands: Record<string, number>;
  overall_band: number | null;
  confidence: number | null;
  blueprint: MockBlueprint | null;
};

export type NextPaper = {
  id: string | null;
  skill: string;
  module: string;
  task: string;
  slug: string;
  title: string;
  prompt: string;
  source: string;
  generated: boolean;
  recycled: boolean;
  remaining: number;
  completed: number;
  total: number;
  visual: import("./taskVisuals").TaskVisualSpec | null;
  speaking: {
    id: string;
    title: string;
    part1: { topic: string; examiner: string; questions: string[] };
    part2: { topic: string; examiner: string; bullets: string[]; explain: string };
    part3: { examiner: string; questions: string[] };
  } | null;
};

export type NextSet = {
  id: string | null;
  title: string;
  remaining: number;
  completed: number;
  total: number;
  recycled: boolean;
  completed_ids: string[];
};
