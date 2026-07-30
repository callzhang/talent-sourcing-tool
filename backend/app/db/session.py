from collections.abc import Generator

from sqlalchemy import Engine, event
from sqlmodel import Session, create_engine

from app.core.config import settings


def create_db_engine(
    database_url: str,
    *,
    echo: bool = False,
    turso_auth_token: str = "",
) -> Engine:
    connect_args: dict[str, str] = {}
    engine_url = database_url

    if database_url.startswith("libsql://"):
        if not turso_auth_token:
            raise RuntimeError("TURSO_AUTH_TOKEN is required when TURSO_DATABASE_URL is configured.")
        engine_url = f"sqlite+{database_url}?secure=true"
        connect_args["auth_token"] = turso_auth_token

    engine = create_engine(engine_url, echo=echo, connect_args=connect_args)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_db_engine(
    settings.database_url,
    echo=False,
    turso_auth_token=settings.turso_auth_token,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
