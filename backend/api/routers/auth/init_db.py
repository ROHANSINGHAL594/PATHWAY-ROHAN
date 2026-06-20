"""
Script to initialize the database and create tables.
Run this once to set up the users table.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from database import get_engine, Base

load_dotenv()

async def init_db():
    """Create all tables in the database"""
    try:
        engine = get_engine()
        print("Connecting to PostgreSQL...")
        async with engine.begin() as conn:
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✓ Tables created successfully!")
            print("✓ Users table is ready!")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. Environment variables are set correctly:")
        print("     - POSTGRES_HOST")
        print("     - POSTGRES_PORT")
        print("     - POSTGRES_DB")
        print("     - POSTGRES_USER")
        print("     - POSTGRES_PASSWORD")
        raise

if __name__ == "__main__":
    asyncio.run(init_db())

