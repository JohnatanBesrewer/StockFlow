import sqlite3
import entities
import json


def get_sql_structure(sql_script: str) -> dict:
    """
    Выполняет SQL-скрипт в памяти и возвращает структуру всех созданных таблиц.
    """
    conn = sqlite3.connect(":memory:")
    try:
        # 1. Выполняем скрипт (всё только в ОЗУ)
        conn.executescript(sql_script)
        cursor = conn.cursor()

        # 2. Ищем все пользовательские таблицы
        cursor.execute(
            """
            SELECT name, sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """
        )
        tables = cursor.fetchall()

        if not tables:
            return {
                "status": "empty",
                "message": "Таблицы не созданы или скрипт не выполнился.",
            }

        structure = {}
        for table_name, create_ddl in tables:
            # 3. Вытаскиваем детали колонок
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns_info = cursor.fetchall()

            structure[table_name] = {
                "create_ddl": create_ddl,
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2] or "ANY",
                        "not_null": bool(col[3]),
                        "default": col[4],
                        "primary_key": bool(col[5]),
                    }
                    for col in columns_info
                ],
            }

        return structure

    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


# ========================
# 🖨️ Красивый вывод в консоль
# ========================
def print_structure(structure: dict):
    if "error" in structure:
        print(f"❌ Ошибка: {structure['error']}")
        return
    if structure.get("status") == "empty":
        print("ℹ️  " + structure["message"])
        return

    print("=" * 60)
    for t_name, t_data in structure.items():
        print(f"📦 Таблица: {t_name}")
        print(f"📜 DDL: {t_data['create_ddl'][:80]}...")
        print("-" * 60)
        print(f"{'Колонка':<15} | {'Тип':<10} | {'PK':<4} | {'NOT NULL':<8} | Default")
        print("-" * 60)
        for col in t_data["columns"]:
            print(
                f"{col['name']:<15} | {col['type']:<10} | {str(col['primary_key']):<4} | {str(col['not_null']):<8} | {col['default']}"
            )
        print("=" * 60 + "\n")


# ========================
# Примеры использования
# ========================
if __name__ == "__main__":

    units = [u.value for u in entities._Unit]
    check_unit = f"CHECK(unit IN ({','.join(repr(u) for u in units)}))"

    transaction_types = [tp.value for tp in entities._TransactionType]
    check_tp = (
        f"CHECK(transaction_type IN ({','.join(repr(tp) for tp in transaction_types)}))"
    )

    sql_script = f"""
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY CONSTRAINT chk_products_product_id CHECK(length(product_id) = 36), 
        name TEXT NOT NULL CONSTRAINT chk_products_name CHECK(length(name) BETWEEN 1 AND {entities.MAX_STRING_LENGTH}),
        unit TEXT NOT NULL {check_unit},
        created_at TEXT NOT NULL CONSTRAINT chk_products_created_at CHECK(datetime(created_at) IS NOT NULL)
    );

    CREATE TABLE IF NOT EXISTS barcodes (
        barcode TEXT PRIMARY KEY CONSTRAINT chk_barcodes_barcode CHECK(length(barcode) <= {entities.MAX_STRING_LENGTH}),
        product_id TEXT NOT NULL CONSTRAINT chk_barcodes_product_id CHECK(length(product_id) = 36),
        created_at TEXT NOT NULL CONSTRAINT chk_barcodes_created_at CHECK(datetime(created_at) IS NOT NULL),
        FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS sale_prices (
        price_id TEXT PRIMARY KEY CONSTRAINT chk_sale_prices_price_id CHECK(length(price_id) = 36),
        product_id TEXT NOT NULL CONSTRAINT chk_sale_prices_product_id CHECK(length(product_id) = 36),
        price INTEGER NOT NULL CONSTRAINT chk_sale_prices_price CHECK(price >= 0),
        valid_from TEXT NOT NULL CONSTRAINT chk_sale_prices_valid_from CHECK(datetime(valid_from) IS NOT NULL),
        valid_to TEXT NOT NULL CONSTRAINT chk_sale_prices_valid_to CHECK(datetime(valid_to) IS NOT NULL),
        CONSTRAINT chk_sale_prices_period CHECK(valid_from < valid_to),
        CONSTRAINT fk_sale_prices_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id TEXT PRIMARY KEY CONSTRAINT chk_suppliers_supplier_id CHECK(length(supplier_id) = 36),
        name TEXT NOT NULL UNIQUE CONSTRAINT chk_suppliers_name CHECK(length(name) <= {entities.MAX_STRING_LENGTH}),
        created_at TEXT NOT NULL CONSTRAINT chk_suppliers_created_at CHECK(datetime(created_at) IS NOT NULL)
    );

    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY CONSTRAINT chk_transactions_transaction_id CHECK(length(transaction_id) = 36),
        transaction_type TEXT NOT NULL {check_tp},
        total_amount INTEGER NOT NULL CONSTRAINT chk_transactions_total CHECK(total_amount >= 0),
        discount INTEGER NOT NULL DEFAULT 0 CONSTRAINT chk_transactions_discount 
            CHECK(discount >= 0 AND discount <= total_amount),
        comment TEXT CONSTRAINT chk_transactions_comment CHECK(length(comment) <= {entities.MAX_STRING_LENGTH}),
        transaction_date TEXT NOT NULL CONSTRAINT chk_transactions_date 
            CHECK(datetime(transaction_date) IS NOT NULL),
        created_at TEXT NOT NULL CONSTRAINT chk_transactions_created_at CHECK(datetime(created_at) IS NOT NULL)
    );

    CREATE TABLE IF NOT EXISTS transaction_items (
        item_id TEXT PRIMARY KEY CONSTRAINT chk_transaction_items_item_id CHECK(length(item_id) = 36),
        transaction_id TEXT NOT NULL CONSTRAINT chk_transaction_items_transaction_id CHECK(length(transaction_id) = 36),
        product_id TEXT NOT NULL CONSTRAINT chk_transaction_items_product_id CHECK(length(product_id) = 36),
        product_barcode TEXT NOT NULL CONSTRAINT chk_transaction_items_product_barcode CHECK(length(product_barcode) <= {entities.MAX_STRING_LENGTH}),
        product_name TEXT NOT NULL CONSTRAINT chk_transaction_items_product_name CHECK(length(product_name) <= {entities.MAX_STRING_LENGTH}),
        purchase_price INTEGER CONSTRAINT chk_items_purchase_price 
            CHECK(purchase_price IS NULL OR purchase_price >= 0),
        sale_price INTEGER CONSTRAINT chk_items_sale_price 
            CHECK(sale_price IS NULL OR sale_price >= 0),
        product_quantity INTEGER NOT NULL CONSTRAINT chk_items_quantity 
            CHECK(product_quantity > 0),
        amount INTEGER NOT NULL CONSTRAINT chk_items_amount CHECK(amount >= 0),
        CONSTRAINT chk_items_price_exists 
            CHECK ((sale_price IS NOT NULL AND purchase_price IS NULL) OR (sale_price IS NULL AND purchase_price IS NOT NULL)),
        CONSTRAINT chk_items_amount_calc 
            CHECK (amount = product_quantity * COALESCE(sale_price, purchase_price)),
        CONSTRAINT fk_ti_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE,
        CONSTRAINT fk_ti_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
    );
    """
    result = get_sql_structure(sql_script)
    print_structure(result)
