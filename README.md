# WakeLock

**WakeLock** is a minimal Windows app I created to prevent the system from sleeping during long-running machine learning tasks or development sessions in VS Code.

## Features
- Prevents sleep using Windows API
- Auto-activates when VS Code is open
- Runtime display

## Run
```bash
pip install ttkbootstrap psutil
python wakelock.py
```

## Build .exe
```bash
python -m PyInstaller --noconsole --onefile --icon=wakelock.ico --add-data "wakelock.ico;." wakelock.py
```
