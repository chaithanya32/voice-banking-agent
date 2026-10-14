
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parent.parent / "voice_banking.db"
)

DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH))
).expanduser().resolve()

# Create the parent directory when needed.
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass
