from typing import Any

from pydantic import BaseModel, Field


class ContentSetSummary(BaseModel):
    id: str
    skill: str
    module: str
    slug: str
    title: str
    difficulty: str
    time_limit_sec: int
    question_count: int
    review_status: str
    kind: str = "exam"


class PassageOut(BaseModel):
    id: str
    order_index: int
    title: str
    body: str


class AudioOut(BaseModel):
    id: str
    order_index: int
    section_label: str
    url: str
    duration_sec: float
    accent: str
    transcript: str | None = None


class QuestionOut(BaseModel):
    id: str
    number: int
    qtype: str
    stem: str
    options: dict[str, Any]
    skill_tags: list[str]
    marks: int
    word_limit: int | None
    passage_id: str | None = None
    audio_asset_id: str | None = None


class ContentSetDetail(ContentSetSummary):
    passages: list[PassageOut]
    audio_assets: list[AudioOut]
    questions: list[QuestionOut]


class ObjectiveEvaluationCreate(BaseModel):
    content_set_id: str
    module: str = "academic"
    mode: str = Field(default="practice", pattern="^(exam|practice)$")
    answers: dict[str, Any]


class NextPaperOut(BaseModel):
    id: str | None = None
    skill: str
    module: str
    task: str
    slug: str = ""
    title: str = ""
    prompt: str = ""
    source: str = "curated"
    generated: bool = False
    recycled: bool = False
    remaining: int = 0
    completed: int = 0
    total: int = 0
    visual: dict[str, Any] | None = None
    speaking: dict[str, Any] | None = None


class NextSetOut(BaseModel):
    id: str | None = None
    title: str = ""
    remaining: int = 0
    completed: int = 0
    total: int = 0
    recycled: bool = False
    completed_ids: list[str] = Field(default_factory=list)


class MockBlueprintOut(BaseModel):
    id: str
    module: str
    title: str
    listening_set_id: str | None
    reading_set_id: str | None
    writing_task1_prompt: str = ""
    writing_task2_prompt: str = ""
    speaking_cues: dict[str, Any] = Field(default_factory=dict)


class MockSessionCreate(BaseModel):
    module: str = "academic"
    blueprint_id: str | None = None


class MockSessionOut(BaseModel):
    id: str
    module: str
    status: str
    current_skill: str
    job_ids: dict[str, Any]
    skill_bands: dict[str, Any]
    overall_band: float | None
    confidence: float | None
    blueprint: MockBlueprintOut | None = None
