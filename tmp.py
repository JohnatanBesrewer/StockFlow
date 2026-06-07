import sqlite3
import os

# 1. Импортируем твой класс репозитория и сущности (если нужно)
# Предполагаем, что класс называется ProductRepository
from repositories import ProductRepository 

def run_debug():
    # 2. Укажи правильный путь к твоему файлу базы данных SQLite
    # Если база лежит в корне проекта, укажи имя файла, например 'app.db'
    DB_PATH = "storage.db" 
    
    if not os.path.exists(DB_PATH):
        print(f"Ошибка: Файл базы данных по пути '{DB_PATH}' не найден!")
        return

    # 3. Подключаемся к базе напрямую, чтобы получить Row-контекст
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Чтобы обращаться к колонкам по именам: row["name"]
    
    print("=== ЗАПУСК ДИАГНОСТИКИ FTS ===")
    
    try:
        print("--- 1. СТРУКТУРА ТАБЛИЦЫ product_search ---")
        schema = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='product_search'"
        ).fetchone()
        if schema:
            print(schema["sql"])
        else:
            print("КРИТИЧЕСКАЯ ОШИБКА: Таблица product_search ВООБЩЕ НЕ НАЙДЕНА в БД!")
            return

        print("\n--- 2. ПЕРВЫЕ 5 СТРОК ИЗ product_search ---")
        rows = conn.execute(
            "SELECT rowid, * FROM product_search LIMIT 5"
        ).fetchall()
        if not rows:
            print("ВНИМАНИЕ: Таблица product_search абсолютно пустая!")
        for row in rows:
            print(dict(row))

        print("\n--- 3. ПРОВЕРКА ПРОСТОГО СОВПАДЕНИЯ (LIKE) ---")
        # Попробуем найти подстроку "Сухар" без учета регистра
        like_rows = conn.execute(
            "SELECT rowid, * FROM product_search WHERE name LIKE '%Сухар%' LIMIT 3"
        ).fetchall()
        if not like_rows:
            print("LIKE ничего не нашёл. Возможно, в базе вообще нет таких товаров?")
        for row in like_rows:
            print("LIKE found:", dict(row))

        print("\n--- 4. ТЕСТ СВЯЗИ С ОСНОВНОЙ ТАБЛИЦЕЙ ---")
        join_check = conn.execute("""
            SELECT COUNT(*) as cnt 
            FROM products p 
            JOIN product_search s ON s.product_id = p.product_id
        """).fetchone()
        print(f"Совпадений по JOIN между products и product_search: {join_check['cnt']}")
        
        # Проверим общее количество в products для сравнения
        total_products = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()
        print(f"Всего товаров в таблице products: {total_products['cnt']}")

    except Exception as e:
        print(f"Произошла ошибка при выполнении SQL: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_debug()