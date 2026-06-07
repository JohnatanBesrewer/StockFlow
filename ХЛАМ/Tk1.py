# === ИМПОРТЫ ===

# tkinter — стандартная библиотека Python для создания графических интерфейсов (GUI).
# tk — основной модуль, содержит базовые виджеты (окна, кнопки и т.д.)
import tkinter as tk

# ttk — тематические виджеты Tkinter (более современный внешний вид)
# filedialog — диалоговые окна для выбора файлов/папок
# messagebox — всплывающие сообщения (ошибки, подтверждения и т.п.)
from tkinter import ttk, filedialog, messagebox

# json — для работы с JSON-файлами (чтение/запись)
import json


# Пример данных (как в вашем JSON)
SAMPLE_DATA = [
    {
        "1": 1,
        "2": None,
        "3": "Насадка мотокосы - ФРЕЗА 26/9 (пропольник)  (упак 6шт)",
        # ... остальные поля ...
        "36": 4500,
    },
    {
        "1": 2,
        "3": "Тросик сцепления для бензокосы STIHL",
        "27": 5,
        "29": "шт",
        "32": 1200,
        "36": 2500,
    },
]


class ProductViewerApp:
    """
    Основной класс приложения для просмотра товаров.
    Использует объектно-ориентированный подход: всё GUI и логика инкапсулированы в классе.
    """

    def __init__(self, root):
        """
        Конструктор класса.
        :param root: корневое окно Tkinter (экземпляр tk.Tk)
        """
        self.root = root  # Сохраняем ссылку на главное окно
        self.root.title("Просмотр товаров")  # Устанавливаем заголовок окна
        self.root.geometry("1000x600")  # Устанавливаем размер окна (ширина x высота)

        # Списки для хранения данных:
        self.all_products = []  # Все товары (полный набор после загрузки)
        self.current_products = (
            []
        )  # Товары, отображаемые сейчас (может быть фильтрован поиском)

        # Создаём все виджеты интерфейса
        self.create_widgets()

        # Загружаем пример данных (в реальном приложении замените на загрузку из файла)
        self.load_sample_data()

    def create_widgets(self):
        """
        Создаёт и размещает все элементы интерфейса (виджеты).
        """
        # === Верхняя панель: поиск и кнопки ===
        # Frame — контейнер для группировки других виджетов
        top_frame = ttk.Frame(self.root)
        # pack() — менеджер геометрии: размещает виджет в окне
        # fill="x" — растягивает по горизонтали, padx/pady — отступы
        top_frame.pack(fill="x", padx=10, pady=5)

        # Метка "Поиск:"
        ttk.Label(top_frame, text="Поиск:").pack(side="left", padx=(0, 5))

        # Переменная для привязки к полю ввода (Entry)
        self.search_var = tk.StringVar()
        # Поле ввода текста (строка поиска)
        self.search_entry = ttk.Entry(
            top_frame,
            textvariable=self.search_var,  # связываем с переменной
            width=50,  # ширина в символах
        )
        # Размещаем поле: слева, растягиваем по оставшемуся месту
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        # Привязываем обработчик события: при каждом нажатии клавиши вызывается on_search
        self.search_entry.bind("<KeyRelease>", self.on_search)

        # Кнопка "Загрузить из JSON"
        ttk.Button(
            top_frame,
            text="Загрузить из JSON",
            command=self.load_from_json,  # функция, вызываемая при нажатии
        ).pack(side="right")

        # === Таблица (Treeview) ===
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Treeview — виджет для отображения табличных данных
        self.tree = ttk.Treeview(table_frame, show="headings")

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)

        # Связываем скроллбары с Treeview
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 🔧 ПРАВИЛЬНЫЙ ПОРЯДОК УПАКОВКИ:
        vsb.pack(side="right", fill="y")  # Сначала вертикальный справа
        hsb.pack(side="bottom", fill="x")  # Потом горизонтальный снизу
        self.tree.pack(side="left", fill="both", expand=True)  # И только потом Treeview

    def load_sample_data(self):
        """
        Загружает пример данных (вместо реального файла).
        В реальном приложении эта функция может быть удалена или заменена.
        """
        self.all_products = []  # SAMPLE_DATA  # раскомментируйте для теста
        self.current_products = self.all_products.copy()
        self.refresh_table()  # Обновляем отображение таблицы

    def load_from_json(self):
        """
        Открывает диалог выбора файла и загружает данные из JSON.
        """
        # Диалог выбора файла: возвращает путь или пустую строку, если отменено
        filepath = filedialog.askopenfilename(
            title="Выберите JSON-файл с товарами",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not filepath:
            return  # Пользователь отменил выбор

        try:
            # Открываем и читаем JSON-файл
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Проверяем, что данные — это список (ожидаем массив объектов)
            if isinstance(data, list):
                self.all_products = data
                self.current_products = data.copy()
                self.refresh_table()
                messagebox.showinfo("Успех", f"Загружено {len(data)} товаров.")
            else:
                messagebox.showerror("Ошибка", "Файл должен содержать массив объектов.")
        except Exception as e:
            # Любая ошибка (некорректный JSON, нет доступа и т.д.)
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{e}")

    def refresh_table(self):
        """
        Полностью перестраивает таблицу на основе current_products.
        """
        # Очищаем все строки в Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.current_products:
            return  # Нечего отображать

        # Собираем все возможные ключи (столбцы) из всех записей
        all_keys = set()
        for prod in self.current_products:
            all_keys.update(prod.keys())
        # Сортируем столбцы: числовые как числа, остальные как строки
        sorted_cols = sorted(all_keys, key=lambda x: int(x) if x.isdigit() else x)

        # Настраиваем столбцы Treeview
        self.tree["columns"] = sorted_cols  # задаём список столбцов
        for col in sorted_cols:
            # Заголовок столбца
            self.tree.heading(col, text=col)
            # Ширина и поведение при изменении размера окна
            self.tree.column(col, width=100, minwidth=50, stretch=False)

        # Добавляем строки
        for prod in self.current_products:
            # Для каждого столбца берём значение из записи или пустую строку, если None
            values = [
                prod.get(col) if prod.get(col) is not None else ""
                for col in sorted_cols
            ]
            # Вставляем строку в конец таблицы
            self.tree.insert("", "end", values=values)

    def on_search(self, event=None):
        """
        Обработчик поиска: фильтрует товары по введённому тексту.
        :param event: объект события (не используется, но передаётся при bind)
        """
        query = self.search_var.get().strip().lower()
        if not query:
            # Если строка поиска пуста — показываем все товары
            self.current_products = self.all_products.copy()
        else:
            # Иначе фильтруем: ищем совпадение в любом значении записи
            self.current_products = []
            for prod in self.all_products:
                match = False
                for val in prod.values():
                    if val is not None and str(val).lower().find(query) != -1:
                        match = True
                        break
                if match:
                    self.current_products.append(prod)
        # Обновляем таблицу
        self.refresh_table()


# Точка входа в программу
if __name__ == "__main__":
    # Создаём главное окно Tkinter
    root = tk.Tk()
    # Создаём экземпляр приложения, передавая ему окно
    app = ProductViewerApp(root)
    # Запускаем главный цикл обработки событий GUI
    root.mainloop()
