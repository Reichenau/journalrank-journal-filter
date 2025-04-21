# импорты библиотек
import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from journal_filter import filter_journals_by_criteria
from journal_updater import update_journals
import threading

def create_gui():
    """Создание и запуск основного GUI приложения"""
    root = tk.Tk()
    root.title("Фильтр журналов")
    root.geometry("400x250")
    root.resizable(False, False)
    
    JournalRankApp(root)
    
    root.mainloop()


class JournalRankApp:
    def __init__(self, root):
        self.root = root
        
        # Переменные для уровней белого списка
        self.level_vars = {}
        for level in range(1, 5):
            self.level_vars[level] = tk.BooleanVar(value=False)
        
        # Переменная для RSCI
        self.in_rsci_var = tk.StringVar(value="all")
        
        # Создание интерфейса
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Фрейм для уровней белого списка
        white_list_frame = ttk.LabelFrame(main_frame, text="Уровень белого списка")
        white_list_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # чекбоксы для уровней
        white_list_inner = ttk.Frame(white_list_frame)
        white_list_inner.pack(fill=tk.X, pady=5)
        
        for level in range(1, 5):
            cb = ttk.Checkbutton(
                white_list_inner,
                text=f"у{level}",
                variable=self.level_vars[level]
            )
            cb.grid(row=0, column=level-1, padx=10)
        
        # Фрейм для RSCI
        rsci_frame = ttk.LabelFrame(main_frame, text="RSCI")
        rsci_frame.pack(fill=tk.X, pady=5, padx=5)
        
        rsci_inner = ttk.Frame(rsci_frame)
        rsci_inner.pack(fill=tk.X, pady=5)
        
        # Радиокнопки для RSCI
        rb_all = ttk.Radiobutton(
            rsci_inner,
            text="Все",
            variable=self.in_rsci_var,
            value="all"
        )
        rb_all.grid(row=0, column=0, padx=10)
        
        rb_yes = ttk.Radiobutton(
            rsci_inner,
            text="Только в RSCI",
            variable=self.in_rsci_var,
            value="yes"
        )
        rb_yes.grid(row=0, column=1, padx=10)
        
        rb_no = ttk.Radiobutton(
            rsci_inner,
            text="Не в RSCI",
            variable=self.in_rsci_var,
            value="no"
        )
        rb_no.grid(row=0, column=2, padx=10)
        
        # Кнопки
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        self.status_var = tk.StringVar(value="Готово к работе")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        self.filter_button = ttk.Button(
            buttons_frame,
            text="Применить фильтр",
            command=self.apply_filter
        )
        self.filter_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="Обновить журналы",
            command=self.update_journals
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="Выход",
            command=self.root.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
    def apply_filter(self):
        selected_levels = [level for level, var in self.level_vars.items() 
                          if var.get()]
        
        # Если ничего не выбрано, используем все уровни
        if not selected_levels:
            selected_levels = list(range(1, 5))
            
        # Определяем фильтр для RSCI
        in_rsci = None
        if self.in_rsci_var.get() == "yes":
            in_rsci = True
        elif self.in_rsci_var.get() == "no":
            in_rsci = False
        
        self.status_var.set("Фильтрация журналов...")
        self.root.update()
        
        # Применяем фильтр
        try:
            result_file = filter_journals_by_criteria(selected_levels, in_rsci)
            if result_file:
                self.status_var.set(f"Журналы сохранены: {result_file}")
                messagebox.showinfo(
                    "Успех", 
                    f"Журналы сохранены: {result_file}"
                )
            else:
                self.status_var.set("Ошибка при фильтрации журналов")
                messagebox.showerror(
                    "Ошибка", 
                    "Не удалось отфильтровать журналы"
                )
        except Exception as e:
            self.status_var.set(f"Ошибка: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
    
    def update_journals(self):
        self.status_var.set("Обновление списка журналов...")
        self.filter_button.config(state=tk.DISABLED)
        self.root.update()
        
        def update_task():
            try:
                result_file = update_journals()
                
                if result_file:
                    self.root.after(0, lambda: self.status_var.set(
                        f"Журналы обновлены: {result_file}"
                    ))
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Успех", 
                        f"Журналы обновлены: {result_file}"
                    ))
                else:
                    self.root.after(0, lambda: self.status_var.set(
                        "Ошибка при обновлении журналов"
                    ))
                    self.root.after(0, lambda: messagebox.showerror(
                        "Ошибка", 
                        "Не удалось обновить журналы"
                    ))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(
                    f"Ошибка: {str(e)}"
                ))
                self.root.after(0, lambda: messagebox.showerror(
                    "Ошибка", 
                    f"Ошибка: {str(e)}"
                ))
            finally:
                self.root.after(0, lambda: self.filter_button.config(
                    state=tk.NORMAL
                ))
        
        update_thread = threading.Thread(target=update_task)
        update_thread.daemon = True  
        update_thread.start()
    
    def open_filtered_journals(self):
        filename = "filtered_journals.xlsx"
        if os.path.exists(filename):
            try:
                if sys.platform.startswith('win'):
                    os.startfile(filename)
                
                self.status_var.set(f"Открыт файл {filename}")
            except Exception:
                self.status_var.set("Ошибка при открытии файла")
                messagebox.showerror(
                    "Ошибка", 
                    "Не удалось открыть файл"
                )


if __name__ == "__main__":
    try:
        create_gui()
    except Exception as error:
        print(f"Произошла ошибка: {error}")
        print("Программа завершила работу с ошибкой") 