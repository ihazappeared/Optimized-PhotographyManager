from PySide6.QtCore import QObject, Signal
from multiprocessing import cpu_count
from concurrent.futures import ThreadPoolExecutor
import threading
import os
from datetime import datetime

from metadata import FileGatherer
from file_ops import FolderNameGenerator, FileMover
from config import RAW_EXTS, VIDEO_EXTS, file_exts


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
        self._log(f"Scanning {self.base_dir}...")
        files = list(FileGatherer.gather_files_with_metadata(
            self.base_dir, file_exts, self.excluded_folders
        ))
        count = len(files)
        self.total_files.emit(count)
        self._log(f"Loaded metadata for {count} files.")
        return files, count

    def _determine_target_directory(self, path: str, date_taken_iso: str | None) -> str:
        dt = None
        if date_taken_iso:
            try:
                dt = datetime.fromisoformat(date_taken_iso)
            except ValueError:
                self._log(f"Invalid date format for {path}, skipping date parsing.")

        ext = os.path.splitext(path)[1].lower()
        if ext in RAW_EXTS:
            return os.path.join(
                self.base_dir,
                FolderNameGenerator.generate(dt, ext, self.folder_structure),
                "Raw"
            )
        elif ext in VIDEO_EXTS and self.separate_videos:
            return os.path.join(self.base_dir, "Videos")
        else:
            return os.path.join(
                self.base_dir,
                FolderNameGenerator.generate(dt, ext, self.folder_structure)
            )

    def _move_file(self, path: str, date_taken_iso: str | None, existing_files: set) -> bool:
        if self.is_cancelled():
            return False

        target_dir = self._determine_target_directory(path, date_taken_iso)

        try:
            FileMover.safe_move_file(path, target_dir, self.lock, existing_files, self._log)
            self.moved_files.emit(1)
            return True
        except Exception as e:
            self._log(f"Error moving {path}: {e}")
            self.skipped_files.emit(1)
            return False

    def _move_batch(self, batch, existing_files) -> int:
        moved_count = 0
        for path, date_taken_iso in batch:
            if self.is_cancelled():
                break
            if self._move_file(path, date_taken_iso, existing_files):
                moved_count += 1
        return moved_count

    def organize(self) -> None:
        existing_files = set()
        files, total = self._gather_files()
        self._emit_progress(0)

        batch_size = max(10, len(files) // (self.max_workers * 4))
        batches = [files[i:i + batch_size] for i in range(0, len(files), batch_size)]

        moved_total = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._move_batch, batch, existing_files)
                for batch in batches
                if not self.is_cancelled()
            ]

            for idx, future in enumerate(futures):
                if self.is_cancelled():
                    self._log("Cancellation detected, awaiting running threads.")
                    break
                moved_in_batch = future.result()
                moved_total += moved_in_batch
                self._emit_progress(int((moved_total / total) * 100))

        if self.is_cancelled():
            self._emit_progress(0)
            self._log("Operation cancelled.")
        else:
            self._emit_progress(100)
            self._log("Organization complete.")

    def organize_single_photo(self, file_path: str, date_taken_iso: str | None = None) -> None:
        existing_files = set()
        self._emit_progress(0)

        if not os.path.exists(file_path):
            self._log(f"{file_path} does not exist.")
            self._emit_progress(100)
            return

        self._move_file(file_path, date_taken_iso, existing_files)
        self._emit_progress(100)
        self._log(f"Finished organizing {file_path}")
