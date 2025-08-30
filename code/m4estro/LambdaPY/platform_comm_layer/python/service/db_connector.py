from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Iterator

class DBConnector:
    def __init__(self, db_url: str) -> None:
        self._engine = create_engine(db_url, pool_pre_ping=True, future=True)
        self._SessionLocal = sessionmaker(bind=self._engine, future=True, expire_on_commit=False)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self):
        self._engine.dispose()
