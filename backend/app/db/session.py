from collections.abc import Generator

from sqlalchemy import Engine, event
from sqlmodel import Session, create_engine

from app.core.config import settings


def create_db_engine(database_url: str, *, echo: bool = False) -> Engine:
    engine = create_engine(database_url, echo=echo)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_db_engine(settings.database_url, echo=False)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
