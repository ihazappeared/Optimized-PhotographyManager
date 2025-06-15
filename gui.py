from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QRadioButton, QButtonGroup, QCheckBox, QListWidget, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QObject, Signal, QThread
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


class PhotoOrganizerGUI(QWidget):
    log_signal = Signal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Organizer")
        self.resize(900, 600)

        self.log_signal.connect(_append_log)

        self.config = ConfigManager.load()
        self.lock = threading.RLock()
        self.existing_files = set()

        self.base_dir_edit = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_base_dir)

        self.folder_struct_group = QButtonGroup(self)
        self.radio_day = QRadioButton("Day (DD-MM-YYYY)")
        self.radio_month_day = QRadioButton("Month/Day (YYYY/Month/DD)")
        self.radio_year_month_day = QRadioButton("Year/Month/Day (YYYY/MM/DD)")
        self.radio_year_day = QRadioButton("Year/Day of Year (YYYY/DDD)")
        self.radio_day.setChecked(True)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(cancel_organizing)

        for i, rb in enumerate([self.radio_day, self.radio_month_day, self.radio_year_month_day, self.radio_year_day]):
            self.folder_struct_group.addButton(rb, i)

        self.video_separate_checkbox = QCheckBox("Separate Videos into 'Videos' Folder")
        self.excluded_folders_list = QListWidget()
        self.excluded_folders_list.setSelectionMode(QListWidget.ExtendedSelection)

        
        self.add_excluded_button = QPushButton("Add Folder to Exclude")
        self.remove_excluded_button = QPushButton("Remove Selected")
        self.reset_all_button = QPushButton("Reset Cache and Settings")

        self.add_excluded_button.clicked.connect(add_excluded_folder)
        self.remove_excluded_button.clicked.connect(remove_selected_excluded_folders)
        self.reset_all_button.clicked.connect(ConfigManager.reset_cache_and_settings)

        self.remove_empty_folders_checkbox = QCheckBox("Remove empty folders after organizing", self)
        self.start_button = QPushButton("Start Organizing")
        self.start_button.clicked.connect(start_organizing)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)

        self.progress_bar = QProgressBar()
        self.progress_bar.setOrientation(Qt.Horizontal)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                height: 20px;
                border: 1px solid black;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #b0b0b0;
                border-radius: 5px;
            }
        """)
        self.progress_bar.update()


        layout = QVBoxLayout()
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Base Directory:"))
        top_row.addWidget(self.base_dir_edit)
        top_row.addWidget(self.browse_button)

        layout.addLayout(top_row)

        folder_struct_layout = QHBoxLayout()
        folder_struct_layout.addWidget(QLabel("Folder Structure:"))
        folder_struct_layout.addWidget(self.radio_day)
        folder_struct_layout.addWidget(self.radio_month_day)
        folder_struct_layout.addWidget(self.radio_year_month_day)
        folder_struct_layout.addWidget(self.radio_year_day)
        layout.addLayout(folder_struct_layout)
        layout.addWidget(self.remove_empty_folders_checkbox)
        layout.addWidget(self.video_separate_checkbox)

        self.onedrive_warning_checkbox = QCheckBox("Warn if OneDrive is running")
        layout.addWidget(self.onedrive_warning_checkbox)
        excluded_layout = QVBoxLayout()
        excluded_layout.addWidget(QLabel("Exclude Folders:"))
        excluded_layout.addWidget(self.excluded_folders_list)

        excluded_buttons_layout = QHBoxLayout()
        excluded_buttons_layout.addWidget(self.add_excluded_button)
        excluded_buttons_layout.addWidget(self.remove_excluded_button)
        excluded_layout.addLayout(excluded_buttons_layout)

        layout.addLayout(excluded_layout)

        layout.addWidget(self.reset_all_button)

        layout.addWidget(self.start_button)
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.progress_bar)

        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log_text)

        self.setLayout(layout)

        # Load saved config
        ConfigManager.load_config(self)
    def browse_base_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Base Directory", self.base_dir_edit.text())
        if path:
            self.base_dir_edit.setText(path)


def cancel_organizing(self):
        if hasattr(self, "organizer"):
            self.progress_bar.setFormat("Cancelling...")
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
            self.append_log("Cancellation requested...")
                
def add_excluded_folder(self):
    path = QFileDialog.getExistingDirectory(self, "Select Folder to Exclude", self.base_dir_edit.text())
    if path and path not in [self.excluded_folders_list.item(i).text() for i in range(self.excluded_folders_list.count())]:
        self.excluded_folders_list.addItem(path)


def remove_selected_excluded_folders(self):
    for item in self.excluded_folders_list.selectedItems():
        self.excluded_folders_list.takeItem(self.excluded_folders_list.row(item))


def _append_log(self, message: str):
    if self.log_text.document().blockCount() > 1000:
        self.log_text.clear()
        self.log_text.append("[Log truncated]")
    self.log_text.append(message)
    self.log_text.moveCursor(QTextCursor.End)

def remove_empty_folders(self, root_path):
    def is_hidden_or_system(file_path):
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
            return attrs != -1 and bool(attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM))
        except Exception:
            return False

    for dirpath, dirnames, filenames in FileUtils.fast_walk(root_path, topdown=False):
        try:
            # Filter out hidden or system files
            visible_files = [
                f for f in filenames
                if not is_hidden_or_system(os.path.join(dirpath, f)) and not f.startswith('.')
            ]

            # If no visible files and no subfolders, remove folder
            if not dirnames and not visible_files:
                os.rmdir(dirpath)
                self.log_signal.emit(f"Removed empty folder: {dirpath}")

        except PermissionError as e:
            self.log_signal.emit(f"Permission denied removing folder {dirpath}: {e}")
        except Exception as e:
            self.log_signal.emit(f"Could not remove folder {dirpath}: {e}")
            
            
def start_organizing(self):
    base_dir = self.base_dir_edit.text().strip()
    if not base_dir or not os.path.isdir(base_dir):
        self.log_signal.emit("Invalid base directory.")
        return

    if self.onedrive_warning_checkbox.isChecked() and SystemUtils.is_onedrive_running():
        self.log_signal.emit("[WARNING] OneDrive is running. This may interfere with file operations.")
            
    self.save_config()

    folder_struct_map = {
        0: "day",
        1: "month_day",
        2: "year_month_day",
        3: "year_day"
    }
    folder_struct = folder_struct_map.get(self.folder_struct_group.checkedId(), "day")

    excluded = [self.excluded_folders_list.item(i).text() for i in range(self.excluded_folders_list.count())]

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
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk {
                background-color: #b0b0b0;
                border-radius: 5px;
            }
        """)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.base_dir = base_dir
        if self.remove_empty_folders_checkbox.isChecked():
            self.remove_empty_folders(base_dir)
    self.worker_thread.finished.connect(on_worker_finished)
    self.worker_thread.start()
