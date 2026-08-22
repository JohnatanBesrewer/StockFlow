from __future__ import annotations
import datetime
from collections.abc import Sequence
from decimal import Decimal
import uuid
import entities
import transaction_repository


class TransactionService:
    def __init__(self, repo: transaction_repository.TransactionRepository) -> None:
        self._repo = repo

    def create_transaction(
            self,
            transaction_type: entities.TransactionType,
            transaction_items: Sequence[entities.TransactionItem],
            transaction_date: datetime.date,
            discount: Decimal = Decimal("0"),
            comment: str | None = None,
            supplier_id: uuid.UUID | None = None,
            supplier_name: str | None = None,
    ) -> entities.Transaction | None:
        transaction = entities.Transaction(
            transaction_id=uuid.uuid7(),
            transaction_type=transaction_type,
            items=tuple(transaction_items),
            transaction_date=transaction_date,
            created_at=datetime.datetime.now(datetime.UTC),
            comment=comment,
            discount=discount,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
        )
        self._repo.create_transaction(transaction)
        return transaction

    def get_transaction(
        self,
        transaction_id: uuid.UUID,
    ) -> entities.Transaction | None:
        return self._transaction_repository.get_by_id(transaction_id)

    def get_transactions_by_date(
        self,
        transaction_date: datetime.date,
    ) -> list[entities.Transaction]:
        return self._transaction_repository.get_by_date(transaction_date)

    def search_transactions(
        self,
        filter_: transaction_repository.TransactionFilter,
    ) -> list[transaction_repository.TransactionSummary]:
        return self._repo.find(filter_)

    def delete_transaction(
        self,
        transaction_id: uuid.UUID,
    ) -> None:
        self._repo.delete(transaction_id)
