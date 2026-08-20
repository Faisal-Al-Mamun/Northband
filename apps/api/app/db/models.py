import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uuid_pk() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    target_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_module: Mapped[str] = mapped_column(String(20), default="academic")
    coach_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs: Mapped[list["EvaluationJob"]] = relationship(back_populates="user")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="user")
    study_plan_items: Mapped[list["StudyPlanItem"]] = relationship(back_populates="user")


class EvaluationJob(Base):
    __tablename__ = "evaluation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    skill: Mapped[str] = mapped_column(String(20))
    module: Mapped[str] = mapped_column(String(20))
    task: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    partial_report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="jobs")
    attempt: Mapped["Attempt | None"] = relationship(back_populates="job", uselist=False)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_jobs.id"), unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    skill: Mapped[str] = mapped_column(String(20), index=True)
    module: Mapped[str] = mapped_column(String(20), index=True)
    task: Mapped[str] = mapped_column(String(20))
    prompt: Mapped[str] = mapped_column(Text)
    bank_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    speaking_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    overall_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    parent_attempt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[EvaluationJob] = relationship(back_populates="attempt")
    user: Mapped[User] = relationship(back_populates="attempts")
    scores: Mapped[list["CriterionScore"]] = relationship(back_populates="attempt")


class CriterionScore(Base):
    __tablename__ = "criterion_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id"), index=True
    )
    criterion: Mapped[str] = mapped_column(String(80))
    band: Mapped[float] = mapped_column(Float)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempt: Mapped[Attempt] = relationship(back_populates="scores")


class StudyPlanItem(Base):
    __tablename__ = "study_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    skill_focus: Mapped[str] = mapped_column(String(40))
    drill_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    drill_task: Mapped[str | None] = mapped_column(String(20), nullable=True)
    drill_skill: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="study_plan_items")


class LlmCallLog(Base):
    __tablename__ = "llm_call_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    agent: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    latency_ms: Mapped[int] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentSet(Base):
    __tablename__ = "content_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    skill: Mapped[str] = mapped_column(String(20), index=True)
    module: Mapped[str] = mapped_column(String(20), index=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    time_limit_sec: Mapped[int] = mapped_column(Integer, default=3600)
    version: Mapped[int] = mapped_column(Integer, default=1)
    review_status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    passages: Mapped[list["Passage"]] = relationship(back_populates="content_set")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="content_set")
    questions: Mapped[list["Question"]] = relationship(back_populates="content_set")


class Passage(Base):
    __tablename__ = "passages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    content_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_sets.id"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text)

    content_set: Mapped[ContentSet] = relationship(back_populates="passages")


class AudioAsset(Base):
    __tablename__ = "audio_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    content_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_sets.id"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=1)
    section_label: Mapped[str] = mapped_column(String(40), default="section1")
    uri: Mapped[str] = mapped_column(String(500))
    duration_sec: Mapped[float] = mapped_column(Float, default=0)
    accent: Mapped[str] = mapped_column(String(20), default="en-GB")
    transcript: Mapped[str] = mapped_column(Text, default="")

    content_set: Mapped[ContentSet] = relationship(back_populates="audio_assets")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    content_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_sets.id"), index=True
    )
    passage_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    audio_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=1)
    number: Mapped[int] = mapped_column(Integer, default=1)
    qtype: Mapped[str] = mapped_column(String(40))
    stem: Mapped[str] = mapped_column(Text)
    options: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    skill_tags: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    marks: Mapped[int] = mapped_column(Integer, default=1)
    word_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    content_set: Mapped[ContentSet] = relationship(back_populates="questions")
    answer_key: Mapped["AnswerKey | None"] = relationship(back_populates="question", uselist=False)


class AnswerKey(Base):
    __tablename__ = "answer_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id"), unique=True, index=True
    )
    canonical: Mapped[str] = mapped_column(String(500))
    acceptable_variants: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    normalization: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    multi_blank: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    key_version: Mapped[int] = mapped_column(Integer, default=1)

    question: Mapped[Question] = relationship(back_populates="answer_key")


class ExplanationCache(Base):
    __tablename__ = "explanation_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    key_version: Mapped[int] = mapped_column(Integer, default=1)
    wrong_normalized: Mapped[str] = mapped_column(String(500), default="")
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    model: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromptItem(Base):
    __tablename__ = "prompt_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    skill: Mapped[str] = mapped_column(String(20), index=True)
    module: Mapped[str] = mapped_column(String(20), index=True)
    task: Mapped[str] = mapped_column(String(20), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    prompt: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    source: Mapped[str] = mapped_column(String(20), default="curated")
    review_status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MockBlueprint(Base):
    __tablename__ = "mock_blueprints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    module: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(255))
    listening_set_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reading_set_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    writing_task1_prompt: Mapped[str] = mapped_column(Text, default="")
    writing_task2_prompt: Mapped[str] = mapped_column(Text, default="")
    speaking_cues: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    review_status: Mapped[str] = mapped_column(String(20), default="published")


class MockSession(Base):
    __tablename__ = "mock_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    blueprint_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    module: Mapped[str] = mapped_column(String(20), default="academic")
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    current_skill: Mapped[str] = mapped_column(String(20), default="listening")
    job_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    skill_bands: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    overall_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
