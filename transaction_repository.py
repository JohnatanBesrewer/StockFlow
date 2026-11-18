from __future__ import annotations
from uuid import UUID
import enum
import sqlite3
import datetime
from typing import Any
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import database
import entities
import validator


class TransactionRepository:
    """Репозиторий для управления транзакциями (приход/расход) и их позициями в SQLite."""

    def __init__(self, db: database.Database):
        self._db = db

    def create_transaction(self, tx: entities.Transaction) -> None:
        """
        Сохраняет новую транзакцию и связанные с ней товары в БД.
        Операция выполняется атомарно внутри одной транзакции БД:
        если запись товаров не удастся, запись самой транзакции также откатится.
        Args:
            tx: Объект транзакции с метаданными (список позиций, дата, поставщик, суммы).
        """

        sql_tx = """
        INSERT INTO transactions (
            transaction_id,
            transaction_type,
            total_amount_x100,
            discount_x100,
            comment,
            transaction_date,
            created_at,
            supplier_id,
            supplier_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        sql_item = """
        INSERT INTO transaction_items (
            item_id,
            transaction_id,
            product_id,
            product_barcode,
            product_name,
            product_unit,
            product_price_x100,
            product_quantity_x1000,
            amount_x100
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        with self._db.transaction() as conn:
            conn.execute(sql_tx, self._map_tx_params(tx))

            for item in tx.items:
                conn.execute(sql_item, self._map_item_params(item))

    def get_by_id(self, transaction_id: UUID) -> entities.Transaction | None:
        """
        Загружает полную агрегированную сущность транзакции по её UUID.
        Выполняет два запроса: один для получения заголовка транзакции,
        второй для получения всех связанных позиций (items).
        Args:
            transaction_id: Уникальный идентификатор транзакции.
        Returns:
            Объект Transaction со списком items, либо None, если транзакция не найдена.
        """
        sql_tx = """
        SELECT *
        FROM transactions
        WHERE transaction_id = ?
        """

        sql_items = """
        SELECT *
        FROM transaction_items
        WHERE transaction_id = ?
        """

        with self._db.read_connection() as conn:
            tx_row = conn.execute(sql_tx, (str(transaction_id),)).fetchone()

            if not tx_row:
                return None

            item_rows = conn.execute(
                sql_items, (str(transaction_id),)).fetchall()

        items = tuple(self._map_item(row) for row in item_rows)
        return self._map_tx(tx_row, items)

    def get_by_date(
            self,
            transaction_date: datetime.date
    ) -> list[entities.Transaction]:
        """
        Загружает все транзакции за указанную дату вместе с их позициями.
        Args: transaction_date: Дата транзакций.
        Returns: Список агрегатов Transaction.
        """

        sql_tx = """
        SELECT *
        FROM transactions
        WHERE transaction_date = ?
        """

        sql_items = """
        SELECT *
        FROM transaction_items
        WHERE transaction_id IN ({})
        """

        with self._db.read_connection() as conn:
            tx_rows = conn.execute(
                sql_tx,
                (transaction_date.isoformat(),)
            ).fetchall()

            if not tx_rows:
                return []

            tx_ids = [row["transaction_id"] for row in tx_rows]

            placeholders = ",".join("?" * len(tx_ids))

            item_rows = conn.execute(
                sql_items.format(placeholders),
                tx_ids
            ).fetchall()

        items_by_tx_id: dict[str, list] = {}

        for row in item_rows:
            item = self._map_item(row)

            items_by_tx_id.setdefault(
                row["transaction_id"],
                []
            ).append(item)

        transactions = []

        for row in tx_rows:
            items = tuple(
                items_by_tx_id.get(
                    row["transaction_id"],
                    []
                )
            )

            transactions.append(
                self._map_tx(row, items)
            )

        return transactions

    def delete(self, transaction_id: UUID) -> None:
        """
        Удаляет транзакцию из базы данных.
        Примечание: Предполагается наличие каскадного удаления (ON DELETE CASCADE)
        в схеме БД для таблицы transaction_items, чтобы автоматически удалить
        связанные позиции при удалении родительской транзакции.
        Args:
            transaction_id: Уникальный идентификатор удаляемой транзакции.
        """
        sql = """
        DELETE FROM transactions
        WHERE transaction_id = ?
        """

        with self._db.transaction() as conn:
            conn.execute(sql, (str(transaction_id),))

    @staticmethod
    def _map_tx(
        row: sqlite3.Row, items: tuple[entities.TransactionItem, ...]
    ) -> entities.Transaction:
        """
        Преобразует сырую строку результата SQL-запроса (Row) в объект доменной модели Transaction.
        Args:
            row: Строка данных из таблицы transactions.
            items: Кортеж уже маппированных объектов TransactionItem.
        Returns:
            Экземпляр класса Transaction.
        """
        return entities.Transaction(
            transaction_id=UUID(row["transaction_id"]),
            transaction_type=entities.TransactionType(row["transaction_type"]),
            discount=Decimal(row["discount_x100"]) / Decimal("100"),
            comment=row["comment"] if row["comment"] else None,
            transaction_date=datetime.date.fromisoformat(
                row["transaction_date"]),
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
            supplier_name=row["supplier_name"] if row["supplier_name"] else None,
            supplier_id=UUID(row["supplier_id"]
                             ) if row["supplier_id"] else None,
            items=items,
        )

    @staticmethod
    def _map_item(row: sqlite3.Row) -> entities.TransactionItem:
        """
        Преобразует сырую строку результата SQL-запроса в объект TransactionItem.
        Args:
            row: Строка данных из таблицы transaction_items.
        Returns:
            Экземпляр класса TransactionItem.
        """
        return entities.TransactionItem(
            item_id=UUID(row["item_id"]),
            transaction_id=UUID(row["transaction_id"]),
            product_id=UUID(row["product_id"]),
            product_barcode=row["product_barcode"],
            product_name=row["product_name"],
            product_unit=entities.Unit(row["product_unit"]),
            product_price=Decimal(row["product_price_x100"]) / Decimal("100"),
            product_quantity=Decimal(
                row["product_quantity_x1000"]) / Decimal("1000")
        )

    @staticmethod
    def _map_tx_params(tx: entities.Transaction):
        """
        Подготавливает кортеж параметров из объекта Transaction для SQL-запроса INSERT.
        Преобразует UUID в строки и обрабатывает nullable поля.
        Args:
            tx: Объект доменной модели Transaction.
        Returns:
            Кортеж значений, соответствующих плейсхолдерам в SQL-запросе.
        """
        return (
            str(tx.transaction_id),
            tx.transaction_type.value,
            int((tx.total_amount * 100).to_integral_value(rounding=ROUND_HALF_UP)),
            int((tx.discount * 100).to_integral_value(rounding=ROUND_HALF_UP)),
            tx.comment if tx.comment is not None else None,
            tx.transaction_date.isoformat(),
            tx.created_at.isoformat(),
            str(tx.supplier_id) if tx.supplier_id is not None else None,
            tx.supplier_name if tx.supplier_name is not None else None,
        )

    @staticmethod
    def _map_item_params(item: entities.TransactionItem):
        """
        Подготавливает кортеж параметров из объекта TransactionItem для SQL-запроса INSERT.
        Преобразует все поля в соответствующий формат.
        Args:
            item: Объект доменной модели TransactionItem.
        Returns:
            Кортеж значений, соответствующих плейсхолдерам в SQL-запросе.
        """
        return (
            str(item.item_id),
            str(item.transaction_id),
            str(item.product_id),
            item.product_barcode,
            item.product_name,
            item.product_unit.value,
            int(item.product_price * 100),
            int(item.product_quantity * 1000),
            int(item.amount * 100),
        )

    def find(
        self,
        filter_: TransactionFilter,
    ) -> list[TransactionSummary]:
        """
        Находит транзакции, удовлетворяющие фильтру.

        Условия WHERE собираются по каждому полю фильтра независимо
        и объединяются через AND. Результат сортируется по дате
        транзакции и времени создания (новые — первыми).
        """

        sql = """
            SELECT
                transaction_id,
                transaction_type,
                total_amount_x100,
                discount_x100,
                comment,
                transaction_date,
                created_at,
                supplier_id,
                supplier_name
            FROM transactions
        """

        # Части WHERE-условия и соответствующие им параметры
        # собираются параллельно, чтобы порядок "?" совпадал
        # с порядком params при финальной подстановке.
        conditions: list[str] = []
        params: list[Any] = []

        self._append_in_condition(
            conditions,
            params,
            "transaction_id",
            filter_.transaction_ids,
        )

        self._append_in_condition(
            conditions,
            params,
            "transaction_type",
            filter_.transaction_types,
        )

        self._append_in_condition(
            conditions,
            params,
            "supplier_id",
            filter_.supplier_ids,
        )

        self._append_range_condition(
            conditions,
            params,
            "total_amount_x100",
            filter_.total_amount,
        )

        self._append_range_condition(
            conditions,
            params,
            "discount_x100",
            filter_.discount,
        )

        self._append_range_condition(
            conditions,
            params,
            "transaction_date",
            filter_.transaction_date,
        )

        self._append_comment_condition(
            conditions,
            filter_.comment_present,
        )

        # WHERE добавляется только если есть хотя бы одно условие —
        # иначе запрос просто вернёт все строки.
        if conditions:
            sql += "\nWHERE " + "\nAND ".join(conditions)

        sql += """
            ORDER BY
                transaction_date DESC,
                created_at DESC
        """

        # Соединение только на чтение — репозиторий не модифицирует данные.
        with self._db.read_connection() as conn:
            rows = conn.execute(
                sql,
                params,
            ).fetchall()

        return [
            self._row_to_summary(row)
            for row in rows
        ]

    @staticmethod
    def _append_in_condition[T](
        conditions: list[str],
        params: list[Any],
        column: str,
        values: tuple[T, ...],
    ) -> None:
        """
        Добавляет условие `column IN (?, ?, ...)`, если values не пуст.

        Значения передаются как параметризованные плейсхолдеры
        (защита от SQL-инъекций), а не как строковая конкатенация.
        """

        if not values:
            return

        placeholders = ", ".join(
            "?" for _ in values
        )

        conditions.append(
            f"{column} IN ({placeholders})"
        )

        params.extend(TransactionRepository._prepare_value_for_db(value)
                      for value in values)

    @staticmethod
    def _append_range_condition[T](
        conditions: list[str],
        params: list[Any],
        column: str,
        value: RangeFilter[T] | None,
    ) -> None:
        """
        Добавляет условие для колонки на основе RangeFilter.
        """
        if value is None or value.is_empty():
            return

        if (
            value.minimum is not None
            and value.maximum is not None
            and value.minimum == value.maximum
        ):
            conditions.append(
                f"{column} = ?"
            )
            params.append(
                TransactionRepository._prepare_value_for_db(
                    value.minimum
                )
            )
            return

        if value.minimum is not None:
            conditions.append(
                f"{column} >= ?"
            )
            params.append(
                TransactionRepository._prepare_value_for_db(
                    value.minimum
                )
            )

        if value.maximum is not None:
            conditions.append(
                f"{column} <= ?"
            )
            params.append(
                TransactionRepository._prepare_value_for_db(
                    value.maximum
                )
            )

    @staticmethod
    def _append_comment_condition(
        conditions: list[str],
        comment_present: bool | None,
    ) -> None:
        """
        Добавляет условие фильтрации по наличию комментария.

        NULL и пустая строка трактуются одинаково — как
        "комментарий отсутствует".
        """

        if comment_present is True:
            conditions.append(
                "(comment IS NOT NULL AND comment != '')"
            )

        elif comment_present is False:
            conditions.append(
                "(comment IS NULL OR comment = '')"
            )

    @staticmethod
    def _row_to_summary(row: sqlite3.Row) -> TransactionSummary:
        return TransactionSummary(
            transaction_id=validator.validate_id(row["transaction_id"]),
            transaction_type=entities.TransactionType(row["transaction_type"]),
            transaction_date=datetime.date.fromisoformat(
                row["transaction_date"]),
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
            total_amount=Decimal(row["total_amount_x100"]) / Decimal("100"),
            discount=Decimal(row["discount_x100"]) / Decimal("100"),
            comment=row["comment"],
            supplier_id=(
                validator.validate_id(row["supplier_id"])
                if row["supplier_id"]
                else None
            ),
            supplier_name=(
                row["supplier_name"] if row["supplier_name"] else None
            ),
        )

    @staticmethod
    def _prepare_value_for_db[T](value: T) -> Any:
        """
        Преобразует значения бизнес-логики
        в значения, пригодные для SQLite.
        """

        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()

        if isinstance(value, Decimal):
            return int(value * 100)

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, enum.Enum):
            return value.value

        return value


@dataclass(frozen=True, slots=True)
class RangeFilter[T]:
    """
    Фильтр диапазона значений.
    Границы включаются.
    """

    minimum: T | None = None
    maximum: T | None = None

    def __post_init__(self) -> None:
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError(
                "minimum cannot be greater than maximum"
            )

    def is_empty(self) -> bool:
        return (
            self.minimum is None
            and self.maximum is None
        )


@dataclass(frozen=True, slots=True)
class TransactionFilter:
    """
    Фильтр получения транзакций.

    Пустая коллекция означает отсутствие ограничения.
    """

    # Точный список ID транзакций (условие IN). Пустой кортеж = без ограничения.
    transaction_ids: tuple[UUID, ...] = ()

    # Точный список типов транзакций (условие IN).
    transaction_types: tuple[entities.TransactionType, ...] = ()

    # Точный список ID поставщиков (условие IN).
    supplier_ids: tuple[UUID, ...] = ()

    # Сумма транзакции в копейках/центах (x100), диапазон или точное значение.
    total_amount: RangeFilter[Decimal] | None = None

    # Размер скидки в копейках/центах (x100), диапазон или точное значение.
    discount: RangeFilter[Decimal] | None = None

    # Диапазон дат совершения транзакции.
    transaction_date: RangeFilter[datetime.date] | None = None

    # None — без ограничения; True — только с комментарием;
    # False — только без комментария.
    comment_present: bool | None = None


@dataclass(frozen=True, slots=True)
class TransactionSummary:
    """Краткое представление транзакции для списков и поиска. Не содержит строки товаров."""

    transaction_id: UUID

    transaction_type: entities.TransactionType

    transaction_date: datetime.date
    created_at: datetime

    total_amount: Decimal
    discount: Decimal

    comment: str | None = None

    supplier_id: UUID | None = None
    supplier_name: str | None = None


if __name__ == "__main__":
    raise RuntimeError("This module is not intended to be run directly")
