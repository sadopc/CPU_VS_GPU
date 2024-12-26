import tkinter as tk
from tkinter import ttk
import string
import itertools
import threading
import time
import numpy as np
from numba import cuda
import math

@cuda.jit
def check_password_kernel(charset_array, password_indices, length, found_array, found_index_array, start_index, batch_size):
    thread_idx = cuda.grid(1)
    if thread_idx >= batch_size:
        return

    current_idx = start_index + thread_idx

    # İndeksi şifre denemesine dönüştür
    temp_idx = current_idx
    match = True
    attempt_indices = cuda.local.array(shape=(50,), dtype=np.int32)

    for i in range(length - 1, -1, -1):
        char_idx = temp_idx % len(charset_array)
        attempt_indices[i] = char_idx
        temp_idx //= len(charset_array)

    # Şifreyi kontrol et
    if length == len(password_indices):
        for i in range(length):
            if attempt_indices[i] != password_indices[i]:
                match = False
                break
        if match:
            found_array[0] = 1
            found_index_array[0] = current_idx

class PasswordCrackerGPU_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GPU Password Cracker")
        self.root.geometry("400x350")

        # Bileşenleri oluştur ve yerleştir
        self.create_widgets()

        # Kırma işlemini durdurmak için bayrak
        self.running = False

    def create_widgets(self):
        # Şifre giriş alanı
        tk.Label(self.root, text="Kırılacak Şifreyi Girin:").pack(pady=10)
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack(pady=5)

        # Butonlar
        self.start_button = tk.Button(self.root, text="Kırmaya Başla", command=self.start_cracking)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(self.root, text="Durdur", command=self.stop_cracking, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        # İlerleme bilgileri
        tk.Label(self.root, text="Mevcut Deneme:").pack(pady=5)
        self.current_attempt_label = tk.Label(self.root, text="")
        self.current_attempt_label.pack()

        tk.Label(self.root, text="Durum:").pack(pady=5)
        self.status_label = tk.Label(self.root, text="Hazır")
        self.status_label.pack()

        tk.Label(self.root, text="Denenen Şifre Sayısı:").pack(pady=5)
        self.attempt_count_label = tk.Label(self.root, text="0")
        self.attempt_count_label.pack()

        # İlerleme çubuğu (GPU ile tam anlamıyla uyumlu değil, tahmini bir gösterge)
        self.progress_bar = ttk.Progressbar(self.root, length=300, mode='indeterminate')
        self.progress_bar.pack(pady=10)

    def check_password_gpu(self, password):
        charset = np.array(list(string.ascii_letters + string.digits))
        password_indices = np.array([np.where(charset == c)[0][0] for c in password], dtype=np.int32)
        password_length = len(password)

        found = False
        attempt = None
        tried_count = 0

        found_array = cuda.to_device(np.zeros(1, dtype=np.int32))
        found_index_array = cuda.to_device(np.zeros(1, dtype=np.int32))

        charset_device = cuda.to_device(charset)
        password_indices_device = cuda.to_device(password_indices)

        threads_per_block = 256
        blocks_per_grid = 128
        batch_size = threads_per_block * blocks_per_grid

        total_possibilities = int(math.pow(len(charset), password_length))
        current_index = np.int64(0)  # Değişiklik burada

        while current_index < total_possibilities and not found and self.running:
            try:
                check_password_kernel[blocks_per_grid, threads_per_block](
                    charset_device, password_indices_device, password_length,
                    found_array, found_index_array, np.int32(current_index),
                    np.int32(batch_size)
                )
                cuda.synchronize()

                tried_count += min(batch_size, total_possibilities - current_index)

                found_result = found_array.copy_to_host()

                if found_result[0] == 1:
                    found = True
                    found_idx = found_index_array.copy_to_host()[0]

                    temp_idx = found_idx
                    attempt = ""
                    for _ in range(password_length):
                        char_idx = temp_idx % len(charset)
                        attempt = charset[char_idx] + attempt
                        temp_idx //= len(charset)
                    break

                current_index += batch_size
                self.update_gui(attempt="", status="Kırılıyor...", attempts=tried_count)

            except OverflowError:
                self.update_gui(status="Şifre çok uzun, daha kısa bir şifre deneyin.", attempts=tried_count)
                return None, tried_count

        return attempt, tried_count

    def start_cracking(self):
        if not self.password_entry.get():
            self.status_label.config(text="Lütfen bir şifre girin")
            return

        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Kırma işlemi başlatıldı...")
        self.progress_bar.start()

        # GPU işlemini ayrı bir thread'de çalıştır
        threading.Thread(target=self.run_gpu_cracker, daemon=True).start()

    def run_gpu_cracker(self):
        password = self.password_entry.get()
        start_time = time.time()
        found_password, attempts = self.check_password_gpu(password)
        end_time = time.time()
        self.progress_bar.stop()

        if found_password:
            self.update_gui(
                attempt=found_password,
                status=f"Şifre bulundu: {found_password}\nGeçen süre: {end_time - start_time:.2f} saniye",
                attempts=attempts
            )
        elif self.running: # Kullanıcı durdurmamışsa ve bulunamadıysa
            self.update_gui(status="Şifre bulunamadı.", attempts=attempts)

        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def stop_cracking(self):
        self.running = False
        self.status_label.config(text="Kullanıcı tarafından durduruldu.")
        self.stop_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)
        self.progress_bar.stop()

    def update_gui(self, attempt="", status="", attempts=0):
        if attempt:
            self.current_attempt_label.config(text=attempt)
        if status:
            self.status_label.config(text=status)
        self.attempt_count_label.config(text=f"{attempts:,}")
        self.root.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordCrackerGPU_GUI(root)
    root.mainloop()