-- T A B L E S
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY CONSTRAINT chk_products_product_id CHECK(length(product_id) = 36),
    name TEXT NOT NULL CONSTRAINT chk_products_name CHECK(
        length(name) BETWEEN 1
        AND 255
    ),
    name_normalized TEXT NOT NULL UNIQUE
        CONSTRAINT chk_products_name_normalized CHECK(
            length(name_normalized) BETWEEN 1 AND 255
        ),
    unit TEXT NOT NULL CHECK(
        unit IN ('шт', 'кг', 'л', 'м', 'упак', 'компл', 'набор')
    ),
    created_at TEXT NOT NULL CONSTRAINT chk_products_created_at CHECK (
        created_at GLOB '20[0-9][0-9]-[0-1][0-9]-[0-3][0-9][T ][0-2][0-9]:[0-5][0-9]:[0-5][0-9]*'
    )
);

CREATE TABLE IF NOT EXISTS barcodes (
    barcode TEXT PRIMARY KEY CONSTRAINT chk_barcodes_barcode CHECK(length(barcode) = 13),
    product_id TEXT NOT NULL CONSTRAINT chk_barcodes_product_id CHECK(length(product_id) = 36),
    created_at TEXT NOT NULL CONSTRAINT chk_barcodes_created_at CHECK (
        created_at GLOB '20[0-9][0-9]-[0-1][0-9]-[0-3][0-9][T ][0-2][0-9]:[0-5][0-9]:[0-5][0-9]*'
    ),
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sale_prices (
    price_id TEXT PRIMARY KEY CONSTRAINT chk_sale_prices_price_id CHECK(length(price_id) = 36),
    product_id TEXT NOT NULL CONSTRAINT chk_sale_prices_product_id CHECK(length(product_id) = 36),
    price_x100 INTEGER NOT NULL CONSTRAINT chk_sale_prices_price_x100 CHECK(price_x100 >= 0),
    valid_from TEXT NOT NULL CONSTRAINT chk_sale_prices_valid_from CHECK (
        valid_from GLOB '20[0-9][0-9]-[0-1][0-9]-[0-3][0-9][T ][0-2][0-9]:[0-5][0-9]:[0-5][0-9]*'
    ),
    valid_to TEXT DEFAULT NULL CONSTRAINT chk_sale_prices_valid_to CHECK (
        valid_to IS NULL
        OR valid_to GLOB '20[0-9][0-9]-[0-1][0-9]-[0-3][0-9][T ][0-2][0-9]:[0-5][0-9]:[0-5][0-9]*'
    ),
    CONSTRAINT chk_sale_prices_valid_range CHECK (
        valid_to IS NULL
        OR valid_from <= valid_to
    ),
    CONSTRAINT fk_sale_prices_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY CONSTRAINT chk_suppliers_supplier_id CHECK(length(supplier_id) = 36),
    name TEXT NOT NULL UNIQUE CONSTRAINT chk_suppliers_name CHECK(length(name) <= 255),
    created_at TEXT NOT NULL CONSTRAINT chk_suppliers_created_at CHECK (
        created_at GLOB '20[0-9][0-9]-[0-1][0-9]-[0-3][0-9][T ][0-2][0-9]:[0-5][0-9]:[0-5][0-9]*'
    )
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY CONSTRAINT chk_transactions_transaction_id CHECK(length(transaction_id) = 36),
    transaction_type TEXT NOT NULL CONSTRAINT chk_transactions_transaction_type CHECK (
        transaction_type IN (
            'purchase',
            'sale',
            'return_from_customer',
            'return_to_supplier',
            'write_off',
            'dekitting',
            'inventory'
        )
    ),
    total_amount_x100 INTEGER NOT NULL CONSTRAINT chk_transactions_total_amount_x100 CHECK(total_amount_x100 >= 0),
    discount_x100 INTEGER NOT NULL DEFAULT 0 CONSTRAINT chk_transactions_discount_x100 CHECK (
        discount_x100 >= 0
        AND discount_x100 <= total_amount_x100
    ),
    comment TEXT CONSTRAINT chk_transactions_comment CHECK(length(comment) <= 255),
    transaction_date TEXT NOT NULL CONSTRAINT chk_transactions_transaction_date CHECK (
        transaction_date GLOB '20[0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
    ),
    created_at TEXT NOT NULL CONSTRAINT chk_transactions_created_at CHECK (
        created_at GLOB '20[0-9][0-9]-[0-1][0-9]-[0-3][0-9][T ][0-2][0-9]:[0-5][0-9]:[0-5][0-9]*'
    ),
    supplier_id TEXT,
    supplier_name TEXT,
    CONSTRAINT chk_transactions_supplier_logic CHECK (
        (
            transaction_type IN ('purchase', 'return_to_supplier')
            AND supplier_id IS NOT NULL
            AND length(supplier_id) = 36
            AND supplier_name IS NOT NULL
            AND length(supplier_name) <= 255
        )
        OR (
            transaction_type NOT IN ('purchase', 'return_to_supplier')
            AND supplier_id IS NULL
            AND supplier_name IS NULL
        )
    ),
    CONSTRAINT fk_transactions_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS transaction_items (
    item_id TEXT PRIMARY KEY CONSTRAINT chk_transaction_items_item_id CHECK(length(item_id) = 36),
    transaction_id TEXT NOT NULL CONSTRAINT chk_transaction_items_transaction_id CHECK(length(transaction_id) = 36),
    product_id TEXT NOT NULL CONSTRAINT chk_transaction_items_product_id CHECK(length(product_id) = 36),
    product_barcode TEXT NOT NULL CONSTRAINT chk_transaction_items_product_barcode CHECK(length(product_barcode) = 13),
    product_name TEXT NOT NULL CONSTRAINT chk_transaction_items_product_name CHECK(length(product_name) <= 255),
    product_unit TEXT NOT NULL CHECK(
        product_unit IN ('шт', 'кг', 'л', 'м', 'упак', 'компл', 'набор')
    ),
    product_price_x100 INTEGER NOT NULL
    CONSTRAINT chk_items_product_price_x100 CHECK (product_price_x100 >= 0),
    product_quantity_x1000 INTEGER NOT NULL CONSTRAINT chk_items_quantity CHECK(product_quantity_x1000 > 0),
    amount_x100 INTEGER NOT NULL
    CONSTRAINT chk_items_amount_x100 CHECK (amount_x100 >= 0),
    CONSTRAINT chk_items_price_amount_consistency CHECK (amount_x100 = (product_quantity_x1000 * product_price_x100 + 500) / 1000),
    CONSTRAINT fk_ti_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    CONSTRAINT fk_ti_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
    );

-- I N D E X E S
-- 1. Таблица products

-- 2. Таблица barcodes
CREATE INDEX IF NOT EXISTS idx_barcodes_product_id ON barcodes(product_id, created_at ASC);

-- 3. Таблица sale_prices
CREATE INDEX IF NOT EXISTS idx_sale_prices_product_dates ON sale_prices(product_id, valid_to, valid_from DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_price ON sale_prices(product_id)
WHERE
    valid_to IS NULL;

-- 4. Таблица transactions
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);

CREATE INDEX IF NOT EXISTS idx_transactions_type_date ON transactions(transaction_type, transaction_date);

-- 5. Таблица transaction_items
CREATE INDEX IF NOT EXISTS idx_transaction_items_transaction_id ON transaction_items(transaction_id);

CREATE INDEX IF NOT EXISTS idx_transaction_items_product_id ON transaction_items(product_id);

CREATE INDEX IF NOT EXISTS idx_transaction_items_barcode ON transaction_items(product_barcode);

-- ============================================
-- FTS5: полнотекстовый поиск по имени продукта
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS product_search USING fts5(
    name,
    product_id UNINDEXED,
    tokenize = 'unicode61 remove_diacritics 2'
);

-- INSERT → добавить запись в FTS5
CREATE TRIGGER IF NOT EXISTS products_ai
AFTER
INSERT
    ON products BEGIN
INSERT INTO
    product_search(rowid, name, product_id)
VALUES
    (new.rowid, new.name, new.product_id);

END;

-- UPDATE → обновить запись в FTS5 при изменении имени
CREATE TRIGGER IF NOT EXISTS products_au
AFTER
UPDATE
    OF name ON products BEGIN
DELETE FROM
    product_search
WHERE
    rowid = old.rowid;

INSERT INTO
    product_search(rowid, name, product_id)
VALUES
    (new.rowid, new.name, new.product_id);

END;

-- DELETE → удалить запись из FTS5
CREATE TRIGGER IF NOT EXISTS products_ad
AFTER
    DELETE ON products BEGIN
DELETE FROM
    product_search
WHERE
    rowid = old.rowid;

END;