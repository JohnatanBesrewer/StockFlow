import pandas as pd
import numpy as np


def is_valid_integer(value):
    """Проверяет, является ли значение целым положительным числом (int), а не float или строкой."""
    if pd.isna(value):
        return False
    if isinstance(value, bool):  # bool — подкласс int в Python, но нам не нужен
        return False
    if isinstance(value, int):
        return value >= 1
    if isinstance(value, float):
        return False  # даже 1.0 не принимаем
    if isinstance(value, str):
        return False  # даже "1" не принимаем
    return False


def find_longest_sequence_column(df):
    """Находит столбец с самой длинной последовательностью 1,2,...,N (в порядке строк)."""
    best_col = None
    best_length = 0
    best_rows = None  # список индексов строк, соответствующих 1..N

    for col in df.columns:
        seq_rows = []  # индексы строк, где найдены 1,2,3,...
        expected = 1  # ожидаемое следующее число

        for idx, val in df[col].items():
            if is_valid_integer(val):
                if val == expected:
                    seq_rows.append(idx)
                    expected += 1
                elif val > expected:
                    # Пропущено число — последовательность обрывается
                    break
                # если val < expected — игнорируем (дубликат или мусор)

        length = len(seq_rows)
        if length > best_length:
            best_length = length
            best_col = col
            best_rows = seq_rows

    return best_col, best_rows


def main(excel_path, csv_path):
    # Читаем Excel без заголовков (чтобы не терять строку, если она похожа на заголовок)
    df = pd.read_excel(excel_path, header=None, dtype=object)

    # Если файл пуст
    if df.empty:
        pd.DataFrame().to_csv(csv_path, index=False, header=False)
        return

    # Находим корректный столбец и строки
    target_col, selected_rows = find_longest_sequence_column(df)

    if target_col is None or not selected_rows:
        # Нет подходящей последовательности — сохраняем пустой CSV
        pd.DataFrame().to_csv(csv_path, index=False, header=False)
        return

    # Индекс целевого столбца
    col_idx = df.columns.get_loc(target_col)

    # Выбираем только нужные строки
    filtered_df = df.loc[selected_rows]

    # Удаляем столбцы слева от target_col
    filtered_df = filtered_df.iloc[:, col_idx:]

    # Сбрасываем индексы столбцов (чтобы начинать с 0)
    filtered_df.columns = range(filtered_df.shape[1])

    # Удаляем полностью пустые столбцы справа
    # Определяем, что такое "пусто": NaN, None, пустая строка
    def is_empty_cell(cell):
        if pd.isna(cell):
            return True
        if isinstance(cell, str) and cell.strip() == "":
            return True
        return False

    # Применяем к каждому столбцу: если все ячейки пустые — удаляем
    non_empty_cols = []
    for col in filtered_df.columns:
        col_data = filtered_df[col]
        if not col_data.apply(is_empty_cell).all():
            non_empty_cols.append(col)
        else:
            # Как только встретили первый пустой столбец с конца — можно остановиться?
            # Но по условию: "пустые столбцы, идущие после последней записи"
            # Это значит: удаляем **все** полностью пустые столбцы, независимо от позиции.
            pass

    if non_empty_cols:
        filtered_df = filtered_df[non_empty_cols]
        # Переназначаем индексы столбцов для порядка
        filtered_df.columns = range(len(non_empty_cols))
    else:
        filtered_df = pd.DataFrame()

    # Сохраняем без заголовков и без индексов
    filtered_df.to_csv(csv_path, index=False, header=False)


# === Пример использования ===
# main("input.xlsx", "output.csv")


try:
    main("nakladnaya.xlsx", "nakladnaya.xlsx.csv")
    print("✅ CSV успешно создан!")
except Exception as e:
    print(f"❌ Ошибка: {e}")
