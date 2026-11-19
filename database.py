import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


class Database:
    """Минималистичная обёртка над SQLite."""

    def __init__(
        self,
        db_path: str | os.PathLike[str],
        timeout: float = 5.0,
        create_if_missing: bool = True,
    ) -> None:
        self._db_path = Path(db_path)
        self._timeout = timeout

        if not create_if_missing and not self._db_path.exists():
            raise FileNotFoundError(
                f"Database file not found: {self._db_path}"
            )

        self._ensure_global_settings()

    def _connect(self) -> sqlite3.Connection:
        """Создаёт и настраивает новое соединение."""

        conn = sqlite3.connect(
            self._db_path,
            timeout=self._timeout,
            isolation_level=None,
        )

        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        except BaseException:
            conn.close()
            raise

        return conn

    def _ensure_global_settings(self) -> None:
        """Настраивает постоянный режим журналирования WAL."""

        conn = sqlite3.connect(
            self._db_path,
            timeout=self._timeout,
            isolation_level=None,
        )

        try:
            result = conn.execute(
                "PRAGMA journal_mode = WAL;"
            ).fetchone()

            if result is None or result[0].lower() != "wal":
                raise RuntimeError(
                    "Failed to enable SQLite WAL mode"
                )
        finally:
            conn.close()

    @contextmanager
    def read_connection(
        self,
    ) -> Generator[sqlite3.Connection, None, None]:
        """Контекст для выполнения операций чтения."""

        conn = self._connect()

        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(
        self,
    ) -> Generator[sqlite3.Connection, None, None]:
        """Контекст транзакции записи."""

        conn = self._connect()

        try:
            conn.execute("BEGIN IMMEDIATE;")

            try:
                yield conn
                conn.commit()

            except BaseException:
                if conn.in_transaction:
                    conn.rollback()
                raise

        finally:
            conn.close()

    def init_schema(
        self,
        schema_path: str | os.PathLike[str],
    ) -> None:
        """Атомарно выполняет SQL-скрипт создания схемы."""

        schema_sql = Path(schema_path).read_text(
            encoding="utf-8"
        )

        conn = self._connect()

        try:
            try:
                conn.executescript(
                    "BEGIN IMMEDIATE;\n"
                    + schema_sql
                    + "\nCOMMIT;"
                )

            except BaseException:
                if conn.in_transaction:
                    conn.rollback()
                raise

        finally:
            conn.close()


if __name__ == "__main__":
    raise RuntimeError(
        "This module is not intended to be run directly"
    )


# db = Database("storage.db")
# db.init_schema("schema.sql")
