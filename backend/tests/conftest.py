import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import models
from app.services import payment_confirmation


@pytest.fixture(autouse=True)
def isolated_test_database(tmp_path, monkeypatch):
    database_file = tmp_path / "test_payments.db"

    test_engine = create_engine(
        f"sqlite:///{database_file}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=test_engine)

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        payment_confirmation,
        "SessionLocal",
        TestSessionLocal,
    )

    yield

    test_engine.dispose()
