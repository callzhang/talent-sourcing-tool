from sqlalchemy import Engine, text
from sqlmodel import SQLModel

from app.db import models  # noqa: F401
from app.db.session import engine


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    migrate_existing_sqlite_schema(engine)


def migrate_existing_sqlite_schema(db_engine: Engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return

    required_columns_by_table = {
        "job": {
            "target_profile_text": "TEXT NOT NULL DEFAULT ''",
            "red_flags_text": "TEXT NOT NULL DEFAULT ''",
            "search_notes": "TEXT NOT NULL DEFAULT ''",
        },
        "reviewjob": {
            "input_path": "VARCHAR",
            "output_path": "VARCHAR",
        },
    }
    with db_engine.begin() as connection:
        for table_name, required_columns in required_columns_by_table.items():
            existing_columns = {
                row[1]
                for row in connection.execute(text(f"PRAGMA table_info({table_name})")).all()
            }
            for column_name, column_definition in required_columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ADD COLUMN {column_name} {column_definition}"
                        )
                    )


if __name__ == "__main__":
    init_db()
