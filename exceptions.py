import functools
import sqlite3


class RepositoryError(Exception):
    """Ошибка доступа к данным."""


class ConstraintViolationError(RepositoryError):
    """Нарушение ограничений БД."""


def handle_db_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        # наши ошибки не трогаем
        except RepositoryError:
            raise

        # ошибки ограничений (UNIQUE, FK, CHECK)
        except sqlite3.IntegrityError as e:
            raise ConstraintViolationError("Нарушены ограничения БД") from e

        # все остальные ошибки SQLite
        except sqlite3.Error as e:
            raise RepositoryError("Ошибка доступа к данным") from e

    return wrapper
