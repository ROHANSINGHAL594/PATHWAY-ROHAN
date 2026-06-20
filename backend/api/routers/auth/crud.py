from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .utils import get_password_hash
from .models import User
from typing import List

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_all_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User).where(User.is_active == True))
    return result.scalars().all()

async def create_user(db: AsyncSession, data):
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name or "",
        is_active=True,
        created_at=datetime.utcnow(),
        role="user"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
