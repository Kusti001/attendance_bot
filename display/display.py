import tkinter as tk
from threading import Thread
import time

def display_code(generator):
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(bg="white")

    # Label for the code
    code_label = tk.Label(
        root,
        text="0000",
        font=("Arial", 200),
        fg="black",
        bg="white"
    )
    code_label.pack(expand=True)

    # Label for the countdown timer
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
            code = generator.get_current_code()  # Get current or new code
            remaining_time = generator.get_time_remaining()
            code_label.config(text=f"{code:04d}")  # Format code to 4 digits
            timer_label.config(text=f"Time left: {remaining_time}s")
            root.update()
            time.sleep(1)  # Update every second for smooth countdown

    # Start the update loop in a separate thread
    Thread(target=update_display, daemon=True).start()
    root.mainloop()