import tkinter as tk
from tkinter import ttk, messagebox, filedialog


def on_button_click():
    messagebox.showinfo("Информация", "Кнопка нажата!")


def on_checkbutton_toggle():
    print("Флажок установлен" if check_var.get() else "Флажок снят")


def on_radiobutton_select():
    print(f"Выбран вариант: {radio_var.get()}")


def on_scale_change(value):
    print(f"Ползунок: {value}")


def on_listbox_select(event):
    selection = listbox.curselection()
    if selection:
        print(f"Выбран элемент: {listbox.get(selection[0])}")


def on_combobox_select(event):
    print(f"Выбрано в Combobox: {combobox.get()}")


def open_file():
    filepath = filedialog.askopenfilename()
    if filepath:
        print(f"Открыт файл: {filepath}")


# Создание главного окна
root = tk.Tk()
root.title("Демонстрация Tkinter")
root.geometry("300x400")

# Метка (Label)
label = tk.Label(root, text="Это метка", font=("Arial", 12))
label.pack(pady=5)

# Кнопка (Button)
button = tk.Button(root, text="Нажми меня", command=on_button_click)
button.pack(pady=5)

# Текстовое поле (Entry)
entry = tk.Entry(root, width=30)
entry.insert(0, "Текст по умолчанию")
entry.pack(pady=5)

# Флажок (Checkbutton)
check_var = tk.BooleanVar()
checkbutton = tk.Checkbutton(
    root, text="Флажок", variable=check_var, command=on_checkbutton_toggle
)
checkbutton.pack(pady=5)

# Переключатели (Radiobutton)
radio_var = tk.StringVar(value="1")
radio1 = tk.Radiobutton(
    root, text="Вариант 1", variable=radio_var, value="1", command=on_radiobutton_select
)
radio2 = tk.Radiobutton(
    root, text="Вариант 2", variable=radio_var, value="2", command=on_radiobutton_select
)
radio1.pack()
radio2.pack(pady=5)

# Ползунок (Scale)
scale = tk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, command=on_scale_change)
scale.set(50)
scale.pack(pady=5)

# Список (Listbox)
listbox = tk.Listbox(root, height=4)
for item in ["Элемент 1", "Элемент 2", "Элемент 3"]:
    listbox.insert(tk.END, item)
listbox.bind("<<ListboxSelect>>", on_listbox_select)
listbox.pack(pady=5)

# Выпадающий список (ttk.Combobox)
combobox = ttk.Combobox(
    root, values=["Опция A", "Опция B", "Опция C"], state="readonly"
)
combobox.set("Выберите...")
combobox.bind("<<ComboboxSelected>>", on_combobox_select)
combobox.pack(pady=5)

# Кнопка для открытия файла
file_button = tk.Button(root, text="Открыть файл...", command=open_file)
file_button.pack(pady=10)

# Запуск главного цикла обработки событий
root.mainloop()
