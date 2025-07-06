from PySide6.QtCore import QObject, Signal
from multiprocessing import cpu_count
from concurrent.futures import ThreadPoolExecutor
import threading
import os
from datetime import datetime

from metadata import FileGatherer
from file_ops import FolderNameGenerator, FileMover
from config import RAW_EXTS, VIDEO_EXTS, file_exts
import gui


class PhotoOrganizer(QObject):
    progress = Signal(int)
    log_msg = Signal(str)
    
    total_files = Signal(int)
    moved_files = Signal(int)
    skipped_files = Signal(int)

    def __init__(
        self,
        base_dir: str,
        folder_structure: str,
        max_workers: int = cpu_count(),
        separate_videos: bool = False,
        excluded_folders: list[str] | None = None,
    ):
        super().__init__()
        self.base_dir = base_dir
        self.folder_structure = folder_structure
        self.max_workers = max_workers
        self.separate_videos = separate_videos
        self.excluded_folders = excluded_folders or []

        self.lock = threading.RLock()
        self._cancel_requested = threading.Event()

    def cancel(self) -> None:
        self._cancel_requested.set()

    def is_cancelled(self) -> bool:
        return self._cancel_requested.is_set()

    def _log(self, msg: str) -> None:
        self.log_msg.emit(msg)

    def _emit_progress(self, percent: int) -> None:
        self.progress.emit(percent)

    def _gather_files(self) -> tuple[list, int]:
        self._log(f"Starting scan in {self.base_dir}...")
        file_list = list(FileGatherer.gather_files_with_metadata(
            self.base_dir, file_exts, self.excluded_folders
        ))
        total = len(file_list)
        
        self.total_files.emit(total)
        self._log(f"Metadata loaded for {total} files.")
        self._log(f"Found {total} files to organize.")
        return file_list, total

    def _move_file_worker(self, file_data: tuple[str, str | None], existing_files: set) -> None:
        if self.is_cancelled():
            return

        path, date_taken_iso = file_data
        dt = None
        if date_taken_iso:
            try:
                dt = datetime.fromisoformat(date_taken_iso)
            except ValueError:
                self._log(f"Invalid date format for file {path}, skipping date parsing.")

        ext = os.path.splitext(path)[1].lower()

        if ext in RAW_EXTS:
            target_dir = os.path.join(
                self.base_dir,
                FolderNameGenerator.generate(dt, ext, self.folder_structure),
                "Raw"
            )
        elif ext in VIDEO_EXTS and self.separate_videos:
            target_dir = os.path.join(self.base_dir, "Videos")
        else:
            target_dir = os.path.join(
                self.base_dir,
                FolderNameGenerator.generate(dt, ext, self.folder_structure)
            )

        with self.lock:
            try:
                FileMover.safe_move_file(path, target_dir, self.lock, existing_files, self._log)
            except Exception as e:
                self._log(f"Error moving file {path}: {e}")

    def organize(self) -> None:
    
        existing_files = set()

        file_list, total_files = self._gather_files()
        self._emit_progress(0)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for file_data in file_list:
                if self.is_cancelled():
                    self._log("Organization cancelled before submission.")
                    break
                futures.append(executor.submit(self._move_file_worker, file_data, existing_files))

            for idx, future in enumerate(futures):
                if self.is_cancelled():
                    self._log("Waiting for threads to exit after cancellation...")
                    break
                future.result()
                progress_pct = int(((idx + 1) / total_files) * 100)
                self._emit_progress(progress_pct)

        if self.is_cancelled():
            self._emit_progress(0)
            self._log("Operation cancelled.")
        else:
            self._emit_progress(100)
            self._log("Organization complete.")
