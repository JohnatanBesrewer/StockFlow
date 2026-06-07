import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
import os


class Database:
    """Минималистичная, предсказуемая и полностью контролируемая обёртка над SQLite."""

    def __init__(
        self,
        db_path: str | os.PathLike[str],
        timeout: float = 5.0,
        create_if_missing: bool = True,
    ) -> None:
        self._db_path = Path(db_path)
        self._timeout = timeout

        if not create_if_missing and not self._db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self._db_path}")

        # Настраиваем постоянные параметры БД (WAL, synchronous)
        self._ensure_global_settings()

    def _connect(self) -> sqlite3.Connection:
        """Создаёт соединение с базой.

        isolation_level=None → ручное управление транзакциями через commit()/rollback()
        """
        conn = sqlite3.connect(
            self._db_path,
            timeout=self._timeout,
            check_same_thread=False,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_global_settings(self) -> None:
        """Настройка WAL и синхронизации для всего файла БД."""
        conn = sqlite3.connect(self._db_path, timeout=self._timeout)
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        finally:
            conn.close()

    @contextmanager
    def read_connection(self) -> Iterator[sqlite3.Connection]:
        """Контекст для чтения (SELECT) без транзакций."""
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Контекст для изменения данных (INSERT/UPDATE/DELETE)."""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE;")  # стартуем транзакцию
            try:
                yield conn
            except Exception:
                conn.rollback()  # откат при ошибке
                raise
            else:
                conn.commit()  # коммит, если всё успешно
        finally:
            conn.close()

    def init_schema(self, schema_path: str | os.PathLike[str]) -> None:
        """Выполняет SQL-скрипт для создания структуры таблиц.

        Использует executescript отдельно, чтобы избежать конфликтов транзакций.
        """
        schema_sql = Path(schema_path).read_text(encoding="utf-8")
        conn = self._connect()
        try:
            conn.executescript(schema_sql)
        finally:
            conn.close()


if __name__ == "__main__":
    raise RuntimeError("This module is not intended to be run directly")

db = Database("storage.db")
db.init_schema("schema.sql")
