"""Seed a demo student. Run: python -m app.seed"""

import asyncio

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


async def seed() -> None:
    async with SessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == "demo@northband.app"))
        if existing:
            print("Demo user already exists: demo@northband.app / demo12345")
            return
        db.add(
            User(
                email="demo@northband.app",
                password_hash=hash_password("demo12345"),
                display_name="Amina Rahman",
                target_band=7.0,
                preferred_module="academic",
            )
        )
        await db.commit()
        print("Created demo user: demo@northband.app / demo12345")


if __name__ == "__main__":
    asyncio.run(seed())
