from sqlalchemy import text

from app.db.session import engine

STATEMENTS = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS coach_profile JSONB DEFAULT '{}'::jsonb",
    "ALTER TABLE evaluation_jobs ADD COLUMN IF NOT EXISTS stage VARCHAR(40)",
    "ALTER TABLE evaluation_jobs ADD COLUMN IF NOT EXISTS partial_report JSONB DEFAULT '{}'::jsonb",
    "ALTER TABLE attempts ADD COLUMN IF NOT EXISTS parent_attempt_id UUID",
    "ALTER TABLE attempts ADD COLUMN IF NOT EXISTS bank_item_id UUID",
    "ALTER TABLE study_plan_items ADD COLUMN IF NOT EXISTS drill_prompt TEXT",
    "ALTER TABLE study_plan_items ADD COLUMN IF NOT EXISTS drill_task VARCHAR(20)",
    "ALTER TABLE study_plan_items ADD COLUMN IF NOT EXISTS drill_skill VARCHAR(20)",
)


async def ensure_optional_columns() -> None:
    async with engine.begin() as conn:
        for statement in STATEMENTS:
            await conn.execute(text(statement))
