import json

from sqlalchemy import Engine, text
from sqlmodel import SQLModel

from app.db import models  # noqa: F401
from app.db.session import engine
from app.services.sourcing import default_job_search_channels


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
            "search_channels": "JSON NOT NULL DEFAULT '[]'",
        },
        "reviewjob": {
            "input_path": "VARCHAR",
            "output_path": "VARCHAR",
        },
    }
    with db_engine.begin() as connection:
        existing_tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            ).all()
        }
        for table_name, required_columns in required_columns_by_table.items():
            if table_name not in existing_tables:
                continue
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
        existing_jobs = connection.execute(
            text("SELECT id, title, description, search_channels FROM job")
        ).all()
        for job_id, title, description, search_channels in existing_jobs:
            if search_channels not in (None, "", "[]"):
                continue
            connection.execute(
                text("UPDATE job SET search_channels = :search_channels WHERE id = :job_id"),
                {
                    "job_id": job_id,
                    "search_channels": (
                        '["' + '","'.join(default_job_search_channels(title, description)) + '"]'
                    ),
                },
            )
        if {"searchrun", "job"}.issubset(existing_tables):
            existing_search_runs = connection.execute(
                text(
                    """
                    SELECT searchrun.id, searchrun.metadata, job.title, job.description, job.search_channels
                    FROM searchrun
                    JOIN job ON job.id = searchrun.job_id
                    """
                )
            ).all()
            for search_run_id, metadata_payload, job_title, job_description, job_search_channels in (
                existing_search_runs
            ):
                metadata = (
                    json.loads(metadata_payload)
                    if isinstance(metadata_payload, str) and metadata_payload
                    else metadata_payload
                )
                if not isinstance(metadata, dict):
                    metadata = {}
                if metadata.get("channels"):
                    continue
                channels = (
                    json.loads(job_search_channels)
                    if isinstance(job_search_channels, str) and job_search_channels
                    else job_search_channels
                )
                metadata["channels"] = channels or default_job_search_channels(
                    job_title, job_description
                )
                connection.execute(
                    text("UPDATE searchrun SET metadata = :metadata WHERE id = :search_run_id"),
                    {"search_run_id": search_run_id, "metadata": json.dumps(metadata)},
                )


if __name__ == "__main__":
    init_db()
