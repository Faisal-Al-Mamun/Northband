from typing import Literal

from pydantic import BaseModel, Field


class EvidenceNote(BaseModel):
    quote: str = Field(min_length=1, max_length=500)
    comment: str = Field(min_length=1, max_length=600)


class CriterionAnalysis(BaseModel):
    criterion: str
    proposed_band: float = Field(ge=0, le=9)
    summary: str
    evidence: list[EvidenceNote] = Field(default_factory=list)


class WritingAgentOutput(BaseModel):
    task_response: CriterionAnalysis
    coherence: CriterionAnalysis
    lexical: CriterionAnalysis
    grammar: CriterionAnalysis
    word_count: int = Field(ge=0)
    task_fit_notes: str


class SpeakingAgentOutput(BaseModel):
    fluency: CriterionAnalysis
    lexical: CriterionAnalysis
    grammar: CriterionAnalysis
    pronunciation: CriterionAnalysis
    mode: Literal["audio", "text"]
    words_per_minute: float | None = None
    duration_seconds: float | None = None


class GrammarIssue(BaseModel):
    span: str
    issue_type: str
    correction: str
    explanation: str
    cefr_tag: str | None = None


class GrammarAgentOutput(BaseModel):
    issues: list[GrammarIssue] = Field(default_factory=list)
    recurring_patterns: list[str] = Field(default_factory=list)
    lexical_range_notes: str
    vocabulary_upgrades: list[str] = Field(default_factory=list)


class BandCriterion(BaseModel):
    criterion: str
    band: float
    rationale: str


class BandScoreOutput(BaseModel):
    criteria: list[BandCriterion]
    overall_band: float
    confidence: float = Field(ge=0, le=1)
    scoring_notes: str


class StudyAction(BaseModel):
    title: str
    detail: str
    skill_focus: str
    drill_prompt: str = ""
    drill_task: str = "task2"


class FeedbackAgentOutput(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    actions: list[StudyAction]
    examiner_summary: str


class TrendPoint(BaseModel):
    label: str
    direction: Literal["up", "down", "flat"]
    note: str


class PerformanceAgentOutput(BaseModel):
    trends: list[TrendPoint]
    plateau: bool
    next_focus: str
    comparison_note: str


class RevisionAgentOutput(BaseModel):
    original_span: str
    rewritten: str
    changes: list[str] = Field(default_factory=list)
    target_band: float = Field(ge=0, le=9)
    notes: str


class CoachStepOutput(BaseModel):
    thought: str
    action: str = Field(
        description="list_misses | inspect_item | quote_context | note_explanation | finish"
    )
    question_id: str = ""
    query: str = ""
    trap_type: str = ""
    explanation: str = ""
    tip: str = ""
    skill_tag: str = ""
