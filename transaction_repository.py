from __future__ import annotations
from uuid import UUID
from decimal import Decimal
from collections.abc import Sequence
import sqlite3
import datetime
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

        items = [self._map_item(row) for row in item_rows]
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
            items = items_by_tx_id.get(
                row["transaction_id"],
                []
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
        row: sqlite3.Row, items: Sequence[entities.TransactionItem]
    ) -> entities.Transaction:
        """
        Преобразует сырую строку результата SQL-запроса (Row) в объект доменной модели Transaction.
        Args:
            row: Строка данных из таблицы transactions.
            items: Список уже маппированных объектов TransactionItem.
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
            int(tx.total_amount * 100),
            int(tx.discount * 100),
            tx.comment if tx.comment else None,
            tx.transaction_date.isoformat(),
            tx.created_at.isoformat(),
            str(tx.supplier_id) if tx.supplier_id else None,
            tx.supplier_name if tx.supplier_name else None,
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


if __name__ == "__main__":
    raise RuntimeError("This module is not intended to be run directly")
