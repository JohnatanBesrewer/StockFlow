from __future__ import annotations
from decimal import Decimal
from uuid import UUID, uuid7
import datetime
import entities
import product_repository
# import database
import validator


class ProductService:

    def __init__(self, repo: product_repository.ProductRepository) -> None:
        self._repo = repo

    def create_product(
        self,
        name: str,
        unit: entities.Unit,
        sale_price: Decimal,
        primary_barcode: str | None = None,
    ) -> entities.Product | None:

        if self.get_product(name=name):
            return None

        if primary_barcode and self.get_product(barcode=primary_barcode):
            return None

        product = entities.Product(
            None,  # UUID
            primary_barcode if primary_barcode else None,
            name,
            unit,
            sale_price,
            None,  # created_at
        )
        self._repo.create(product)
        return product

    def get_product(
        self,
        product_id: UUID | None = None,
        barcode: str | None = None,
        name: str | None = None
    ) -> entities.Product | None:

        if product_id is not None:
            return self._repo.get_by_id(product_id)

        if barcode is not None:
            return self._repo.get_by_barcode(barcode)

        if name is not None:
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
                       barcode_to_delete: str | None = None,
                       new_sale_price: Decimal | None = None,
                       ) -> None:
        # attrs_of_product = {
        #     key: val for key, val in locals().items()
        #     if key not in ('self', 'product_id') and val is not None
        # }
        product = self.get_product(product_id)

        if product is None:
            return

        if new_name is not None:
            self._repo.update_name(
                product.product_id, validator.validate_string(new_name))

        if new_unit is not None:
            self._repo.update_unit(product.product_id, new_unit)

        if new_barcode is not None:
            self._repo.add_barcode(
                product.product_id, validator.validate_ean13(new_barcode))

        if barcode_to_delete is not None:
            barcodes = self._repo.get_barcodes(product.product_id)

            if barcode_to_delete in barcodes and len(barcodes) > 1:
                self._repo.delete_barcode(
                    product.product_id,
                    barcode_to_delete,
                )

        if new_sale_price is not None:
            validated_price = validator.validate_price(
                new_sale_price,
                allow_zero=False,
            )
            if validated_price != product.sale_price:
                self._repo.set_sale_price(
                    product.product_id,
                    validated_price,
                    datetime.datetime.now(datetime.UTC)
                )

        return


if __name__ == "__main__":
    raise RuntimeError("This module is not intended to be run directly")

# db = database.Database("storage.db")
# db.init_schema("schema.sql")

# ps = ProductService(product_repository.ProductRepository(db))

# print(ps.create_product("Кусок дерьма",
#                         entities.Unit.PIECE,
#                         Decimal(10.25),
#                         None,
#                         ))

# ps.update_product(
#     UUID("019fe109-6c29-71f7-8c2c-eca6f39707bb"),
#     new_name="Хуйня2",
#     new_unit=entities.Unit.SET,
#     new_barcode="4610044661592",
#     barcode_to_delete="2933928670131",
#     new_sale_price=Decimal("118.11")
# )

# print(ps.get_product(name="хуйня"))
# print(ps.get_product(barcode="4610044661592"))
# print(ps.search_products_by_name("х"))
# print(ps.delete_product("019fe0ee-f1bf-7176-97fe-b0577a490611"))
