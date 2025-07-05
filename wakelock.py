import ctypes
import threading
import time
import psutil
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import timedelta, datetime
import os
import sys

# Windows API flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

# Helper to get correct icon path (works in PyInstaller)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # when bundled by PyInstaller
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class WakeLockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WakeLock")
        self.root.geometry("400x260")
        self.root.resizable(False, False)

        self.running = False
        self.auto_vscode_enabled = False
        self.start_time = None
        self.elapsed_seconds = 0

        self.prevent_thread = None
        self.timer_thread = None
        self.vscode_monitor_thread = threading.Thread(target=self.vscode_watcher, daemon=True)

        # UI
        self.frame = ttk.Frame(self.root, padding=20)
        self.frame.pack(fill=BOTH, expand=True)

        self.status_label = ttk.Label(self.frame, text="Status: Stopped", font=("Segoe UI", 13))
        self.status_label.pack(pady=10)

        self.time_label = ttk.Label(self.frame, text="Runtime: 00:00:00", font=("Segoe UI", 11))
        self.time_label.pack(pady=5)

        self.toggle_button = ttk.Button(self.frame, text="Start", bootstyle="success", command=self.toggle)
        self.toggle_button.pack(pady=5, ipadx=10, ipady=4)

        self.auto_check = ttk.Checkbutton(
            self.frame,
            text="Auto-run when VS Code is open",
            bootstyle="info-round-toggle",
            command=self.toggle_vscode_mode
        )
        self.auto_check.pack(pady=10)

    def prevent_sleep(self):
        while self.running:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
            )
            time.sleep(60)

    def update_timer(self):
        while self.running:
            elapsed = datetime.now() - self.start_time
            formatted = str(timedelta(seconds=int(elapsed.total_seconds())))
            self.root.after(0, lambda: self.time_label.config(text=f"Runtime: {formatted}"))
            time.sleep(1)

    def toggle(self):
        if not self.running:
            self.running = True
            self.start_time = datetime.now()
            self.status_label.config(text="Status: Running")
            self.toggle_button.config(text="Stop", bootstyle="danger")

            self.prevent_thread = threading.Thread(target=self.prevent_sleep, daemon=True)
            self.prevent_thread.start()

            self.timer_thread = threading.Thread(target=self.update_timer, daemon=True)
            self.timer_thread.start()
        else:
            self.running = False
            self.status_label.config(text="Status: Stopped")
            self.toggle_button.config(text="Start", bootstyle="success")
            self.time_label.config(text="Runtime: 00:00:00")

    def toggle_vscode_mode(self):
        self.auto_vscode_enabled = not self.auto_vscode_enabled
        if self.auto_vscode_enabled and not self.vscode_monitor_thread.is_alive():
            self.vscode_monitor_thread = threading.Thread(target=self.vscode_watcher, daemon=True)
            self.vscode_monitor_thread.start()

    def vscode_watcher(self):
        while self.auto_vscode_enabled:
            vscode_running = any("Code.exe" in p.name() for p in psutil.process_iter())
            if vscode_running and not self.running:
                print("[VSCode detected] Auto-starting WakeLock...")
                self.root.after(0, self.toggle)
            elif not vscode_running and self.running:
                print("[VSCode closed] Auto-stopping WakeLock...")
                self.root.after(0, self.toggle)
            time.sleep(10)

# Run the GUI
if __name__ == "__main__":
    app = ttk.Window(themename="darkly")

    # Use absolute icon path that works for both .py and .exe
    icon_path = resource_path("wakelock.ico")
    app.iconbitmap(icon_path)

    WakeLockApp(app)
    app.mainloop()
