from __future__ import annotations
from decimal import Decimal
from uuid import UUID, uuid7
import datetime
import entities
import product_repository
import database


class ProductService:

    def __init__(self, repo: product_repository.ProductRepository) -> None:
        self._repo = repo

    def create_product(
        self,
        name: str,
        unit: entities.Unit,
        price: Decimal,
        barcode: str | None = None,
    ) -> None:
        product = entities.Product(
            None,  # product_id
            barcode,
            name,
            unit,
            price,
            None,  # created_at
        )

        self._repo.create(product)

    def get_product(
        self,
        product_id: UUID | None = None,
        barcode: str | None = None,
        name: str | None = None
    ) -> entities.Product | None:

        if product_id:
            return self._repo.get_by_id(product_id)

        if barcode:
            return self._repo.get_by_barcode(barcode)

        if name:
            return self._repo.get_by_name(name)

        return

    def search_products_by_name(self, query: str, limit: int | None = None) -> list[entities.Product]:
        return self._repo.search_by_name(query, limit)

    def delete_product(self, product_id: UUID) -> bool:
        return self._repo.delete_product(product_id)

    def update_product(self,
                       product_id: UUID,
                       new_name: str | None = None,
                       new_unit: entities.Unit | None = None,
                       new_barcode: str | None = None,
                       new_price: Decimal | None = None,
                       ):
        pass

    def get_all_products(self):
        pass


# if __name__ == "__main__":
#     raise RuntimeError("This module is not intended to be run directly")

db = database.Database("storage.db")
db.init_schema("schema.sql")

ps = ProductService(product_repository.ProductRepository(db))

# ps.create_product("Кусок дерьма",
#                   entities.Unit.PIECE,
#                   Decimal(10.25),
#                   None,
#                   )

print(ps.get_product(name="Кусок дерьма"))
print(ps.get_product(barcode="2963939457544"))
print(ps.search_products_by_name("Д"))
print(ps.delete_product("019fd20a-fd1e-7124-8b9d-9eb97633b107"))
