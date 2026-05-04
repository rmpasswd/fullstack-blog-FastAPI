from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from auth.config import settings
# DB_URL_SQLITE = "sqlite+aiosqlite:///./blog.db"
# engine = create_async_engine(DB_URL_SQLITE, connect_args={"check_same_thread": False},)

import sys, asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

engine = create_async_engine(
            settings.database_url, 
            echo=True,
            connect_args={"options": "-c search_path=blogdb"} 
            #  Force alembic to use another schema 'blogdb' instead of schema 'public'. default database 'postgres' stays fixed.
        )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession,  expire_on_commit=False)
#when an object expires(after commit), sqlite tryies to reload it lazily. But async sqlite does not support lazy loads, hence expire_on_commit=False


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as db_session:
        yield db_session

