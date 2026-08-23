from __future__ import annotations
import uuid
import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
import entities
import transaction_repository


class TransactionService:
    def __init__(self, repo: transaction_repository.TransactionRepository) -> None:
        self._repo = repo

    def create_transaction(
            self,
            transaction_type: entities.TransactionType,
            items_data: Sequence[TransactionItemCreate],
            transaction_date: datetime.date,
            discount: Decimal = Decimal("0"),
            comment: str | None = None,
            supplier_id: uuid.UUID | None = None,
            supplier_name: str | None = None,
    ) -> entities.Transaction:

        transaction_id = uuid.uuid7()

        items = tuple(
            entities.TransactionItem(
                item_id=None,
                transaction_id=transaction_id,
                product_id=item.product_id,
                product_barcode=item.product_barcode,
                product_name=item.product_name,
                product_unit=item.product_unit,
                product_price=item.product_price,
                product_quantity=item.product_quantity,
            )
            for item in items_data
        )

        transaction = entities.Transaction(
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            items=items,
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


@dataclass(frozen=True, slots=True)
class TransactionItemCreate:
    product_id: uuid.UUID
    product_barcode: str
    product_name: str
    product_unit: entities.Unit
    product_price: Decimal
    product_quantity: Decimal
