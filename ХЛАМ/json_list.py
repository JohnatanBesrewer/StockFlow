import pandas as pd
import json
import numpy as np
from pathlib import Path


def find_index_column(df):
    """
    Находит столбец с самой длинной непрерывной последовательностью 1,2,3,... без пропусков.
    Возвращает:
        - имя столбца (или None, если не найден)
        - список индексов строк, где находятся числа 1..N
        - длина последовательности N
    """
    best_col = None
    best_indices = []
    best_length = 0

    for col in df.columns:
        # Получаем серию значений
        series = df[col]
        valid_positions = []  # (row_index, expected_value)

        # Собираем все позиции, где значение — целое положительное число
        for idx, val in series.items():
            if pd.isna(val):
                continue
            try:
                # Пробуем привести к float, затем проверить целочисленность
                fval = float(val)
                if fval.is_integer() and fval >= 1:
                    valid_positions.append((idx, int(fval)))
            except (ValueError, TypeError):
                continue

        # Группируем по порядку: ищем непрерывную последовательность, начинающуюся с 1
        # Сортируем по фактическому порядку строк (индексам DataFrame)
        valid_positions.sort(key=lambda x: x[0])  # сохраняем порядок строк

        # Теперь ищем подпоследовательность, которая является 1,2,3,...
        current_seq = []
        expected = 1
        seq_indices = []

        for row_idx, num in valid_positions:
            if num == expected:
                seq_indices.append(row_idx)
                current_seq.append(num)
                expected += 1
            elif num > expected:
                # Пропущено число — обрываем последовательность
                break
            # Если num < expected — игнорируем (например, дубликат или мусор)

        # Проверяем, начинается ли с 1
        if current_seq and current_seq[0] == 1:
            length = len(current_seq)
            if length > best_length:
                best_length = length
                best_col = col
                best_indices = seq_indices

    return best_col, best_indices, best_length


def trim_columns(df, start_col_name):
    """
    Обрезает DataFrame: оставляет столбцы от start_col_name до последнего непустого.
    """
    start_idx = list(df.columns).index(start_col_name)
    sub_df = df.iloc[:, start_idx:].copy()

    # Удаляем пустые столбцы справа (только в выбранных строках? но пока глобально)
    # Лучше удалять, если столбец полностью пуст во всём df, но по условию — "после последней записи"
    # Для точности: определим, какие столбцы имеют хотя бы одно непустое значение
    non_empty_cols = sub_df.columns[sub_df.notna().any(axis=0)]
    if len(non_empty_cols) == 0:
        return sub_df.iloc[:, :0]  # пустой DataFrame с нужными столбцами
    last_non_empty = non_empty_cols[-1]
    last_idx = sub_df.columns.get_loc(last_non_empty)
    return sub_df.iloc[:, : last_idx + 1]


def excel_to_json(excel_path, json_path):
    """
    Основная функция: читает Excel, находит индексный столбец, фильтрует строки и сохраняет в JSON.
    """
    # Читаем первый лист (можно расширить для нескольких листов при необходимости)
    df = pd.read_excel(excel_path, header=None, dtype=object)

    # Если файл пуст
    if df.empty:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return

    # Назначаем временные имена столбцов (0, 1, 2, ...)
    df.columns = range(df.shape[1])

    # Находим корректный столбец
    index_col, selected_rows, seq_len = find_index_column(df)

    if index_col is None:
        raise ValueError(
            "Не найден столбец с непрерывной последовательностью 1,2,3,..."
        )

    # Фильтруем только нужные строки
    filtered_df = df.loc[selected_rows].copy()

    # Обрезаем столбцы: от index_col до последнего непустого
    trimmed_df = trim_columns(filtered_df, index_col)

    # Преобразуем в список словарей для JSON
    # Используем оригинальные значения, заменяя NaN на null (что сделает json.dumps)
    records = []
    for _, row in trimmed_df.iterrows():
        record = {}
        for col in trimmed_df.columns:
            val = row[col]
            # Явно конвертируем NaN/NaT в None для корректного JSON
            if pd.isna(val):
                record[str(col)] = None
            else:
                # Сохраняем исходное значение, но приводим к базовому типу
                if isinstance(val, (np.integer, np.floating)):
                    record[str(col)] = val.item()
                else:
                    record[str(col)] = val
        records.append(record)

    # Сохраняем в JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


# === Пример использования ===
if __name__ == "__main__":
    excel_file = "Инструмент_copy.xlsx"  # замените на ваш файл
    json_file = "Инструмент_copy.xlsx.json"
    excel_to_json(excel_file, json_file)
    print(f"Данные успешно сохранены в {json_file}")
