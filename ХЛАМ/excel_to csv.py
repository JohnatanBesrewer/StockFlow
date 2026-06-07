import pandas as pd

# Укажите путь к вашему Excel-файлу
input_file = "УПД.xls"  # замените на путь к вашему файлу
output_file = "УПД.csv"  # имя выходного CSV-файла

# Определяем engine в зависимости от расширения
if input_file.lower().endswith(".xlsx"):
    df = pd.read_excel(input_file, engine="openpyxl")
elif input_file.lower().endswith(".xls"):
    # xlrd поддерживает .xls только в версиях <= 1.2.0
    df = pd.read_excel(input_file, engine="xlrd")
else:
    raise ValueError("Неподдерживаемый формат файла. Используйте .xls или .xlsx")

# Сохраняем в CSV без индекса и без форматирования
df.to_csv(output_file, index=False, encoding="utf-8", sep="#")

print(f"Файл успешно сохранён как {output_file}")
