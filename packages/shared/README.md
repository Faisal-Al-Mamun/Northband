# Shared contracts

Northband does not publish a generated client. API contracts are Pydantic models; the Next.js studio mirrors the shapes it needs in TypeScript.

| Concern | API | Web |
|---------|-----|-----|
| Agent JSON | `apps/api/app/schemas/agents.py` (`WritingAgentOutput`, `SpeakingAgentOutput`, `GrammarAgentOutput`, `CoachStepOutput`, …) | Nested fields on `Report` in `apps/web/src/lib/types.ts` |
| HTTP bodies / jobs | `apps/api/app/schemas/evaluations.py`, `auth.py`, `content.py` | `apps/web/src/lib/api.ts` + `User`, `EvaluationSummary`, `EvaluationDetail`, `ProgressSummary`, `StudyPlanItem`, `RevisionResult`, `NextPaper`, `NextSet`, `ContentSetSummary` |
| Criterion labels | `apps/api/app/agents/rubrics.py` | `apps/web/src/lib/labels.ts` (`criterionShort`, task/module names, `full` speaking/writing papers) |
| Exam copy / visuals | Task prompts in `prompt_bank.py` + `content/generate.py` | `examPrompt.ts`, `taskVisuals.ts`, `ExamPrompt.tsx`, `TaskVisual.tsx` |

When you add a report field:

1. Extend the Pydantic schema and persist it on `attempts.report` (see [docs/AGENTS.md](../../docs/AGENTS.md)).
2. Add the same optional field to `Report` in `types.ts`.
3. Render it on `apps/web/src/app/app/results/[id]/page.tsx`.

Keep agent output JSON-only. The studio should tolerate partial reports:

- Writing/Speaking: `tools` / `grammar` before `scores`
- Reading/Listening: `objective` marks before explanations / `coach_trace`
- Drills: `objective.is_drill` with a null `overall_band`

Agent roster and graph wiring: [docs/AGENT_ARCHITECTURE.md](../../docs/AGENT_ARCHITECTURE.md).
