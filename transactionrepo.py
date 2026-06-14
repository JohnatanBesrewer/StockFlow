from __future__ import annotations
from uuid import UUID, uuid7
from decimal import Decimal
import datetime
import sqlite3
import database

from entities import Transaction


class TransactionRepository:
    def __init__(self, db: database.Database):
        self._db = db

    # -------------------------
    # CREATE
    # -------------------------
    def add_transaction(self, tx: Transaction) -> None:
        sql = """
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

        with self._db.transaction() as conn:
            conn.execute(
                sql,
                (
                    str(tx.transaction_id),
                    tx.transaction_type,
                    tx.total_amount,
                    tx.discount,
                    tx.comment,
                    tx.transaction_date.isoformat(),
                    tx.created_at.isoformat(),
                    tx.supplier_name,
                    str(tx.supplier_id) if tx.supplier_id else None,
                ),
            )

    # -------------------------
    # READ BY ID
    # -------------------------
    def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        sql = """
        SELECT *
        FROM transactions
        WHERE transaction_id = ?
        """

        with self._db.read_connection() as conn:
            row = conn.execute(sql, (str(transaction_id),)).fetchone()

        if not row:
            return None

        return self._map(row)

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

    # -------------------------
    # LIST (базовый вариант)
    # -------------------------
    def list_latest(self, limit: int = 50) -> list[Transaction]:
        sql = """
        SELECT *
        FROM transactions
        ORDER BY created_at DESC
        LIMIT ?
        """

        with self._db.read_connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()

        return [self._map(r) for r in rows]

    # -------------------------
    # MAPPER
    # -------------------------
    def _map(self, row: sqlite3.Row) -> Transaction:
        return Transaction(
            transaction_id=UUID(row["transaction_id"]),
            transaction_type=row["transaction_type"],
            total_amount=row["total_amount"],
            discount=row["discount"],
            comment=row["comment"],
            transaction_date=datetime.date.fromisoformat(row["transaction_date"]),
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
            supplier_name=row["supplier_name"],
            supplier_id=UUID(row["supplier_id"]) if row["supplier_id"] else None,
        )