import tkinter as tk
from tkinter import ttk
import string
import itertools
import threading
import time

class PasswordCrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Password Cracker")
        self.root.geometry("400x300")

        # Create and pack widgets
        self.create_widgets()

        # Flag for stopping the cracking process
        self.running = False
        self.attempt_count = 0  # Initialize attempt counter

    def create_widgets(self):
        # Password input
        tk.Label(self.root, text="Enter Password to Crack:").pack(pady=10)
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack(pady=5)

        # Buttons
        self.start_button = tk.Button(self.root, text="Start Cracking", command=self.start_cracking)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(self.root, text="Stop", command=self.stop_cracking, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        # Progress information
        tk.Label(self.root, text="Attempt Count:").pack(pady=5)
        self.attempt_count_label = tk.Label(self.root, text="0")  # Display attempt count
        self.attempt_count_label.pack()

        tk.Label(self.root, text="Status:").pack(pady=5)
        self.status_label = tk.Label(self.root, text="Ready")
        self.status_label.pack()

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.root, length=300, mode='indeterminate')
        self.progress_bar.pack(pady=10)

    def check_password(self, attempt, password):
        return attempt == password

    def brute_force(self):
        password = self.password_entry.get()
        charset = string.ascii_letters + string.digits
        start_time = time.time()

        try:
            for length in range(1, len(password) + 1):
                if not self.running:
                    break
                for attempt in itertools.product(charset, repeat=length):
                    if not self.running:
                        break

                    self.attempt_count += 1  # Increment attempt counter

                    # Update GUI with attempt count
                    self.attempt_count_label.config(text=str(self.attempt_count))
                    self.root.update_idletasks()  # Update GUI immediately

                    attempt_str = ''.join(attempt)

                    if self.check_password(attempt_str, password):
                        end_time = time.time()
                        self.status_label.config(
                            text=f"Password found: {attempt_str}\n"
                                f"Attempts: {self.attempt_count}\n"
                                f"Time: {end_time - start_time:.2f} seconds"
                        )
                        self.running = False
                        break
        finally:
            self.progress_bar.stop()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if self.running:
                self.status_label.config(text="Password not found")
            self.running = False

    def start_cracking(self):
        if not self.password_entry.get():
            self.status_label.config(text="Please enter a password")
            return

        self.running = True
        self.attempt_count = 0  # Reset attempt counter on start
        self.attempt_count_label.config(text="0")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Cracking in progress...")
        self.progress_bar.start()

        # Start brute force in a separate thread
        threading.Thread(target=self.brute_force, daemon=True).start()

    def stop_cracking(self):
        self.running = False
        self.status_label.config(text="Stopped by user")
        self.stop_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordCrackerGUI(root)
    root.mainloop()