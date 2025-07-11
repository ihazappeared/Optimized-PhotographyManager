import os
import stat
import ctypes
import threading
from pathlib import Path
from multiprocessing import cpu_count

from PySide6.QtWidgets import QApplication, QWidget, QFileDialog, QMessageBox
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt, Signal
import flatten
import startup_watchdog

from config import ConfigManager
from organizer import PhotoOrganizer
from worker import WorkerThread
from ui_form import Ui_Widget


class PhotoOrganizerGUI(QWidget):
    log_signal = Signal(str)
    FOLDER_STRUCT_MAP = {0: "day", 1: "year_month_day", 2: "year_month", 3: "year_day"}
    PROGRESS_STYLE_DEFAULT = """
        QProgressBar {
            height: 22px; border: 1px solid #444; border-radius: 6px;
            text-align: center; font-weight: bold;
        }
        QProgressBar::chunk { background-color: #88c0d0; }
    """

    def __init__(self):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.config = ConfigManager.load()
        self.lock = threading.RLock()
        self._connect_signals()
        self.load_config()

    def _connect_signals(self):
        u = self.ui
        u.browse_button.clicked.connect(self.browse_base_dir)
        u.add_excluded_button.clicked.connect(self.add_excluded_folder)
        u.remove_excluded_button.clicked.connect(self.remove_selected_excluded_folders)
        u.reset_all_button.clicked.connect(self.reset_settings)
        u.start_button.clicked.connect(self.start_organizing)
        u.flatten_button.clicked.connect(self.flatten_button_clicked)
        u.clean_filenames_button.clicked.connect(self.clean_filenames_clicked)
        u.startupadd_button.clicked.connect(startup_watchdog.install_watchdog)
        u.startupremove_button.clicked.connect(startup_watchdog.uninstall_watchdog)
        self.log_signal.connect(self._append_log)

    def _append_log(self, msg):
        doc = self.ui.log_list.document()
        if doc.blockCount() > 1000:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self.ui.log_list.append(msg)
        self.ui.log_list.moveCursor(QTextCursor.End)

    def update_value(self, field, value):
        getattr(self.ui, f"{field}_lineEdit").setText(str(value))

    def browse_base_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Base Directory", self.ui.base_dir_edit.text())
        if path:
            self.ui.base_dir_edit.setText(path)
            self.save_config()

    def add_excluded_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder to Exclude", self.ui.base_dir_edit.text())
        if path and path not in self.get_excluded_folders():
            self.ui.excluded_list.addItem(path)
            self.save_config()

    def remove_selected_excluded_folders(self):
        for item in self.ui.excluded_list.selectedItems():
            self.ui.excluded_list.takeItem(self.ui.excluded_list.row(item))
        self.save_config()

    def get_excluded_folders(self):
        return [self.ui.excluded_list.item(i).text() for i in range(self.ui.excluded_list.count())]

    def start_organizing(self):
        base_dir = self.ui.base_dir_edit.text().strip()
        if not base_dir or not os.path.isdir(base_dir):
            self.log_signal.emit("Invalid base directory.")
            return

        self.save_config()
        self.organizer = PhotoOrganizer(
            base_dir=base_dir,
            folder_structure=self.FOLDER_STRUCT_MAP.get(self.ui.format_comboBox.currentIndex(), "day"),
            max_workers=min(8, cpu_count()),
            separate_videos=self.ui.sep_videos_checkbox.isChecked(),
            excluded_folders=self.get_excluded_folders()
        )
        self.organizer.progress.connect(self.ui.progress_bar.setValue)
        self.organizer.log_msg.connect(self.log_signal.emit)
        self.organizer.total_files.connect(lambda v: self.update_value("total", v))
        self.organizer.moved_files.connect(lambda v: self.update_value("moved", v))
        self.organizer.skipped_files.connect(lambda v: self.update_value("skipped", v))

        self.ui.start_button.setEnabled(False)
        self.worker_thread = WorkerThread(self.organizer)
        self.worker_thread.finished.connect(lambda: self._organizing_done(base_dir))
        self.worker_thread.start()

    def _organizing_done(self, base_dir):
        if self.ui.rem_empty_checkbox.isChecked():
            remove_empty_folders(base_dir, self.log_signal)
        self.ui.start_button.setEnabled(True)

    def reset_settings(self):
        if QMessageBox.question(self, "Confirm Reset", "Delete all settings files?") == QMessageBox.Yes:
            path = os.path.expanduser("~/.photo_organizer_config.json")
            if os.path.exists(path):
                try: os.remove(path)
                except: pass
            self.ui.excluded_list.clear()
            self.ui.progress_bar.setValue(0)
            self.ui.log_list.clear()
            self.ui.base_dir_edit.clear()
            self.ui.sep_videos_checkbox.setChecked(False)
            self.log_signal.emit("Settings reset.")

    def clean_filenames_clicked(self):
        self._run_flatten_op("cleaning filenames", lambda p: flatten.clean_img_filenames(p, recursive=True, log_fn=self.log_signal.emit))

    def flatten_button_clicked(self):
        self._run_flatten_op("flattening folders", lambda p: flatten.flatten_folder_tree(root_dir=p, target_dir=p))

    def _run_flatten_op(self, action, func):
        path = self.ui.base_dir_edit.text().strip()
        if not path or not os.path.isdir(path):
            self.log_signal.emit(f"Invalid base directory for {action}.")
            return
        try:
            func(path)
            self.log_signal.emit(f"Completed {action} under: {path}")
        except Exception as e:
            self.log_signal.emit(f"Error during {action}: {e}")

    def load_config(self):
        cfg = self.config
        self.ui.base_dir_edit.setText(cfg.get("base_dir", ""))
        idx = {v: k for k, v in self.FOLDER_STRUCT_MAP.items()}.get(cfg.get("folder_structure", "day"), 0)
        self.ui.format_comboBox.setCurrentIndex(idx)
        self.ui.sep_videos_checkbox.setChecked(cfg.get("separate_videos", False))
        self.ui.excluded_list.clear()
        for folder in cfg.get("excluded_folders", []):
            self.ui.excluded_list.addItem(folder)

    def save_config(self):
        ConfigManager.save({
            "base_dir": self.ui.base_dir_edit.text(),
            "folder_structure": self.FOLDER_STRUCT_MAP.get(self.ui.format_comboBox.currentIndex(), "day"),
            "separate_videos": self.ui.sep_videos_checkbox.isChecked(),
            "excluded_folders": self.get_excluded_folders()
        })

def remove_empty_folders(root_path: str, log_signal):
    def is_hidden_or_system(p: Path) -> bool:
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
            if attrs == -1:
                return False
            return bool(attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM))
        except Exception:
            return False

    root = Path(root_path)

    # Walk bottom-up to remove children before parents
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        current_dir = Path(dirpath)

        # Skip if current path is symlink (avoid removing real data accidentally)
        if current_dir.is_symlink():
            continue

        # Filter visible files (non-hidden/non-system)
        visible_files = [
            f for f in filenames
            if not is_hidden_or_system(current_dir / f) and not f.startswith(".")
        ]

        # Filter visible directories (non-hidden/non-system)
        visible_dirs = [
            d for d in dirnames
            if not is_hidden_or_system(current_dir / d) and not (current_dir / d).name.startswith(".")
        ]

        # Remove directory if empty (no visible files or directories)
        if not visible_files and not visible_dirs:
            try:
                current_dir.rmdir()
                log_signal.emit(f"Removed empty folder: {current_dir}")
            except PermissionError as e:
                log_signal.emit(f"Permission denied removing folder {current_dir}: {e}")
            except Exception as e:
                log_signal.emit(f"Could not remove folder {current_dir}: {e}")