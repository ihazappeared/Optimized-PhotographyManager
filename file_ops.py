import os
import hashlib
import shutil
import traceback
import threading
from datetime import datetime


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
            
    @staticmethod
    def fast_walk(top, topdown=True):
        stack = [top]
        visited = []

        while stack:
            current_dir = stack.pop()
            try:
                with os.scandir(current_dir) as it:
                    dirs, files = [], []
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            dirs.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            files.append(entry.name)
                    if topdown:
                        yield current_dir, dirs, files
                    visited.append((current_dir, dirs, files))
                    stack.extend(dirs)
            except (PermissionError, FileNotFoundError):
                continue

        if not topdown:
            for item in reversed(visited):
                yield item


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

class FolderNameGenerator:
    @staticmethod
    def generate(dt: datetime | None, ext: str, structure: str) -> str:
        if not dt:
            return "Unknown Date"

        if structure == "day":
            return dt.strftime("%Y-%m-%d")
        if structure == "month_day":
            return os.path.join(str(dt.year), dt.strftime("%B"), f"{dt.day:02d}")
        if structure == "year_month_day":
            return os.path.join(str(dt.year), f"{dt.month:02d}", dt.strftime("%A"))
        if structure == "year_day":
            return os.path.join(str(dt.year), f"{dt.timetuple().tm_yday:03d}")
        return os.path.join(str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}")