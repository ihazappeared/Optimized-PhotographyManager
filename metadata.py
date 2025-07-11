import os
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from PIL import Image, UnidentifiedImageError
import exifread

from file_ops import FileUtils
from config import PHOTO_EXTS, RAW_EXTS
from utils import SystemUtils

PHOTO_EXTS = set(PHOTO_EXTS)
RAW_EXTS = set(RAW_EXTS)


class FileGatherer:
    @staticmethod
    def scan_files(base: str, exts: tuple[str, ...], excluded_folders: list[str] | None = None):
        excluded_abs = set(os.path.abspath(x) for x in (excluded_folders or []))
        join = os.path.join
        abspath = os.path.abspath

        for root, _, files in FileUtils.fast_walk(base):
            absroot = abspath(root)
            if any(absroot.startswith(e + os.sep) for e in excluded_abs):
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in exts:
                    yield join(root, f)

    @staticmethod
    def gather_files_with_metadata(base_path: str, extensions: tuple[str, ...], excluded_folders: list[str] | None = None):
        pending = list(FileGatherer.scan_files(base_path, extensions, excluded_folders))
        if not pending:
            return

        max_procs = min(cpu_count(), 4)
        chunksize = max(10, len(pending) // (max_procs * 4))

        with ProcessPoolExecutor(max_workers=max_procs) as executor:
            for path, iso_dt in executor.map(extract_worker, pending, chunksize=chunksize):
                yield path, iso_dt


class MetadataExtractor:
    @staticmethod
    def get_date_taken(path: str) -> datetime | None:
        ext = os.path.splitext(path)[1].lower()
        try:
            with open(path, 'rb') as f:
                if ext in PHOTO_EXTS:
                    try:
                        img = Image.open(f)
                        exif = img.getexif()
                        if exif:
                            for tag in (36867, 306, 36868, 36869):  # DateTimeOriginal, etc.
                                dt_str = exif.get(tag)
                                if dt_str:
                                    try:
                                        return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                                    except ValueError:
                                        continue
                    except (UnidentifiedImageError, OSError):
                        pass

                    f.seek(0)
                    tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
                    dt_str = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
                    if dt_str:
                        try:
                            return datetime.strptime(str(dt_str), "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            pass

                elif ext in RAW_EXTS:
                    tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
                    dt_str = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
                    if dt_str:
                        try:
                            return datetime.strptime(str(dt_str), "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            pass

                    try:
                        import rawpy
                        f.seek(0)
                        with rawpy.imread(f) as raw:
                            dt_str = raw.metadata.datetime_taken
                            if dt_str:
                                try:
                                    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                                except ValueError:
                                    pass
                    except Exception:
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
