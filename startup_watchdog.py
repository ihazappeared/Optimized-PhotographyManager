import sys
import os
import subprocess
import winreg
import signal
import psutil
from pathlib import Path

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal

from typing import Optional
from config import REG_NAME, WINDOWS_RUN_KEY, main_icon

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class NewFileHandler(FileSystemEventHandler):
    def __init__(self, organizer: 'PhotoOrganizer') -> None:
        super().__init__()
        self.organizer = organizer

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        self.organizer._log(f"New file detected: {event.src_path}")
        self.organizer.organize_file(event.src_path)


class WindowsFileWatchdog(QObject):
    log_msg = Signal(str)

    def __init__(self, watch_dir: Path, organizer: 'PhotoOrganizer') -> None:
        super().__init__()
        self.watch_dir = watch_dir
        self.organizer = organizer
        self.observer: Optional[Observer] = None

    def start(self) -> None:
            if self.observer and self.observer.is_alive():
                self.log_msg.emit("Observer already running.")
                return
            self.observer = Observer()
            handler = NewFileHandler(self.organizer)
            self.observer.schedule(handler, str(self.watch_dir), recursive=True)
            self.observer.start()
            self.log_msg.emit(f"Started watching {self.watch_dir}")

    def stop(self) -> None:
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.log_msg.emit("Stopped file watching.")

def get_pythonw_exe() -> Path:
    python_exe = Path(sys.executable)
    return python_exe.with_name("pythonw.exe") if python_exe.name == "python.exe" else python_exe

def launch_watchdog() -> None:
    subprocess.Popen(
        [str(get_pythonw_exe()), str(Path(__file__).resolve())],
        close_fds=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print("Watchdog process launched.")


def kill_watchdog_process() -> None:
    current_pid = os.getpid()
    script_name = Path(__file__).name
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.pid == current_pid:
                continue
            cmdline = proc.info['cmdline']
            if cmdline and any(script_name in part for part in cmdline):
                proc.send_signal(signal.SIGTERM)
                print(f"Killed watchdog process PID {proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def install_watchdog() -> None:
    command = f'"{get_pythonw_exe()}" "{Path(__file__).resolve()}"'
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, command)
    print(f"Installed watchdog to startup: {command}")
    launch_watchdog()



def uninstall_watchdog() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, REG_NAME)
        print("Uninstalled watchdog from startup.")
    except FileNotFoundError:
        print("Watchdog not found in startup registry.")
    kill_watchdog_process()


def is_watchdog_installed() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
            winreg.QueryValueEx(key, REG_NAME)
            return True
    except FileNotFoundError:
        return False


def launch_main_app() -> None:
    base_dir = Path(__file__).resolve().parent
    main_py = base_dir / "main.py"

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and sys.executable in cmdline and str(main_py) in cmdline:
                print(f"Main app already running (PID {proc.pid})")
                return
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if main_py.exists():
        subprocess.Popen([sys.executable, str(main_py)], close_fds=True)
        print(f"Launched main app: {main_py}")
    else:
        print(f"Main app not found at {main_py}")


def create_tray_icon():
    app = QApplication(sys.argv)
    icon = main_icon
    if icon.isNull():
        icon = QIcon()
    tray_icon = QSystemTrayIcon(icon)
    tray_icon.setVisible(True)
    
    menu = QMenu()
    open_action = QAction("Open Main App")
    open_action.triggered.connect(launch_main_app)
    menu.addAction(open_action)

    quit_action = QAction("Quit Background Process")
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray_icon.setContextMenu(menu)
    app.aboutToQuit.connect(lambda: print("Application is quitting..."))
    sys.exit(app.exec())

if __name__ == "__main__":
    create_tray_icon()
