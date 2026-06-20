from __future__ import annotations
from decimal import Decimal
from uuid import UUID, uuid7
import datetime
import entities
import product_repository


class ProductService:

    def __init__(self, repo: product_repository.ProductRepository) -> None:
        self._repo = repo

    def create_product(
        self,
        name: str,
        unit: entities.Unit,
        price: Decimal,
        barcode: str | None = None,
    ):
        product = entities.Product(
            None,
            barcode,
            name,
            unit,
            price,
        )

        self._repo.create(product)

    def get_product(self, product_id):
        pass

    def get_all_products(self):
        pass

    def update_product(self, product_id, **data):
        pass

    def delete_product(self, product_id):
        pass

    def search_products(self, query):
        pass
