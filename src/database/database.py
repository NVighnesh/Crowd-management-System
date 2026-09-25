import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).resolve().parent / "schema_postgresql.sql"


def postgres_timestamp(value):
    """Normalize API ISO-8601 values before binding them to TIMESTAMPTZ."""
    if not isinstance(value, str):
        return value
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class Database:
    """Small PostgreSQL adapter used by repositories.

    Each operation owns a connection so repository calls remain independent.
    Multi-statement workflows can use :meth:`transaction` to share one
    connection and commit or roll back atomically.
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("CROWD_DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "CROWD_DATABASE_URL is required for the PostgreSQL database."
            )

    def get_connection(self):
        return psycopg.connect(
            self.database_url,
            row_factory=dict_row,
            autocommit=False,
        )

    def initialize(self):
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                for statement in schema.split(";"):
                    statement = statement.strip()
                    if statement:
                        cursor.execute(statement)
                # Upgrade databases created by the former PostgreSQL schema,
                # which represented boolean flags as integer columns.
                for table, column in (
                    ("users", "active"),
                    ("cameras", "enabled"),
                    ("cameras", "loop"),
                    ("alerts", "active"),
                    ("alerts", "resolved"),
                ):
                    column_type = cursor.execute(
                        """
                        SELECT data_type
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = %s
                          AND column_name = %s
                        """,
                        (table, column),
                    ).fetchone()
                    if column_type and column_type["data_type"] == "integer":
                        cursor.execute(
                            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP DEFAULT'
                        )
                        cursor.execute(
                            f"""
                            ALTER TABLE "{table}" ALTER COLUMN "{column}"
                            TYPE BOOLEAN USING "{column}" <> 0
                            """
                        )
                        cursor.execute(
                            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT TRUE'
                        )
                cursor.execute(
                    'ALTER TABLE cameras ALTER COLUMN owner_id DROP DEFAULT'
                )
                cursor.execute(
                    'ALTER TABLE cameras ALTER COLUMN owner_id DROP NOT NULL'
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _validate_query(query: str) -> str:
        if "?" in query:
            raise ValueError(
                "PostgreSQL queries must use %s placeholders, not ?."
            )
        return query

    def execute(self, query: str, parameters: tuple = ()):
        for attempt in range(4):
            connection = self.get_connection()
            try:
                cursor = connection.execute(
                    self._validate_query(query),
                    parameters,
                )
                connection.commit()
                return cursor
            except psycopg.OperationalError:
                connection.rollback()
                if attempt == 3:
                    raise
                time.sleep(0.05 * (attempt + 1))
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def execute_insert_returning_id(
        self,
        query: str,
        parameters: tuple = (),
    ):
        connection = self.get_connection()
        try:
            cursor = connection.execute(
                self._validate_query(query) + " RETURNING id",
                parameters,
            )
            row = cursor.fetchone()
            connection.commit()
            return row["id"]
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def fetch_one(self, query: str, parameters: tuple = ()):
        connection = self.get_connection()
        try:
            row = connection.execute(
                self._validate_query(query),
                parameters,
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            connection.close()

    def fetch_all(self, query: str, parameters: tuple = ()):
        connection = self.get_connection()
        try:
            rows = connection.execute(
                self._validate_query(query),
                parameters,
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def close(self):
        """Compatibility no-op; connections are scoped to operations."""

    @contextmanager
    def transaction(self):
        connection = self.get_connection()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
