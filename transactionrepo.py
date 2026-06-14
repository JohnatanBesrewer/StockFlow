from __future__ import annotations
from uuid import UUID, uuid7
from decimal import Decimal
import datetime
import sqlite3
import database
from entities import Transaction, TransactionItem


class TransactionRepository:
    def __init__(self, db):
        self._db = db

    # =========================================================
    # CREATE (transaction + items) — атомарно
    # =========================================================
    def create_transaction(self, tx: Transaction, items: list[TransactionItem]) -> None:
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

    # =========================================================
    # READ FULL AGGREGATE
    # =========================================================
    def get_by_id(self, transaction_id: UUID) -> Transaction | None:
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

    # -------------------------
    # DELETE
    # -------------------------
    def delete(self, transaction_id: UUID) -> None:
        sql = """
        DELETE FROM transactions
        WHERE transaction_id = ?
        """

        with self._db.transaction() as conn:
            conn.execute(sql, (str(transaction_id),))

    # =========================================================
    # MAP TX
    # =========================================================
    @staticmethod
    def _map_tx(row: sqlite3.Row, items: list[TransactionItem]) -> Transaction:
        return Transaction(
            transaction_id=UUID(row["transaction_id"]),
            transaction_type=row["transaction_type"],
            total_amount=row["total_amount"],
            discount=row["discount"],
            comment=row["comment"],
            transaction_date=row["transaction_date"],
            created_at=row["created_at"],
            supplier_name=row["supplier_name"],
            supplier_id=UUID(row["supplier_id"]) if row["supplier_id"] else None,
            items=items,
        )

    # =========================================================
    # MAP ITEM
    # =========================================================
    @staticmethod
    def _map_item(row: sqlite3.Row) -> TransactionItem:
        return TransactionItem(
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

    # =========================================================
    # PARAMS TX
    # =========================================================
    @staticmethod
    def _map_tx_params(tx: Transaction):
        return (
            str(tx.transaction_id),
            tx.transaction_type,
            tx.total_amount,
            tx.discount,
            tx.comment,
            tx.transaction_date,
            tx.created_at,
            tx.supplier_name,
            str(tx.supplier_id) if tx.supplier_id else None,
        )

    # =========================================================
    # PARAMS ITEM
    # =========================================================
    @staticmethod
    def _map_item_params(item: TransactionItem):
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