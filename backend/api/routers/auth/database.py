import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
from fastapi import HTTPException, status, WebSocketException


load_dotenv()
# Database URL construction
def get_database_url():
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "db")
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "admin123")
    
    # Use asyncpg for async PostgreSQL
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"

# Create async engine (lazy initialization)
_engine = None
_AsyncSessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_async_engine(
            database_url,
            echo=False,
            future=True
        )
    return _engine

def get_session_factory():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _AsyncSessionLocal

# Module-level accessors (for backward compatibility where needed)
# Note: Use get_engine() and get_session_factory() directly in new code

# Base class for models
class Base(DeclarativeBase):
    pass

# Dependency to get database session
async def get_db():
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()
    except HTTPException:
        # Re-raise HTTPExceptions without wrapping them
        raise
    except WebSocketException:
        raise
    except Exception as e:
        # Only wrap actual database connection errors
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}"
        )

