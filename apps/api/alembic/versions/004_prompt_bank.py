"""Prompt bank items and attempt.bank_item_id.

Revision ID: 004_prompt_bank
Revises: 003_content_bank
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_prompt_bank"
down_revision: Union[str, None] = "003_content_bank"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("skill", sa.String(20), nullable=False, index=True),
        sa.Column("module", sa.String(20), nullable=False, index=True),
        sa.Column("task", sa.String(20), nullable=False, index=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source", sa.String(20), nullable=False, server_default="curated"),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="published", index=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.add_column("attempts", sa.Column("bank_item_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_attempts_bank_item_id", "attempts", ["bank_item_id"])


def downgrade() -> None:
    op.drop_index("ix_attempts_bank_item_id", table_name="attempts")
    op.drop_column("attempts", "bank_item_id")
    op.drop_table("prompt_items")
