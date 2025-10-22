import tkinter as tk
from threading import Thread
import time

def display_code(generator):
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(bg="white")

    # Frame для кнопки закрытия (чтобы разместить её в правом верхнем углу)
    header_frame = tk.Frame(root, bg="white")
    header_frame.pack(side="top", fill="x")

    # Кнопка "Закрыть" в правом верхнем углу
    close_button = tk.Button(
        header_frame,
        text="Закрыть",
        font=("Arial", 16),
        bg="red",
        fg="white",
        command=root.destroy,
        relief="raised",
        padx=10,
        pady=5
    )
    close_button.pack(side="right", anchor="ne", padx=10, pady=10)

    # Label для кода
    code_label = tk.Label(
        root,
        text="0000",
        font=("Arial", 200),
        fg="black",
        bg="white"
    )
    code_label.pack(expand=True)

    # Label для таймера
    timer_label = tk.Label(
        root,
        text="Time left: 20s",
        font=("Arial", 50),
        fg="red",
        bg="white"
    )
    timer_label.pack()

    def update_display():
        while True:
            code = generator.get_current_code()  # Получить текущий код
            remaining_time = generator.get_time_remaining()
            code_label.config(text=f"{code:04d}")  # Форматировать код до 4 цифр
            timer_label.config(text=f"Time left: {remaining_time}s")
            root.update()
            time.sleep(1)  # Обновлять каждую секунду

    # Запустить цикл обновления в отдельном потоке
    Thread(target=update_display, daemon=True).start()
    root.mainloop()