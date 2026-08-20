"""Add content item bank, explanation cache, and mock sessions.

Revision ID: 003_content_bank
Revises: 002_coach_loop
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_content_bank"
down_revision: Union[str, None] = "002_coach_loop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("skill", sa.String(20), nullable=False, index=True),
        sa.Column("module", sa.String(20), nullable=False, index=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("time_limit_sec", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="draft", index=True),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "passages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_sets.id"), index=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False),
    )
    op.create_table(
        "audio_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_sets.id"), index=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("section_label", sa.String(40), nullable=False, server_default="section1"),
        sa.Column("uri", sa.String(500), nullable=False),
        sa.Column("duration_sec", sa.Float(), nullable=False, server_default="0"),
        sa.Column("accent", sa.String(20), nullable=False, server_default="en-GB"),
        sa.Column("transcript", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_sets.id"), index=True),
        sa.Column("passage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("audio_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("qtype", sa.String(40), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("skill_tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("marks", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("word_limit", sa.Integer(), nullable=True),
    )
    op.create_table(
        "answer_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questions.id"), unique=True, index=True),
        sa.Column("canonical", sa.String(500), nullable=False),
        sa.Column("acceptable_variants", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("normalization", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("multi_blank", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "explanation_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("wrong_normalized", sa.String(500), nullable=False, server_default=""),
        sa.Column("explanation", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("model", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "mock_blueprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("module", sa.String(20), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("listening_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reading_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("writing_task1_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("writing_task2_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("speaking_cues", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="published"),
    )
    op.create_table(
        "mock_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True),
        sa.Column("blueprint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("module", sa.String(20), nullable=False, server_default="academic"),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress", index=True),
        sa.Column("current_skill", sa.String(20), nullable=False, server_default="listening"),
        sa.Column("job_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("skill_bands", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("overall_band", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("mock_sessions")
    op.drop_table("mock_blueprints")
    op.drop_table("explanation_cache")
    op.drop_table("answer_keys")
    op.drop_table("questions")
    op.drop_table("audio_assets")
    op.drop_table("passages")
    op.drop_table("content_sets")
