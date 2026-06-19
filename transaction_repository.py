from __future__ import annotations
from uuid import UUID
import sqlite3
import database
import entities


class TransactionRepository:
    """Репозиторий для управления транзакциями (приход/расход) и их позициями в SQLite."""

    def __init__(self, db: database.Database):
        self._db = db

    def create_transaction(self, tx: entities.Transaction, items: list[ entities.TransactionItem]) -> None:
        """
        Сохраняет новую транзакцию и связанные с ней товары в БД.        
        Операция выполняется атомарно внутри одной транзакции БД: 
        если запись товаров не удастся, запись самой транзакции также откатится.        
        Args:
            tx: Объект транзакции с метаданными (дата, поставщик, суммы).
            items: Список позиций товаров, входящих в эту транзакцию.
        """

        sql_tx = """
        INSERT INTO transactions (
            transaction_id,
            transaction_type,
            total_amount,
            discount,
            comment,
            transaction_date,
            created_at,
            supplier_name,
            supplier_id
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
            purchase_price_x100,
            sale_price_x100,
            product_quantity_x1000,
            amount_x100
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        with self._db.transaction() as conn:
            conn.execute(sql_tx, self._map_tx_params(tx))

            for item in items:
                conn.execute(sql_item, self._map_item_params(item))

    def get_by_id(self, transaction_id: UUID) ->  entities.Transaction | None:
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

            item_rows = conn.execute(sql_items, (str(transaction_id),)).fetchall()

        items = [self._map_item(row) for row in item_rows]
        return self._map_tx(tx_row, items)

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
    def _map_tx(row: sqlite3.Row, items: list[ entities.TransactionItem]) ->  entities.Transaction:
        """
        Преобразует сырую строку результата SQL-запроса (Row) в объект доменной модели Transaction.        
        Args:
            row: Строка данных из таблицы transactions.
            items: Список уже маппированных объектов TransactionItem.            
        Returns:
            Экземпляр класса Transaction.
        """
        return  entities.Transaction(
            transaction_id=UUID(row["transaction_id"]),
            transaction_type=row["transaction_type"],
            total_amount=row["total_amount"],
            discount=row["discount"],
            comment=row["comment"] if row["comment"] else None,
            transaction_date=row["transaction_date"],
            created_at=row["created_at"],
            supplier_name=row["supplier_name"] if row["supplier_name"] else None,
            supplier_id=UUID(row["supplier_id"]) if row["supplier_id"] else None,
            items=items,
        )

    @staticmethod
    def _map_item(row: sqlite3.Row) ->  entities.TransactionItem:
        """
        Преобразует сырую строку результата SQL-запроса в объект TransactionItem.        
        Args:
            row: Строка данных из таблицы transaction_items.            
        Returns:
            Экземпляр класса TransactionItem.
        """
        return  entities.TransactionItem(
            item_id=UUID(row["item_id"]),
            transaction_id=UUID(row["transaction_id"]),
            product_id=UUID(row["product_id"]),
            product_barcode=row["product_barcode"],
            product_name=row["product_name"],
            product_unit=row["product_unit"],
            purchase_price_x100=row["purchase_price_x100"],
            sale_price_x100=row["sale_price_x100"],
            product_quantity_x1000=row["product_quantity_x1000"],
            amount_x100=row["amount_x100"],
        )

    @staticmethod
    def _map_tx_params(tx:  entities.Transaction):
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
            tx.transaction_type,
            tx.total_amount,
            tx.discount,
            tx.comment if tx.supplier_comment else None,
            tx.transaction_date,
            tx.created_at,
            tx.supplier_name if tx.supplier_name else None,
            str(tx.supplier_id) if tx.supplier_id else None,
        )

    @staticmethod
    def _map_item_params(item:  entities.TransactionItem):
        """
        Подготавливает кортеж параметров из объекта TransactionItem для SQL-запроса INSERT.        
        Преобразует все UUID-поля в строковый формат.        
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
            item.product_unit,
            item.purchase_price_x100,
            item.sale_price_x100,
            item.product_quantity_x1000,
            item.amount_x100,
        )
    
if __name__ == "__main__":
    raise RuntimeError("This module is not intended to be run directly")