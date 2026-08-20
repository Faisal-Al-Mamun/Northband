from typing import Any, Literal

from pydantic import BaseModel, Field

Module = Literal["academic", "general"]
Skill = Literal["writing", "speaking", "reading", "listening"]
WritingTask = Literal["task1", "task2"]
SpeakingTask = Literal["part1", "part2", "part3", "full"]
ObjectiveTask = Literal["set", "drill"]
JobStatus = Literal["queued", "running", "completed", "failed"]


class WritingEvaluationCreate(BaseModel):
    module: Module
    task: WritingTask
    prompt: str = Field(min_length=10, max_length=4000)
    essay: str = Field(min_length=20, max_length=8000)
    parent_attempt_id: str | None = None
    study_item_id: str | None = None
    bank_item_id: str | None = None


class SpeakingEvaluationCreate(BaseModel):
    module: Module = "academic"
    task: SpeakingTask
    prompt: str = Field(min_length=5, max_length=4000)
    transcript: str | None = Field(default=None, max_length=12000)


class ObjectiveEvaluationCreate(BaseModel):
    content_set_id: str
    module: Module | Literal["shared"] = "academic"
    mode: Literal["exam", "practice"] = "practice"
    answers: dict[str, Any]
    mock_session_id: str | None = None


class EvaluationSummary(BaseModel):
    id: str
    skill: str
    module: str
    task: str
    status: str
    error: str | None
    overall_band: float | None = None
    stage: str | None = None
    created_at: str


class EvaluationDetail(EvaluationSummary):
    prompt: str | None = None
    input_text: str | None = None
    transcript: str | None = None
    speaking_mode: str | None = None
    attempt_id: str | None = None
    report: dict[str, Any] | None = None


class ProgressPoint(BaseModel):
    attempt_id: str
    skill: str
    module: str
    task: str
    overall_band: float
    created_at: str


class SkillBreakdown(BaseModel):
    skill: str
    average_band: float | None
    attempt_count: int
    latest_band: float | None


class ProgressSummary(BaseModel):
    target_band: float | None
    latest_overall: float | None
    attempt_count: int
    series: list[ProgressPoint]
    skills: list[SkillBreakdown]
    next_focus: str | None = None
    overall_estimate: float | None = None
    overall_confidence: float | None = None
    missing_skills: list[str] = []
    type_accuracy: dict[str, Any] = {}


class StudyPlanItemOut(BaseModel):
    id: str
    title: str
    detail: str
    skill_focus: str
    status: str
    drill_prompt: str | None = None
    drill_task: str | None = None
    drill_skill: str | None = None
    created_at: str


class StudyPlanUpdate(BaseModel):
    status: Literal["pending", "done", "in_progress"]


class RevisionRequest(BaseModel):
    span: str | None = Field(default=None, max_length=2000)


class DrillStartResponse(BaseModel):
    study_item_id: str
    skill: str
    task: str
    prompt: str
