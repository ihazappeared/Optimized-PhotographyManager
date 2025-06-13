import os
import shutil
import psutil
import threading
import traceback
import json
import ctypes
import stat
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count
from collections import defaultdict
import hashlib
from PIL import Image, UnidentifiedImageError

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QRadioButton, QButtonGroup, QCheckBox, QListWidget, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QObject, Signal, QThread


# Constants for file extensions and config/cache filenames
PHOTO_EXTS = ('.jpg', '.jpeg', '.png')
RAW_EXTS = ('.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2')
VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.mts', '.m2ts', '.wmv')

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".photo_organizer_config.json")
CACHE_FILENAME = ".photo_metadata_cache.json"


class ConfigManager:
    @staticmethod
    def load() -> dict:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def save(config: dict) -> None:
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass


class MetadataCache:
    def __init__(self, base_dir: str):
        self.cache_path = os.path.join(base_dir, CACHE_FILENAME)
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save(self) -> None:
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f)
        except Exception:
            pass

    def get(self, filepath: str):
        return self.cache.get(filepath)

    def update(self, filepath: str, date_taken_iso: str, mod_time: float):
        self.cache[filepath] = {"date_taken": date_taken_iso, "mod_time": mod_time}


class FileUtils:
    @staticmethod
    def get_file_mod_time(path: str) -> float | None:
        try:
            return os.path.getmtime(path)
        except Exception:
            return None

    @staticmethod
    def quick_file_hash(path: str, block_size: int = 4096) -> str:
        try:
            size = os.path.getsize(path)
            with open(path, 'rb') as f:
                start = f.read(block_size)
            return hashlib.md5(start + str(size).encode()).hexdigest()
        except Exception:
            return ""

    @staticmethod
    def full_file_hash(path: str, block_size: int = 65536) -> str:
        try:
            hasher = hashlib.md5()
            with open(path, 'rb') as f:
                while True:
                    buf = f.read(block_size)
                    if not buf:
                        break
                    hasher.update(buf)
            return hasher.hexdigest()
        except Exception:
            return ""

    @staticmethod
    def files_are_identical(path1: str, path2: str, block_size: int = 65536) -> bool:
        try:
            if os.path.getsize(path1) != os.path.getsize(path2):
                return False
            with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
                while True:
                    b1 = f1.read(block_size)
                    b2 = f2.read(block_size)
                    if b1 != b2:
                        return False
                    if not b1:
                        break
            return True
        except Exception:
            return False

    @staticmethod
    def resolve_filename_conflict(dest: str, src: str) -> str | None:
        if not os.path.exists(dest):
            return dest

        # First quick hash compare
        if FileUtils.quick_file_hash(dest) == FileUtils.quick_file_hash(src):
            # Deeper check with full file hash and byte-by-byte
            if FileUtils.files_are_identical(dest, src):
                return None  # Duplicate, no need to move

        base, ext = os.path.splitext(dest)
        i = 1
        while True:
            new_path = f"{base}_{i}{ext}"
            if not os.path.exists(new_path):
                return new_path
            if FileUtils.quick_file_hash(new_path) == FileUtils.quick_file_hash(src):
                if FileUtils.files_are_identical(new_path, src):
                    return None
            i += 1


class MetadataExtractor:
    @staticmethod
    def get_date_taken(path: str) -> datetime | None:
        ext = os.path.splitext(path)[1].lower()
        if ext in PHOTO_EXTS:
            try:
                img = Image.open(path)
                try:
                    exif = img._getexif()
                except Exception:
                    exif = None
                if exif:
                    # Try multiple tags for DateTimeOriginal or fallback DateTime
                    for tag in (36867, 306, 36868, 36869):
                        dt_str = exif.get(tag)
                        if dt_str:
                            try:
                                return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                            except Exception:
                                continue
                # Fallback to file mod time
            except (UnidentifiedImageError, OSError):
                pass
        mod_time = FileUtils.get_file_mod_time(path)
        return datetime.fromtimestamp(mod_time) if mod_time else None

    @staticmethod
    def extract_metadata_worker(item: tuple) -> tuple:
        path, last_mod = item
        dt = MetadataExtractor.get_date_taken(path)
        iso_dt = dt.isoformat() if dt else None
        return path, iso_dt, last_mod


class FileGatherer:
    @staticmethod
    def gather_files_with_metadata(base: str, exts: tuple, cache: MetadataCache, excluded_folders: list | None = None):
        excluded_abs = [os.path.abspath(x) for x in (excluded_folders or [])]
        pending = []

        for root, _, files in os.walk(base):
            absroot = os.path.abspath(root)
            if any(absroot.startswith(e + os.sep) for e in excluded_abs):
                continue
            for f in files:
                if f in ("photo_organizer_log.txt", CACHE_FILENAME):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in exts:
                    full_path = os.path.join(root, f)
                    mod = FileUtils.get_file_mod_time(full_path)
                    cache_entry = cache.get(full_path)
                    if cache_entry and cache_entry.get("mod_time") == mod:
                        yield full_path, cache_entry.get("date_taken")
                    else:
                        pending.append((full_path, mod))

        if pending:
            batches = [pending[i:i+200] for i in range(0, len(pending), 200)]
            for batch in batches:
                with ProcessPoolExecutor(max_workers=min(cpu_count(), 4)) as executor:
                    for p, iso_dt, m in executor.map(MetadataExtractor.extract_metadata_worker, batch):
                        cache.update(p, iso_dt, m)
                        yield p, iso_dt


class FolderNameGenerator:
    @staticmethod
    def generate(dt: datetime | None, ext: str, structure: str) -> str:
        if not dt:
            return "Unknown Date"

        if structure == "day":
            return dt.strftime("%d-%m-%Y")
        if structure == "month_day":
            return os.path.join(str(dt.year), dt.strftime("%B"), f"{dt.day:02d}")
        if structure == "year_month_day":
            return os.path.join(str(dt.year), f"{dt.month:02d}", dt.strftime("%A"))
        if structure == "year_day":
            return os.path.join(str(dt.year), f"{dt.timetuple().tm_yday:03d}")
        return os.path.join(str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}")


class FileMover:
    @staticmethod
    def move_file(src: str, dest_folder: str, lock: threading.RLock, existing_files: set) -> str:
        fn = os.path.basename(src)
        try:
            os.makedirs(dest_folder, exist_ok=True)
            dest = os.path.join(dest_folder, fn)
            with lock:
                new_dest = FileUtils.resolve_filename_conflict(dest, src)
                if new_dest is None:
                    return f"Skipped {fn}, duplicate"
                dest = new_dest
                existing_files.add(os.path.basename(dest))
            if os.path.abspath(src) != os.path.abspath(dest):
                shutil.move(src, dest)
                return f"Moved {fn} → {dest_folder}"
            return f"Skipped {fn}, already there"
        except Exception as e:
            return f"Error moving {fn}: {e}"

    @staticmethod
    def safe_move_file(src: str, target: str, lock: threading.RLock, existing: set, log_func) -> None:
        try:
            result = FileMover.move_file(src, target, lock, existing)
            log_func(result)
        except Exception as e:
            err = traceback.format_exc()
            log_func(f"[CRITICAL] Exception moving {src}: {e}\n{err}")


class SystemUtils:
    @staticmethod
    def is_onedrive_running() -> bool:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'onedrive' in proc.info['name'].lower():
                return True
        return False


class PhotoOrganizer(QObject):
    progress = Signal(int)
    log_msg = Signal(str)

    def __init__(self, base_dir: str, folder_structure: str,
                 max_workers: int = cpu_count(), separate_videos: bool = False, excluded_folders: list | None = None):
        super().__init__()
        self.base_dir = base_dir
        self.folder_structure = folder_structure
        self.max_workers = max_workers
        self.separate_videos = separate_videos
        self.excluded_folders = excluded_folders or []

        self.lock = threading.RLock()
        self.cache = MetadataCache(base_dir)

    def organize(self):
        exts = PHOTO_EXTS + RAW_EXTS
        file_exts = exts + VIDEO_EXTS

        # Build existing_files set thread safely
        with self.lock:
            existing_files = set()

        self.log_msg.emit(f"Starting scan in {self.base_dir}...")

        # Gather files and metadata
        file_metadata_gen = FileGatherer.gather_files_with_metadata(self.base_dir, file_exts, self.cache, self.excluded_folders)

        file_list = list(file_metadata_gen)
        total_files = len(file_list)

        self.log_msg.emit(f"Found {total_files} files to organize.")
        self.progress.emit(0)

        # Keep track of files moved
        moved_count = 0

        def log_and_update_progress(msg):
            self.log_msg.emit(msg)

        def move_worker(file_data):
            path, date_taken_iso = file_data
            dt = datetime.fromisoformat(date_taken_iso) if date_taken_iso else None

            ext = os.path.splitext(path)[1].lower()

            if ext in RAW_EXTS:
                # Raw files inside date folder / Raw subfolder
                target_dir = os.path.join(self.base_dir, FolderNameGenerator.generate(dt, ext, self.folder_structure), "Raw")
            elif ext in VIDEO_EXTS and self.separate_videos:
                # Videos in top-level Videos folder
                target_dir = os.path.join(self.base_dir, "Videos")
            else:
                # Photos go directly in date folder
                target_dir = os.path.join(self.base_dir, FolderNameGenerator.generate(dt, ext, self.folder_structure))

            FileMover.safe_move_file(path, target_dir, self.lock, existing_files, log_and_update_progress)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for idx, file_data in enumerate(file_list):
                futures.append(executor.submit(move_worker, file_data))
                self.progress.emit(int((idx / total_files) * 100))
            for idx, future in enumerate(futures):
                future.result()  # Wait for all to finish
                self.progress.emit(int(((idx + 1) / total_files) * 100))

        self.cache.save()
        self.progress.emit(100)
        self.log_msg.emit("Organization complete.")


class WorkerThread(QThread):
    def __init__(self, organizer: PhotoOrganizer):
        super().__init__()
        self.organizer = organizer

    def run(self):
        self.organizer.organize()


class PhotoOrganizerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Organizer")
        self.resize(900, 600)

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

        for i, rb in enumerate([self.radio_day, self.radio_month_day, self.radio_year_month_day, self.radio_year_day]):
            self.folder_struct_group.addButton(rb, i)

        self.video_separate_checkbox = QCheckBox("Separate Videos into 'Videos' Folder")
        self.excluded_folders_list = QListWidget()
        self.excluded_folders_list.setSelectionMode(QListWidget.ExtendedSelection)

        
        self.add_excluded_button = QPushButton("Add Folder to Exclude")
        self.remove_excluded_button = QPushButton("Remove Selected")
        self.reset_all_button = QPushButton("Reset Cache and Settings")

        self.add_excluded_button.clicked.connect(self.add_excluded_folder)
        self.remove_excluded_button.clicked.connect(self.remove_selected_excluded_folders)
        self.reset_all_button.clicked.connect(self.reset_cache_and_settings)

        self.remove_empty_folders_checkbox = QCheckBox("Remove empty folders after organizing", self)
        self.start_button = QPushButton("Start Organizing")
        self.start_button.clicked.connect(self.start_organizing)

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
        layout.addWidget(self.progress_bar)

        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log_text)

        self.setLayout(layout)

        # Load saved config
        self.load_config()


    def add_excluded_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder to Exclude", self.base_dir_edit.text())
        if path and path not in [self.excluded_folders_list.item(i).text() for i in range(self.excluded_folders_list.count())]:
            self.excluded_folders_list.addItem(path)
            
    
    def remove_selected_excluded_folders(self):
        for item in self.excluded_folders_list.selectedItems():
            self.excluded_folders_list.takeItem(self.excluded_folders_list.row(item))

    def reset_cache_and_settings(self):
        base_dir = self.base_dir_edit.text().strip()
        config_path = os.path.expanduser("~/.photo_organizer_config.json")
        cache_path = os.path.join(base_dir, ".photo_metadata_cache.json") if base_dir else None

        msg = QMessageBox()
        msg.setWindowTitle("Reset Confirmation")
        msg.setText("This will delete your settings and cache files.\nAre you sure you want to continue?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec() == QMessageBox.Yes:
            try:
                if os.path.exists(config_path):
                    os.remove(config_path)
            except Exception:
                pass
            if cache_path and os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
            self.excluded_folders_list.clear()
            self.progress_bar.setValue(0)
            self.log_text.clear()
            self.base_dir_edit.clear()
            self.video_separate_checkbox.setChecked(False)
            self.radio_day.setChecked(True)

            self.append_log("Settings and cache reset completed.")
        
    
    def browse_base_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Base Directory", self.base_dir_edit.text())
        if path:
            self.base_dir_edit.setText(path)

    def load_config(self):
        base_dir = self.config.get("base_dir", "")
        if base_dir:
            self.base_dir_edit.setText(base_dir)
        folder_structure = self.config.get("folder_structure", "day")
        if folder_structure == "day":
            self.radio_day.setChecked(True)
        elif folder_structure == "month_day":
            self.radio_month_day.setChecked(True)
        elif folder_structure == "year_month_day":
            self.radio_year_month_day.setChecked(True)
        elif folder_structure == "year_day":
            self.radio_year_day.setChecked(True)
        self.video_separate_checkbox.setChecked(self.config.get("separate_videos", False))
        excluded = self.config.get("excluded_folders", "")
        self.excluded_folders_list.clear()
        if isinstance(excluded, list):
            for folder in excluded:
                self.excluded_folders_list.addItem(folder)
        elif isinstance(excluded, str) and excluded:
            for folder in excluded.split(','):
                self.excluded_folders_list.addItem(folder.strip())
    def save_config(self):
        folder_struct_map = {
            0: "day",
            1: "month_day",
            2: "year_month_day",
            3: "year_day"
        }
        folder_struct_id = self.folder_struct_group.checkedId()
        folder_struct = folder_struct_map.get(folder_struct_id, "day")

        excluded = [self.excluded_folders_list.item(i).text() for i in range(self.excluded_folders_list.count())]
        config = {
            "base_dir": self.base_dir_edit.text(),
            "folder_structure": folder_struct,
            "separate_videos": self.video_separate_checkbox.isChecked(),
            "excluded_folders": excluded
        }
        ConfigManager.save(config)

    def append_log(self, message: str):
        self.log_text.append(message)
        self.log_text.moveCursor(QTextCursor.End)

    def remove_empty_folders(self, root_path):
        def is_hidden_or_system(file_path):
            try:
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
                return attrs != -1 and bool(attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM))
            except Exception:
                return False

        for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
            try:
                # Filter out hidden or system files
                visible_files = [
                    f for f in filenames
                    if not is_hidden_or_system(os.path.join(dirpath, f)) and not f.startswith('.')
                ]

                # If no visible files and no subfolders, remove folder
                if not dirnames and not visible_files:
                    os.rmdir(dirpath)
                    print(f"Removed empty folder: {dirpath}")

            except PermissionError as e:
                print(f"Permission denied removing folder {dirpath}: {e}")
            except Exception as e:
                print(f"Could not remove folder {dirpath}: {e}")
                
                
    def start_organizing(self):
        base_dir = self.base_dir_edit.text().strip()
        if not base_dir or not os.path.isdir(base_dir):
            self.append_log("Invalid base directory.")
            return

        # if SystemUtils.is_onedrive_running():
        #     self.append_log("[WARNING] OneDrive is running. This may interfere with file operations.")

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
        self.organizer.log_msg.connect(self.append_log)

        self.start_button.setEnabled(False)

        self.worker_thread = WorkerThread(self.organizer)
        def on_worker_finished():
            self.start_button.setEnabled(True)
            self.base_dir = base_dir
            if self.remove_empty_folders_checkbox.isChecked():
                self.remove_empty_folders(base_dir)
        self.worker_thread.finished.connect(on_worker_finished)
        self.worker_thread.start()
        
        
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = PhotoOrganizerGUI()
    window.show()
    sys.exit(app.exec())