from __future__ import annotations
from uuid import UUID, uuid7
from decimal import Decimal
import datetime
import sqlite3
import entities
import validator
import database

# update_price
# add_barcode
# delete_product
# update_name
# add_barcode(...)
# remove_barcode(...)
# set_primary_barcode(...)


class ProductRepository:

    _PRODUCT_SELECT = """
    SELECT
        p.product_id,
        p.name,
        p.unit,
        p.created_at,

        (
            SELECT b.barcode
            FROM barcodes b
            WHERE b.product_id = p.product_id
            ORDER BY b.created_at ASC
            LIMIT 1
        ) AS primary_barcode,

        (
            SELECT sp.price_x100
            FROM sale_prices sp
            WHERE sp.product_id = p.product_id
            AND sp.valid_to IS NULL
            ORDER BY sp.valid_from DESC
            LIMIT 1
        ) AS active_price

    FROM products p
"""

    def __init__(self, db: database.Database) -> None:
        self._db = db

    @staticmethod
    def _normalize_query(query: str) -> str:
        """
        Превращает пользовательский ввод в безопасный FTS5-запрос.
        Удаляет недопустимые символы, добавляет префиксный поиск.
        """

        if not query:
            return ""

        # 1. Удаляем символы, которые ломают FTS5
        # % _ " ' : ( ) + - < > = ~ ^ |
        bad_chars = "%_\"'():+-<>~=^|"
        cleaned = query.translate({ord(c): " " for c in bad_chars})

        # 2. Разбиваем на слова
        parts = [p.strip() for p in cleaned.split() if p.strip()]

        if not parts:
            return ""

        # 3. Префиксный поиск
        tokens = [f"{p}*" for p in parts]

        # 4. Соединяем через AND
        return " AND ".join(tokens)

    @staticmethod
    def _build_product_from_row(row: sqlite3.Row) -> entities.Product:
        """
        Единый mapper для сборки _Product из строки.
        Используется и в get_by_id(), и в search_by_name().
        """
        product_id = row["product_id"]

        if row["primary_barcode"] is None:
            raise RuntimeError(
                f"Product {product_id} exists but has no barcodes — нарушена целостность данных"
            )

        if row["active_price"] is None:
            raise RuntimeError(
                f"Product {product_id} exists but has no active price — нарушена целостность данных"
            )

        return entities.Product(
            product_id=UUID(product_id),
            primary_barcode=row["primary_barcode"],
            name=row["name"],
            unit=entities.Unit(row["unit"]),
            sale_price=Decimal(row["active_price"]) / Decimal("100"),
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
        )

    def create(
        self,
        product: entities.Product,
    ) -> None:
        """
        Сохраняет новый  Product. Вставляет строки в таблицы:
        - products (product_id, name, unit, created_at),
        - barcodes (barcode, product_id, created_at),
        - sale_prices (price_id, product_id, price_x100, valid_from)
        """

        product_id_str = str(product.product_id)
        created_at_str = product.created_at.astimezone(datetime.UTC).isoformat()

        with self._db.transaction() as conn:

            conn.execute(
                """
                INSERT INTO products (
                    product_id, name, unit, created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    product_id_str,
                    product.name,
                    product.unit.value,
                    created_at_str,
                ),
            )

            # 3. Вставка в barcodes
            conn.execute(
                """
                INSERT INTO barcodes (barcode, product_id, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    product.primary_barcode,
                    product_id_str,
                    created_at_str,
                ),
            )

            # 4. Вставка в sale_prices
            price_id = uuid7()  # репозиторий может генерировать только свои ключи
            conn.execute(
                """
                INSERT INTO sale_prices (price_id, product_id, price_x100, valid_from, valid_to)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (
                    str(price_id),
                    product_id_str,
                    int(product.sale_price * 100),  # Decimal → INTEGER
                    created_at_str,
                ),
            )

    def get_by_id(
        self,
        product_id: UUID | str,
    ) -> entities.Product | None:

        sql = self._PRODUCT_SELECT + """
            WHERE p.product_id = ?
            """

        with self._db.read_connection() as conn:
            row = conn.execute(
                sql,
                (str(product_id),),
            ).fetchone()

        if row is None:
            return None

        return self._build_product_from_row(row)

    def get_by_barcode(self, barcode: str) -> entities.Product | None:
        """
        Получаем продукт по штрихкоду. Используем существующие подзапросы
        для сборки, фильтруя через EXISTS по таблице штрихкодов.
        """
        barcode = validator.validate_ean13(barcode)

        # Просто добавляем условие фильтрации к базовому запросу
        sql = self._PRODUCT_SELECT + """
            WHERE EXISTS (
                SELECT 1 FROM barcodes b 
                WHERE b.product_id = p.product_id AND b.barcode = ?
            )
            LIMIT 1
        """
        with self._db.read_connection() as conn:
            row = conn.execute(sql, (barcode,)).fetchone()

        if row is None:
            return None

        return self._build_product_from_row(row)

    def search_by_name(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[entities.Product]:

        normalized = self._normalize_query(query)

        if not normalized:
            return []

        sql = self._PRODUCT_SELECT + """
            JOIN product_search s
                ON s.product_id = p.product_id

            WHERE s.name MATCH ?
            

            ORDER BY bm25(product_search)
            """
        params: list[str | int] = [normalized]

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        with self._db.transaction() as conn:
            rows = conn.execute(
                sql,
                params,
            ).fetchall()

        return [self._build_product_from_row(row) for row in rows]

    # def update_product(
    #     self,
    #     product_id: UUID,
    #     *,
    #     name: str | None = None,
    #     unit_id: UUID | None = None,
    #     price: Decimal | None = None,
    #     barcodes: list[str] | None = None,
    # ) -> None:
    #     pass
    
    def delete_product(self, product_id: UUID) -> None:
        """
        Удаляет продукт по product_id.        
        """

        with self._db.transaction() as conn:
            conn.execute(
            "DELETE FROM products WHERE product_id = ?",
            (str(product_id),)
        )
    
    def set_sale_price(
        self,
        product_id: UUID | str,
        new_price: Decimal,
        now: datetime.datetime | None = None,
    ) -> None:
        """
        Закрывает текущую цену товара и создаёт новую запись цены.
        Сохраняет полную историю изменений.
        """

        if now is None:
            now = datetime.datetime.now(datetime.UTC)

        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        now_iso = now.astimezone(datetime.UTC).isoformat()

        validated_price = validator.validate_price(new_price)
        price_cents = int(validated_price * Decimal("100"))

        product_id_str = str(product_id)

        with self._db.transaction() as conn:
            exists = conn.execute(
                "SELECT 1 FROM products WHERE product_id = ?",
                (product_id_str,),
            ).fetchone()

            if exists is None:
                raise RuntimeError(f"Product {product_id} does not exist")

            active = conn.execute(
                """
                SELECT
                    price_id,
                    price_x100,
                    valid_from
                FROM sale_prices
                WHERE product_id = ?
                AND valid_to IS NULL
                """,
                (product_id_str,),
            ).fetchone()

            if active is None:
                raise RuntimeError(f"Product {product_id} has no active price")

            # Защита от бессмысленного создания новой записи.
            if active["price_x100"] == price_cents:
                return

            # Запрещаем создавать цену раньше текущей активной.
            if now_iso < active["valid_from"]:
                raise ValueError(
                    "new price timestamp is earlier than active price start"
                )

            conn.execute(
                """
                UPDATE sale_prices
                SET valid_to = ?
                WHERE price_id = ?
                """,
                (
                    now_iso,
                    active["price_id"],
                ),
            )

            conn.execute(
                """
                INSERT INTO sale_prices (
                    price_id,
                    product_id,
                    price_x100,
                    valid_from,
                    valid_to
                )
                VALUES (?, ?, ?, ?, NULL)
                """,
                (
                    str(uuid7()),
                    product_id_str,
                    price_cents,
                    now_iso,
                ),
            )

    def add_barcode(self, product_id: UUID, barcode: str) -> None:
        """
        Добавляет новый EAN-13 штрихкод к продукту.
        """
        barcode = validator.validate_ean13(barcode)
        now = datetime.datetime.now(datetime.UTC)
        now_iso = now.astimezone(datetime.UTC).isoformat()

        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO barcodes (barcode, product_id, created_at) VALUES (?, ?, ?)",
                (barcode, str(product_id), now_iso),
            )

    def update_name(self, product_id: UUID, new_name: str) -> bool:
        """
        Обновляет имя продукта.
        Возвращает True, если продукт обновлён, False если продукта с таким id нет.
        FTS5 обновляется автоматически триггерами.
        """
        name = validator.validate_string(new_name)

        with self._db.transaction() as conn:
            cursor = conn.execute(
                "UPDATE products SET name = :name WHERE product_id = :product_id",
                {"name": name, "product_id": str(product_id)},
            )
            return cursor.rowcount > 0


repo = ProductRepository(database.db)


# product1 = entities.Product(
#     None,  # uuid7(),
#     None,  # validate_ean13(code: str) -> str
#     "Сухари чёрные",
#     entities.Unit.PIECE,
#     Decimal(120.50),
#     None,  # datetime.datetime.now(datetime.UTC),
# )

# repo.create(product1)

# product2 = entities.Product(
#     None,  # uuid7(),
#     None,  # validate_ean13(code: str) -> str
#     "Топор зелёныйй",
#     entities.Unit.METRE,
#     Decimal(15.55),
#     None,  # datetime.datetime.now(datetime.UTC),
# )

# repo.create(product2)


# def dump_table(db: database.Database, table: str):
#     with db.transaction() as conn:
#         rows = conn.execute(f"SELECT * FROM {table}").fetchall()
#         for row in rows:
#             print(dict(row))


# dump_table(database.db, "products")
# dump_table(database.db, "barcodes")
# dump_table(database.db, "sale_prices")

# print(repo.get_by_id(UUID("019e8454-c959-7743-8a7f-d84d14711585")))
# print(repo.get_by_barcode("2954456322828"))

# repo.add_barcode(UUID("019e8454-c95e-762e-ab07-9ec59acc78b7"), "5901234123457")

# print(repo.update_name(UUID("019e8454-c95e-762e-ab07-9ec59acc78b7"), "Топор зелёный"))
# print(repo.get_by_barcode("5901234123457"))

# print(repo.search_by_name("зе"))

# repo.set_sale_price("019e8454-c95e-762e-ab07-9ec59acc78b7", Decimal("11.90"))
# repo.delete_product(UUID("019ebc79-71e0-766e-8e7f-e0005f5299f4"))
