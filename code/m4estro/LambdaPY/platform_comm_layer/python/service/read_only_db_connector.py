from sqlalchemy.orm import Session
from typing import Iterator
from contextlib import contextmanager

from service.db_connector import DBConnector

class ReadOnlyDBConnector(DBConnector):
    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session: Session = self._SessionLocal()
        try:
            yield session
        finally:
            session.close()