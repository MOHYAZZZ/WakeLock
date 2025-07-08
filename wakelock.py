import ctypes
import threading
import time
import psutil
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import timedelta, datetime
import os
import sys
import webbrowser

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

THEMES = {
    "Dark": "darkly",
    "Light": "flatly"
}

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class WakeLockApp:
    def __init__(self, root, initial_theme):
        self.root = root
        self.root.title("WakeLock")
        self.root.geometry("400x300")
        self.root.resizable(False, False)

        # --- Menu Bar ---
        self.menubar = ttk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self.helpmenu = ttk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label="About WakeLock...", command=self.show_about)
        self.menubar.add_cascade(label="Help", menu=self.helpmenu)

        # Thread control events
        self.running_event = threading.Event()
        self.auto_vscode_event = threading.Event()

        self.start_time = None
        self.prevent_thread = None
        self.timer_thread = None
        self.vscode_monitor_thread = None

        # --- Theme Switcher ---
        self.theme_var = ttk.StringVar(value=initial_theme)
        self.theme_frame = ttk.Frame(self.root, padding=(20, 8, 20, 0))
        self.theme_frame.pack(fill=X)
        ttk.Label(self.theme_frame, text="Theme:").pack(side=LEFT, padx=(0, 10))
        self.theme_menu = None
        self.create_theme_menu()

        # UI
        self.frame = ttk.Frame(self.root, padding=20)
        self.frame.pack(fill=BOTH, expand=True)

        self.status_label = ttk.Label(self.frame, text="Status: Stopped", font=("Segoe UI", 13))
        self.status_label.pack(pady=10)

        self.time_label = ttk.Label(self.frame, text="Runtime: 00:00:00", font=("Segoe UI", 11))
        self.time_label.pack(pady=5)

        self.toggle_button = ttk.Button(self.frame, text="Start", bootstyle="success", command=self.toggle)
        self.toggle_button.pack(pady=5, ipadx=10, ipady=4)

        self.auto_var = ttk.BooleanVar(value=True)
        self.auto_check = ttk.Checkbutton(
            self.frame,
            text="Auto-run when VS Code is open",
            bootstyle="info-round-toggle",
            command=self.toggle_vscode_mode,
            variable=self.auto_var
        )
        self.auto_check.pack(pady=10)

        # Start the VSCode watcher thread
        self.start_vscode_monitor()

        # Clean shutdown on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_theme_menu(self):
        # Remove old OptionMenu if it exists
        if self.theme_menu:
            self.theme_menu.destroy()
        bootstyle = "dark" if self.theme_var.get() == "Dark" else "light"
        self.theme_menu = ttk.OptionMenu(
            self.theme_frame,
            self.theme_var,
            self.theme_var.get(),
            *THEMES.keys(),
            command=self.change_theme,
            bootstyle=bootstyle
        )
        self.theme_menu.pack(side=LEFT)

    def change_theme(self, selected):
        themename = THEMES[self.theme_var.get()]
        self.root.style.theme_use(themename)
        self.create_theme_menu()  # Re-create menu for correct styling

    def start_vscode_monitor(self):
        self.auto_vscode_event.set()
        if not self.vscode_monitor_thread or not self.vscode_monitor_thread.is_alive():
            self.vscode_monitor_thread = threading.Thread(target=self.vscode_watcher, daemon=True)
            self.vscode_monitor_thread.start()

    def stop_vscode_monitor(self):
        self.auto_vscode_event.clear()
        if self.vscode_monitor_thread and self.vscode_monitor_thread.is_alive():
            self.vscode_monitor_thread.join(timeout=2)

    def prevent_sleep(self):
        while self.running_event.is_set():
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
            )
            for _ in range(60):
                if not self.running_event.is_set():
                    break
                time.sleep(1)

    def update_timer(self):
        while self.running_event.is_set():
            elapsed = datetime.now() - self.start_time
            formatted = str(timedelta(seconds=int(elapsed.total_seconds())))
            self.root.after(0, lambda: self.time_label.config(text=f"Runtime: {formatted}"))
            for _ in range(1):
                if not self.running_event.is_set():
                    break
                time.sleep(1)

    def toggle(self):
        if not self.running_event.is_set():
            self.running_event.set()
            self.start_time = datetime.now()
            self.status_label.config(text="Status: Running")
            self.toggle_button.config(text="Stop", bootstyle="danger")

            self.prevent_thread = threading.Thread(target=self.prevent_sleep, daemon=True)
            self.timer_thread = threading.Thread(target=self.update_timer, daemon=True)
            self.prevent_thread.start()
            self.timer_thread.start()
        else:
            self.running_event.clear()
            self.status_label.config(text="Status: Stopped")
            self.toggle_button.config(text="Start", bootstyle="success")
            self.time_label.config(text="Runtime: 00:00:00")
            # Wait for threads to exit
            if self.prevent_thread and self.prevent_thread.is_alive():
                self.prevent_thread.join(timeout=2)
            if self.timer_thread and self.timer_thread.is_alive():
                self.timer_thread.join(timeout=2)

    def toggle_vscode_mode(self):
        enabled = self.auto_var.get()
        if enabled:
            self.auto_vscode_event.set()
            self.start_vscode_monitor()
        else:
            self.auto_vscode_event.clear()

    def vscode_watcher(self):
        while self.auto_vscode_event.is_set():
            vscode_running = any("code" in p.name().lower() for p in psutil.process_iter())
            if vscode_running and not self.running_event.is_set():
                print("[VSCode detected] Auto-starting WakeLock...")
                self.root.after(0, self.toggle)
            elif not vscode_running and self.running_event.is_set():
                print("[VSCode closed] Auto-stopping WakeLock...")
                self.root.after(0, self.toggle)
            for _ in range(10):
                if not self.auto_vscode_event.is_set():
                    break
                time.sleep(1)

    def show_about(self):
        # Prevent multiple About windows
        if hasattr(self, '_about_win') and self._about_win and self._about_win.winfo_exists():
            self._about_win.lift()
            return

        self._about_win = ttk.Toplevel(self.root)
        self._about_win.title("About WakeLock")
        self._about_win.geometry("400x300")  # Increased size
        self._about_win.resizable(False, False)
        self._about_win.transient(self.root)
        self._about_win.grab_set()

        # Icon (emoji, or replace with your own image)
        icon_label = ttk.Label(self._about_win, text="💡", font=("Segoe UI Emoji", 20))
        icon_label.pack(pady=(18, 4))

        # App name and version
        name_label = ttk.Label(
            self._about_win, 
            text="WakeLock v1.0",
            font=("Segoe UI", 14, "bold"),
            justify="center"
        )
        name_label.pack()

        # Info (wrap text and center)
        info = (
            "Prevents your PC from sleeping while running, or when VS Code is open.\n\n"
            "Created by MOHYAZZZ."
        )
        info_label = ttk.Label(
            self._about_win,
            text=info,
            font=("Segoe UI", 9),
            justify="center",
            anchor="center",
            wraplength=300  # Wraps text for readability
        )
        info_label.pack(pady=(8, 8))

        # GitHub link as a button
        def open_github(event=None):
            webbrowser.open("https://github.com/MOHYAZZZ/WakeLock")
            self._about_win.destroy()

        github_btn = ttk.Button(
            self._about_win,
            text="View on GitHub",
            bootstyle="info-outline",
            command=open_github
        )
        github_btn.pack(pady=(0, 16))

        # OK/Close button
        close_btn = ttk.Button(self._about_win, text="OK", command=self._about_win.destroy, bootstyle="secondary")
        close_btn.pack(pady=(0, 12))

        # Center the window relative to the main app
        self._about_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - self._about_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - self._about_win.winfo_height()) // 2
        self._about_win.geometry(f"+{x}+{y}")

    def on_close(self):
        self.auto_vscode_event.clear()
        self.running_event.clear()
        if self.vscode_monitor_thread and self.vscode_monitor_thread.is_alive():
            self.vscode_monitor_thread.join(timeout=2)
        if self.prevent_thread and self.prevent_thread.is_alive():
            self.prevent_thread.join(timeout=2)
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=2)
        self.root.destroy()

if __name__ == "__main__":
    # Default to Dark theme on startup
    initial_theme = "Dark"
    app = ttk.Window(themename=THEMES[initial_theme])
    try:
        icon_path = resource_path("wakelock.ico")
        app.iconbitmap(icon_path)
    except Exception as e:
        print(f"Could not set icon: {e}")
    WakeLockApp(app, initial_theme)
    app.mainloop()
