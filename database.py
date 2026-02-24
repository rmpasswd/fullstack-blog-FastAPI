from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DB_URL_SQLITE = "sqlite+aiosqlite:///./blog.db"

engine = create_async_engine(DB_URL_SQLITE, connect_args={"check_same_thread": False},)


# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession,  expire_on_commit=False)
#when an object expires(after commit), sqlite tryies to reload it lazily. But async sqlite does not support lazy loads, hence expire_on_commit=False


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as db_session:
        yield db_session

