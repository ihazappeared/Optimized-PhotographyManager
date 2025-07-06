import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QRadioButton, QButtonGroup, QCheckBox, QListWidget,
    QProgressBar, QMessageBox, QGroupBox, QFormLayout, QSizePolicy,
    QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon, QTextCursor, QCursor

import threading
import os
import ctypes
import stat
from multiprocessing import cpu_count

from config import ConfigManager
from file_ops import FileUtils
from utils import SystemUtils
from organizer import PhotoOrganizer
from worker import WorkerThread
from ui_form import Ui_Widget
import flatten
import startup_watchdog

class PhotoOrganizerGUI(QWidget):
    # Signals
    log_signal = Signal(str)

    # Constants
    FOLDER_STRUCT_MAP = {
        0: "day",
        1: "year_month_day",
        2: "year_month",
        3: "year_day"
    }

    PROGRESS_STYLE_DEFAULT = """
        QProgressBar {
            height: 22px;
            border: 1px solid #444;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: #88c0d0;
        }
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
        self.ui.browse_button.clicked.connect(self.browse_base_dir)
        self.ui.add_excluded_button.clicked.connect(self.add_excluded_folder)
        self.ui.remove_excluded_button.clicked.connect(self.remove_selected_excluded_folders)
        self.ui.reset_all_button.clicked.connect(self.reset_settings)
        self.ui.start_button.clicked.connect(self.start_organizing)
        self.ui.flatten_button.clicked.connect(self.flatten_button_clicked)
        self.ui.clean_filenames_button.clicked.connect(self.clean_filenames_clicked)
        self.ui.startupadd_button.clicked.connect(self.add_startup_watchdog)
        self.ui.startupremove_button.clicked.connect(self.remove_startup_watchdog)
        self.log_signal.connect(self._append_log)


    def _append_log(self, message: str):
        doc = self.ui.log_list.document()
        max_blocks = 1000
        if doc.blockCount() > max_blocks:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self.ui.log_list.append(message)
        self.ui.log_list.moveCursor(QTextCursor.End)

    def update_value(self, field: str, value: int):
        if field == "total":
            self.ui.total_lineEdit.setText(str(value))
        elif field == "moved":
            self.ui.moved_lineEdit.setText(str(value))
        elif field == "skipped":
            self.ui.skipped_lineEdit.setText(str(value))

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

    def add_startup_watchdog(self):
        startup_watchdog.install_watchdog()

    def remove_startup_watchdog(self):
        startup_watchdog.uninstall_watchdog()

    def cancel_organizing(self):
        if hasattr(self, "organizer"):
            self.ui.progress_bar.setFormat("Cancelling...")
            self.ui.progress_bar.setStyleSheet(self.PROGRESS_STYLE_CANCEL)
            self.log_signal.emit("Cancellation requested...")

    def start_organizing(self):
        base_dir = self.ui.base_dir_edit.text().strip()
        if not base_dir or not os.path.isdir(base_dir):
            self.log_signal.emit("Invalid base directory.")
            return

        self.save_config()

        folder_struct = self.FOLDER_STRUCT_MAP.get(self.ui.format_comboBox.currentIndex(), "day")
        excluded = self.get_excluded_folders()

        self.organizer = PhotoOrganizer(
            base_dir=base_dir,
            folder_structure=folder_struct,
            max_workers=min(8, cpu_count()),
            separate_videos=self.ui.sep_videos_checkbox.isChecked(),
            excluded_folders=excluded
        )
        self.organizer.progress.connect(self.ui.progress_bar.setValue)
        self.organizer.log_msg.connect(self.log_signal.emit)

        self.ui.start_button.setEnabled(False)

        self.worker_thread = WorkerThread(self.organizer)

        def on_worker_finished():
            if self.ui.rem_empty_checkbox.isChecked():
                remove_empty_folders(base_dir, self.log_signal)
            self.ui.start_button.setEnabled(True)

        self.worker_thread.finished.connect(on_worker_finished)
        self.worker_thread.start()
        
        self.organizer.total_files.connect(lambda val: self.update_value("total", val))
        self.organizer.moved_files.connect(lambda val: self.update_value("moved", val))
        self.organizer.skipped_files.connect(lambda val: self.update_value("skipped", val))

    def reset_settings(self):
        base_dir = self.ui.base_dir_edit.text().strip()
        config_path = os.path.expanduser("~/.photo_organizer_config.json")

        msg = QMessageBox(self)
        msg.setWindowTitle("Confirm Reset")
        msg.setText("Delete all settings files?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if msg.exec() == QMessageBox.Yes:
            for path in [config_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

            self.ui.excluded_list.clear()
            self.ui.progress_bar.setValue(0)
            self.ui.log_list.clear()
            self.ui.base_dir_edit.clear()
            self.ui.sep_videos_checkbox.setChecked(False)
            self.log_signal.emit("Settings reset.")

    # def setup_tray_icon(self):
    #     self.tray_icon = QSystemTrayIcon(QIcon.fromTheme("camera-photo"))  # store on self
    #     self.tray_icon.setVisible(True)

    #     tray_menu = QMenu()

    #     open_action = QAction("Open", self)
    #     open_action.triggered.connect(self.showNormal)
    #     tray_menu.addAction(open_action)

    #     quit_action = QAction("Quit", self)
    #     quit_action.triggered.connect(QApplication.instance().quit)
    #     tray_menu.addAction(quit_action)

    #     self.tray_icon.setContextMenu(tray_menu)

    #     # Optional: minimize to tray behavior
    #     self.tray_icon.activated.connect(self._on_tray_activated)

    # def _on_tray_activated(self, reason):
    #     if reason == QSystemTrayIcon.Trigger:  # single click
    #         if self.isVisible():
    #             self.hide()
    #             self.log_signal.emit("Window hidden to tray.")
    #         else:
    #             self.showNormal()
    #             self.raise_()
    #             self.activateWindow()
    #             self.log_signal.emit("Window restored from tray.")

    def clean_filenames_clicked(self):
        root_dir = self.ui.base_dir_edit.text().strip()
        if not root_dir or not os.path.isdir(root_dir):
            self.log_signal.emit("Invalid base directory for cleaning filenames.")
            return

        try:
            flatten.clean_img_filenames(root_dir, recursive=True, log_fn=self.log_signal.emit)
            self.log_signal.emit(f"Cleaned IMG filenames under: {root_dir}")
        except Exception as e:
            self.log_signal.emit(f"Error during filename cleaning: {e}")

    def flatten_button_clicked(self):
        root_dir = self.ui.base_dir_edit.text().strip()
        if not root_dir or not os.path.isdir(root_dir):
            self.log_signal.emit("Invalid base directory for flattening.")
            return

        try:
            flatten.flatten_folder_tree(root_dir=root_dir, target_dir=root_dir)
            self.log_signal.emit(f"Flattened subfolders into: {root_dir}")
        except Exception as e:
            self.log_signal.emit(f"Error during flattening: {e}")
            
    def load_config(self):
        base_dir = self.config.get("base_dir", "")
        if base_dir:
            self.ui.base_dir_edit.setText(base_dir)

        folder_structure = self.config.get("folder_structure", "day")
        reverse_map = {v: k for k, v in self.FOLDER_STRUCT_MAP.items()}
        index = reverse_map.get(folder_structure, 0)
        self.ui.format_comboBox.setCurrentIndex(index)
        self.ui.sep_videos_checkbox.setChecked(self.config.get("separate_videos", False))

        excluded = self.config.get("excluded_folders", [])
        self.ui.excluded_list.clear()
        for folder in excluded if isinstance(excluded, list) else excluded.split(','):
            self.ui.excluded_list.addItem(folder.strip())

    def save_config(self):
        folder_struct_id = self.ui.format_comboBox.currentIndex()
        folder_struct = self.FOLDER_STRUCT_MAP.get(folder_struct_id, "day")
        excluded = self.get_excluded_folders()

        config = {
            "base_dir": self.ui.base_dir_edit.text(),
            "folder_structure": folder_struct,
            "separate_videos": self.ui.sep_videos_checkbox.isChecked(),
            "excluded_folders": excluded
        }
        ConfigManager.save(config)


def remove_empty_folders(root_path: str, log_signal: Signal):
    def is_hidden_or_system(file_path):
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
            return attrs != -1 and bool(attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM))
        except Exception:
            return False

    for dirpath, dirnames, filenames in FileUtils.fast_walk(root_path, topdown=False):
        try:
            visible_files = [
                f for f in filenames
                if not is_hidden_or_system(os.path.join(dirpath, f)) and not f.startswith('.')
            ]
            if not dirnames and not visible_files:
                os.rmdir(dirpath)
                log_signal.emit(f"Removed empty folder: {dirpath}")

        except PermissionError as e:
            log_signal.emit(f"Permission denied removing folder {dirpath}: {e}")
        except Exception as e:
            log_signal.emit(f"Could not remove folder {dirpath}: {e}")
