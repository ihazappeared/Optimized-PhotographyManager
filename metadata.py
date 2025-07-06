import os
import json
from multiprocessing import cpu_count
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from PIL import Image, UnidentifiedImageError
import exifread

from file_ops import FileUtils
from config import PHOTO_EXTS, RAW_EXTS
from utils import SystemUtils


class FileGatherer:
    @staticmethod
    def scan_files(base: str, exts: tuple[str, ...], excluded_folders: list[str] | None = None):
        excluded_abs = [os.path.abspath(x) for x in (excluded_folders or [])]
        for root, _, files in FileUtils.fast_walk(base):
            absroot = os.path.abspath(root)
            if any(absroot.startswith(e + os.sep) for e in excluded_abs):
                continue
            for f in files:
                if f in ("photo_organizer_log.txt"):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in exts:
                    yield os.path.join(root, f)

    @staticmethod
    def gather_files_with_metadata(base_path: str, extensions: tuple[str, ...], excluded_folders: list[str] | None = None):
        pending = []

        file_paths = list(FileGatherer.scan_files(base_path, extensions, excluded_folders))

        for path in file_paths:
            pending.append(path)

        if not pending:
            return

        batch_size = SystemUtils.auto_tune_batch_size(min_size=200, max_size=2000)
        batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]

        max_procs = min(cpu_count(), 4)
        with ProcessPoolExecutor(max_workers=max_procs) as executor:
            for batch in batches:
                results = executor.map(extract_worker, batch)
                for path, iso_dt in results:
                    yield path, iso_dt

class MetadataExtractor:
    @staticmethod
    def get_date_taken(path: str) -> datetime | None:
        ext = os.path.splitext(path)[1].lower()

        if ext in PHOTO_EXTS:
            try:
                with Image.open(path) as img:
                    exif = img.getexif()
                    if exif:
                        for tag in (36867, 306, 36868, 36869):  # DateTimeOriginal, etc.
                            dt_str = exif.get(tag)
                            if dt_str:
                                try:
                                    return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                                except Exception:
                                    continue
            except (UnidentifiedImageError, OSError):
                pass

        elif ext in RAW_EXTS:
            try:
                with open(path, 'rb') as f:
                    tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
                    dt_str = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
                    if dt_str:
                        try:
                            return datetime.strptime(str(dt_str), "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            pass
            except Exception:
                pass

            try:
                import rawpy
                with rawpy.imread(path) as raw:
                    dt_str = raw.metadata.datetime_taken
                    if dt_str:
                        try:
                            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            pass
            except Exception:
                pass

        mod_time = FileUtils.get_file_mod_time(path)
        if mod_time:
            return datetime.fromtimestamp(mod_time)

        return None


def extract_worker(path: str):
    dt = MetadataExtractor.get_date_taken(path)
    iso_dt = dt.isoformat() if dt else None
    return path, iso_dt