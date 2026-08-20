"""Add coach profile, job stage, parent attempts, and drill fields.

Revision ID: 002_coach_loop
Revises: 001_initial
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_coach_loop"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("coach_profile", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("evaluation_jobs", sa.Column("stage", sa.String(40), nullable=True))
    op.add_column(
        "evaluation_jobs",
        sa.Column("partial_report", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("attempts", sa.Column("parent_attempt_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("study_plan_items", sa.Column("drill_prompt", sa.Text(), nullable=True))
    op.add_column("study_plan_items", sa.Column("drill_task", sa.String(20), nullable=True))
    op.add_column("study_plan_items", sa.Column("drill_skill", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("study_plan_items", "drill_skill")
    op.drop_column("study_plan_items", "drill_task")
    op.drop_column("study_plan_items", "drill_prompt")
    op.drop_column("attempts", "parent_attempt_id")
    op.drop_column("evaluation_jobs", "partial_report")
    op.drop_column("evaluation_jobs", "stage")
    op.drop_column("users", "coach_profile")
