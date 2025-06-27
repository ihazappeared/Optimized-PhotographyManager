from PySide6.QtGui import QTextCursor, QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QRadioButton, QButtonGroup, QCheckBox, QListWidget,
    QProgressBar, QMessageBox, QGroupBox, QFormLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

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
import flatten


class PhotoOrganizerGUI(QWidget):
    # Signals
    log_signal = Signal(str)

    # Constants
    FOLDER_STRUCT_MAP = {
        0: "day",
        1: "month_day",
        2: "year_month_day",
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

    PROGRESS_STYLE_CANCEL = """
        QProgressBar::chunk {
            background-color: red;
        }
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Organizer")
        self.resize(1000, 680)
        self.setStyleSheet("QWidget { font-size: 12px; }")

        self.config = ConfigManager.load()
        self.lock = threading.RLock()
        self.existing_files = set()

        self._init_widgets()
        self._connect_signals()
        self._build_main_layout()
        self.load_config()

    # -----------------------
    # Initialization Methods
    # -----------------------

    def _init_widgets(self):
        # Base directory selection
        self.base_dir_edit = QLineEdit()
        self.browse_button = QPushButton("Browse")

        # Folder structure radio buttons
        self.folder_struct_group = QButtonGroup(self)
        self.radio_day = QRadioButton("Day (DD-MM-YYYY)")
        self.radio_month_day = QRadioButton("Month/Day (YYYY/Month/DD)")
        self.radio_year_month_day = QRadioButton("Year/Month/Day (YYYY/MM/DD)")
        self.radio_year_day = QRadioButton("Year/Day of Year (YYYY/DDD)")
        self.radio_day.setChecked(True)
        for i, rb in enumerate([
            self.radio_day, self.radio_month_day,
            self.radio_year_month_day, self.radio_year_day
        ]):
            self.folder_struct_group.addButton(rb, i)

        # Options checkboxes
        self.video_separate_checkbox = QCheckBox("Separate Videos")
        self.remove_empty_folders_checkbox = QCheckBox("Remove Empty Folders")
        self.onedrive_warning_checkbox = QCheckBox("Warn if OneDrive is Running")

        # Excluded folders list and controls
        self.excluded_folders_list = QListWidget()
        self.excluded_folders_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.add_excluded_button = QPushButton("Add Folder")
        self.remove_excluded_button = QPushButton("Remove Selected")

        # Action buttons
        self.reset_all_button = QPushButton("Reset All Settings")
        self.flatten_button = QPushButton("Flatten Structure")
        self.clean_filenames_button = QPushButton("Clean Filenames")
        self.start_button = QPushButton("Start")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setFont(QFont("Courier", 10))

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setOrientation(Qt.Horizontal)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(self.PROGRESS_STYLE_DEFAULT)

    def _connect_signals(self):
        self.browse_button.clicked.connect(self.browse_base_dir)
        self.add_excluded_button.clicked.connect(self.add_excluded_folder)
        self.remove_excluded_button.clicked.connect(self.remove_selected_excluded_folders)
        self.reset_all_button.clicked.connect(self.reset_cache_and_settings)
        self.start_button.clicked.connect(self.start_organizing)
        self.flatten_button.clicked.connect(self.flatten_button_clicked)
        self.clean_filenames_button.clicked.connect(self.clean_filenames_clicked)
        self.cancel_button.clicked.connect(self.cancel_organizing)
        self.log_signal.connect(self._append_log)

    def _build_main_layout(self):
        layout = QVBoxLayout()

        layout.addWidget(self._build_path_group())
        layout.addWidget(self._build_folder_struct_group())
        layout.addWidget(self._build_options_group())
        layout.addWidget(self._build_excluded_group())
        layout.addWidget(self._build_controls_group())
        layout.addWidget(QLabel("Log Output:"))
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    # -----------------------
    # Layout Group Builders
    # -----------------------

    def _build_path_group(self):
        box = QGroupBox("Base Directory")
        form = QHBoxLayout()
        form.addWidget(self.base_dir_edit)
        form.addWidget(self.browse_button)
        box.setLayout(form)
        return box

    def _build_folder_struct_group(self):
        box = QGroupBox("Folder Structure Format")
        layout = QHBoxLayout()
        layout.addWidget(self.radio_day)
        layout.addWidget(self.radio_month_day)
        layout.addWidget(self.radio_year_month_day)
        layout.addWidget(self.radio_year_day)
        layout.addStretch()
        box.setLayout(layout)
        return box

    def _build_options_group(self):
        box = QGroupBox("Options")
        layout = QHBoxLayout()
        layout.addWidget(self.video_separate_checkbox)
        layout.addWidget(self.remove_empty_folders_checkbox)
        layout.addWidget(self.onedrive_warning_checkbox)
        layout.addStretch()
        box.setLayout(layout)
        return box

    def _build_excluded_group(self):
        box = QGroupBox("Excluded Folders")
        layout = QVBoxLayout()
        layout.addWidget(self.excluded_folders_list)

        btns = QHBoxLayout()
        btns.addWidget(self.add_excluded_button)
        btns.addWidget(self.remove_excluded_button)

        layout.addLayout(btns)
        box.setLayout(layout)
        return box

    def _build_controls_group(self):
        box = QGroupBox("Actions")
        layout = QVBoxLayout()
        layout.addWidget(self.flatten_button)
        layout.addWidget(self.clean_filenames_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.reset_all_button)
        layout.addWidget(self.progress_bar)
        box.setLayout(layout)
        return box

    # -----------------------
    # Logging
    # -----------------------

    def _append_log(self, message: str):
        if self.log_text.document().blockCount() > 1000:
            self.log_text.clear()
            self.log_text.append("[Log truncated]")
        self.log_text.append(message)
        self.log_text.moveCursor(QTextCursor.End)

    # -----------------------
    # UI Interaction Methods
    # -----------------------

    def browse_base_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Base Directory", self.base_dir_edit.text())
        if path:
            self.base_dir_edit.setText(path)

    def add_excluded_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder to Exclude", self.base_dir_edit.text())
        if path and path not in self.get_excluded_folders():
            self.excluded_folders_list.addItem(path)

    def remove_selected_excluded_folders(self):
        for item in self.excluded_folders_list.selectedItems():
            self.excluded_folders_list.takeItem(self.excluded_folders_list.row(item))

    def get_excluded_folders(self):
        return [self.excluded_folders_list.item(i).text() for i in range(self.excluded_folders_list.count())]

    def cancel_organizing(self):
        if hasattr(self, "organizer"):
            self.progress_bar.setFormat("Cancelling...")
            self.progress_bar.setStyleSheet(self.PROGRESS_STYLE_CANCEL)
            self.log_signal.emit("Cancellation requested...")

    # -----------------------
    # Core Functionality
    # -----------------------

    def start_organizing(self):
        base_dir = self.base_dir_edit.text().strip()
        if not base_dir or not os.path.isdir(base_dir):
            self.log_signal.emit("Invalid base directory.")
            return

        if self.onedrive_warning_checkbox.isChecked() and SystemUtils.is_onedrive_running():
            self.log_signal.emit("[WARNING] OneDrive is running. This may interfere with file operations.")

        self.save_config()

        folder_struct = self.FOLDER_STRUCT_MAP.get(self.folder_struct_group.checkedId(), "day")
        excluded = self.get_excluded_folders()

        self.organizer = PhotoOrganizer(
            base_dir=base_dir,
            folder_structure=folder_struct,
            max_workers=min(8, cpu_count()),
            separate_videos=self.video_separate_checkbox.isChecked(),
            excluded_folders=excluded
        )
        self.organizer.progress.connect(self.progress_bar.setValue)
        self.organizer.log_msg.connect(self.log_signal.emit)

        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        self.worker_thread = WorkerThread(self.organizer)

        def on_worker_finished():
            self.progress_bar.setFormat("%p%")
            self.progress_bar.setStyleSheet(self.PROGRESS_STYLE_DEFAULT)
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)

            if self.remove_empty_folders_checkbox.isChecked():
                remove_empty_folders(base_dir, self.log_signal)

        self.worker_thread.finished.connect(on_worker_finished)
        self.worker_thread.start()

    def reset_cache_and_settings(self):
        base_dir = self.base_dir_edit.text().strip()
        config_path = os.path.expanduser("~/.photo_organizer_config.json")
        cache_path = os.path.join(base_dir, ".photo_metadata_cache.db") if base_dir else None

        msg = QMessageBox(self)
        msg.setWindowTitle("Confirm Reset")
        msg.setText("Delete all settings and cache files?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if msg.exec() == QMessageBox.Yes:
            for path in [config_path, cache_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

            self.excluded_folders_list.clear()
            self.progress_bar.setValue(0)
            self.log_text.clear()
            self.base_dir_edit.clear()
            self.video_separate_checkbox.setChecked(False)
            self.radio_day.setChecked(True)
            self.log_signal.emit("Settings and cache reset.")

    def clean_filenames_clicked(self):
        root_dir = self.base_dir_edit.text().strip()
        if not root_dir or not os.path.isdir(root_dir):
            self.log_signal.emit("Invalid base directory for cleaning filenames.")
            return

        try:
            flatten.clean_img_filenames(root_dir, recursive=True, log_fn=self.log_signal.emit)
            self.log_signal.emit(f"Cleaned IMG filenames under: {root_dir}")
        except Exception as e:
            self.log_signal.emit(f"Error during filename cleaning: {e}")

    def flatten_button_clicked(self):
        root_dir = self.base_dir_edit.text().strip()
        if not root_dir or not os.path.isdir(root_dir):
            self.log_signal.emit("Invalid base directory for flattening.")
            return

        try:
            flatten.flatten_folder_tree(root_dir=root_dir, target_dir=root_dir)
            self.log_signal.emit(f"Flattened subfolders into: {root_dir}")
        except Exception as e:
            self.log_signal.emit(f"Error during flattening: {e}")

    # -----------------------
    # Config Persistence
    # -----------------------

    def load_config(self):
        self.onedrive_warning_checkbox.setChecked(self.config.get("warn_onedrive", True))

        base_dir = self.config.get("base_dir", "")
        if base_dir:
            self.base_dir_edit.setText(base_dir)

        folder_structure = self.config.get("folder_structure", "day")
        reverse_map = {v: k for k, v in self.FOLDER_STRUCT_MAP.items()}
        self.folder_struct_group.button(reverse_map.get(folder_structure, 0)).setChecked(True)

        self.video_separate_checkbox.setChecked(self.config.get("separate_videos", False))

        excluded = self.config.get("excluded_folders", [])
        self.excluded_folders_list.clear()
        for folder in excluded if isinstance(excluded, list) else excluded.split(','):
            self.excluded_folders_list.addItem(folder.strip())

    def save_config(self):
        folder_struct_id = self.folder_struct_group.checkedId()
        folder_struct = self.FOLDER_STRUCT_MAP.get(folder_struct_id, "day")
        excluded = self.get_excluded_folders()

        config = {
            "base_dir": self.base_dir_edit.text(),
            "folder_structure": folder_struct,
            "separate_videos": self.video_separate_checkbox.isChecked(),
            "excluded_folders": excluded,
            "warn_onedrive": self.onedrive_warning_checkbox.isChecked()
        }
        ConfigManager.save(config)


# -----------------------------------
# Helper function outside the class
# -----------------------------------

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
