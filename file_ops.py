import os
import hashlib
import shutil
import threading
from datetime import datetime
from collections import deque


class FileUtils:
    _seen_hashes = set()
    _seen_lock = threading.Lock()

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
            return hashlib.md5(start + size.to_bytes(8, 'little')).hexdigest()
        except Exception:
            return ""

    @staticmethod
    def full_file_hash(path: str, block_size: int = 65536) -> str:
        try:
            hasher = hashlib.md5()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(block_size), b''):
                    hasher.update(chunk)
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
                        return True
        except Exception:
            return False

    @staticmethod
    def resolve_filename_conflict(dest: str, src: str) -> str | None:
        if not os.path.exists(dest):
            return dest

        if FileUtils.quick_file_hash(dest) == FileUtils.quick_file_hash(src):
            if FileUtils.files_are_identical(dest, src):
                return None

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
    def fast_walk(top: str, topdown: bool = True):
        queue = deque([top])
        visited = []

        while queue:
            current_dir = queue.popleft()
            try:
                with os.scandir(current_dir) as it:
                    dirs, files = [], []
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                dirs.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                files.append(entry.name)
                        except Exception:
                            continue
                    if topdown:
                        yield current_dir, dirs, files
                    visited.append((current_dir, dirs, files))
                    queue.extend(dirs)
            except (PermissionError, FileNotFoundError):
                continue

        if not topdown:
            for item in reversed(visited):
                yield item

    @staticmethod
    def is_fast_duplicate(path: str) -> bool:
        checksum = FileUtils.quick_file_hash(path)
        with FileUtils._seen_lock:
            if checksum in FileUtils._seen_hashes:
                return True
            FileUtils._seen_hashes.add(checksum)
        return False


class FileMover:
    @staticmethod
    def move_file(src: str, dest_folder: str, lock: threading.RLock, existing_files: set[str]) -> str:
        filename = os.path.basename(src)
        if FileUtils.is_fast_duplicate(src):
            return f"Skipped {filename}, duplicate by checksum"

        try:
            os.makedirs(dest_folder, exist_ok=True)
            dest = os.path.join(dest_folder, filename)

            with lock:
                resolved_dest = FileUtils.resolve_filename_conflict(dest, src)
                if resolved_dest is None:
                    return f"Skipped {filename}, duplicate"
                dest = resolved_dest
                existing_files.add(os.path.basename(dest))

            if os.path.abspath(src) != os.path.abspath(dest):
                try:
                    os.rename(src, dest)
                except OSError:
                    shutil.move(src, dest)
                return f"Moved {filename} → {dest_folder}"
            return f"Skipped {filename}, already there"
        except Exception as e:
            return f"Error moving {filename}: {e}"

    @staticmethod
    def safe_move_file(src: str, target: str, lock: threading.RLock, existing: set[str], log_func) -> None:
        try:
            result = FileMover.move_file(src, target, lock, existing)
            log_func(result)
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            log_func(f"[CRITICAL] Exception moving {src}: {e}\n{err}")


class FolderNameGenerator:
    @staticmethod
    def generate(dt: datetime | None, ext: str, structure: str) -> str:
        if not dt:
            return "Unknown Date"

        formats = {
            "day": lambda: dt.strftime("%Y-%m-%d"),
            "year_month_day": lambda: os.path.join(dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")),
            "year_month": lambda: os.path.join(dt.strftime("%Y"), dt.strftime("%m")),
            "year_day": lambda: os.path.join(dt.strftime("%Y"), dt.strftime("%j")),
        }
        return formats.get(structure, lambda: dt.strftime("%Y-%m-%d"))()
