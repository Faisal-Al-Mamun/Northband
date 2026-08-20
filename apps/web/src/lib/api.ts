import type {
  ContentSetDetail,
  ContentSetSummary,
  EvaluationDetail,
  EvaluationSummary,
  MockBlueprint,
  MockSession,
  NextPaper,
  NextSet,
  ProgressSummary,
  RevisionResult,
  StudyPlanItem,
  User,
} from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("nb_token");
}

export function setToken(value: string | null) {
  if (value) localStorage.setItem("nb_token", value);
  else localStorage.removeItem("nb_token");
}

function errorMessage(detail: unknown, fallback: string) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : ""))
      .filter(Boolean);
    if (parts.length) return parts.join(". ");
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const auth = getToken();
  if (auth) headers.set("Authorization", `Bearer ${auth}`);
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body;
    } catch {
      /* ignore */
    }
    if (res.status === 413) throw new Error("That file is too large. Use an audio clip under 15 MB.");
    if (res.status === 429) throw new Error("Too many attempts. Wait a few minutes and try again.");
    throw new Error(errorMessage(detail, "Request failed"));
  }
  return res.json() as Promise<T>;
}

export async function fetchAuthedBlobUrl(path: string): Promise<string> {
  const auth = getToken();
  const res = await fetch(`${API}${path}`, {
    headers: auth ? { Authorization: `Bearer ${auth}` } : {},
  });
  if (!res.ok) throw new Error("Could not load audio");
  const type = (res.headers.get("content-type") || "audio/wav").split(";")[0];
  const buffer = await res.arrayBuffer();
  const blob = new Blob([buffer], { type });
  return URL.createObjectURL(blob);
}

export const api = {
  register: (body: { email: string; password: string; display_name: string }) =>
    request<{ access_token: string; user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  me: () => request<User>("/auth/me"),
  updateMe: (body: Partial<Pick<User, "display_name" | "target_band" | "preferred_module">>) =>
    request<User>("/auth/me", { method: "PATCH", body: JSON.stringify(body) }),
  createWriting: (body: {
    module: string;
    task: string;
    prompt: string;
    essay: string;
    parent_attempt_id?: string;
    study_item_id?: string;
    bank_item_id?: string;
  }) =>
    request<EvaluationSummary>("/evaluations/writing", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createSpeaking: (form: FormData) =>
    request<EvaluationSummary>("/evaluations/speaking", { method: "POST", body: form }),
  createReading: (body: {
    content_set_id: string;
    module?: string;
    mode?: string;
    answers: Record<string, unknown>;
    mock_session_id?: string;
  }) =>
    request<EvaluationSummary>("/evaluations/reading", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createListening: (body: {
    content_set_id: string;
    module?: string;
    mode?: string;
    answers: Record<string, unknown>;
    mock_session_id?: string;
  }) =>
    request<EvaluationSummary>("/evaluations/listening", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listEvaluations: (query = "") => request<EvaluationSummary[]>(`/evaluations${query}`),
  getEvaluation: (id: string) => request<EvaluationDetail>(`/evaluations/${id}`),
  progress: () => request<ProgressSummary>("/progress/summary"),
  studyPlan: () => request<StudyPlanItem[]>("/progress/study-plan"),
  updatePlanItem: (id: string, status: "pending" | "done" | "in_progress") =>
    request<StudyPlanItem>(`/progress/study-plan/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  startDrill: (id: string) =>
    request<{ study_item_id: string; skill: string; task: string; prompt: string }>(
      `/progress/study-plan/${id}/drill`,
      { method: "POST" },
    ),
  reviseEvaluation: (id: string, span?: string) =>
    request<RevisionResult>(`/evaluations/${id}/revise`, {
      method: "POST",
      body: JSON.stringify({ span: span || null }),
    }),
  listContentSets: (skill: string, module?: string) => {
    const params = new URLSearchParams({ skill });
    if (module) params.set("module", module);
    return request<ContentSetSummary[]>(`/content/sets?${params}`);
  },
  nextPrompt: (skill: string, task: string, module?: string, excludeId?: string) => {
    const params = new URLSearchParams({ skill, task });
    if (module) params.set("module", module);
    if (excludeId) params.set("exclude_id", excludeId);
    return request<NextPaper>(`/content/next-prompt?${params}`);
  },
  nextSet: (skill: string, module?: string, excludeId?: string) => {
    const params = new URLSearchParams({ skill });
    if (module) params.set("module", module);
    if (excludeId) params.set("exclude_id", excludeId);
    return request<NextSet>(`/content/next-set?${params}`);
  },
  getContentSet: (id: string, includeTranscript = false) =>
    request<ContentSetDetail>(`/content/sets/${id}?include_transcript=${includeTranscript}`),
  prepareListeningAudio: (id: string) =>
    request<{ assets: { id: string; filename: string; duration_sec: number; ready: boolean }[] }>(
      `/content/sets/${id}/prepare-audio`,
      { method: "POST" },
    ),
  listMockBlueprints: (module?: string) => {
    const q = module ? `?module=${encodeURIComponent(module)}` : "";
    return request<MockBlueprint[]>(`/mocks/blueprints${q}`);
  },
  startMock: (body: { module: string; blueprint_id?: string }) =>
    request<MockSession>("/mocks/sessions", { method: "POST", body: JSON.stringify(body) }),
  getMock: (id: string) => request<MockSession>(`/mocks/sessions/${id}`),
  attachMockJob: (sessionId: string, skill: string, jobId: string) =>
    request<MockSession>(`/mocks/sessions/${sessionId}/attach/${skill}?job_id=${encodeURIComponent(jobId)}`, {
      method: "POST",
    }),
  refreshMock: (id: string) =>
    request<MockSession>(`/mocks/sessions/${id}/refresh`, { method: "POST" }),
};
