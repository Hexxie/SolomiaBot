import os
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
DBNAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"

Base = declarative_base()

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0, 
        "ssl": ssl_context,
      },
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def test_connection():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = list(result)[0][0]
            print(f"✅ Connected successfully! PostgreSQL version: {version}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")