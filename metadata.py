import os
import json
from multiprocessing import cpu_count
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from PIL import Image, UnidentifiedImageError
import exifread
import xxhash

from metadata_cache import MetadataCache
from file_ops import FileUtils
from constants import PHOTO_EXTS, CACHE_FILENAME, RAW_EXTS
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
                if f in ("photo_organizer_log.txt", CACHE_FILENAME):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in exts:
                    yield os.path.join(root, f)

    @staticmethod
    def gather_files_with_metadata(base_path: str, extensions: tuple[str, ...], cache: MetadataCache, memory_cache, excluded_folders: list[str] | None = None):
        all_paths = set()
        pending = []

        def check_cache_status(path: str):
            try:
                mod_time = os.path.getmtime(path)
                cache_entry = cache.get_metadata_by_path(path)
                if cache_entry and cache_entry.get("mod_time") == mod_time:
                    meta = json.loads(cache_entry.get("metadata_json"))
                    return "cached", path, meta.get("date_taken")
                else:
                    checksum = MetadataCache.compute_checksum(path)
                    return "pending", path, checksum, mod_time
            except Exception:
                return "error", path

        file_paths = list(FileGatherer.scan_files(base_path, extensions, excluded_folders))
        all_paths.update(file_paths)

        max_threads = min(32, max(4, cpu_count() * 2))
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            results = executor.map(check_cache_status, file_paths)

        for result in results:
            if result[0] == "cached":
                _, path, date_taken = result
                yield path, date_taken
            elif result[0] == "pending":
                _, path, checksum, mod_time = result
                pending.append((path, checksum, mod_time))

        if pending:
            batch_size = SystemUtils.auto_tune_batch_size(min_size=200, max_size=2000)
            batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]

            max_procs = min(cpu_count(), 4)
            with ProcessPoolExecutor(max_workers=max_procs) as executor:
                for batch in batches:
                    args = [(p, c) for p, c, _ in batch]
                    for path, checksum, metadata_dict, iso_dt in executor.map(extract_worker, args):
                        mod_time = next(m for p, c, m in batch if p == path)
                        cache.store(checksum, metadata_dict, path, mod_time)
                        yield path, iso_dt

        cache.prune_orphaned_paths(all_paths)
        cache.close()


class MetadataCache:
    @staticmethod
    def compute_checksum(path: str) -> str:
        size = os.path.getsize(path)
        chunk_size = 4096  # 4 KB

        with open(path, 'rb') as f:
            first_chunk = f.read(chunk_size)
            mid_offset = max(size // 2 - chunk_size // 2, 0)
            f.seek(mid_offset)
            mid_chunk = f.read(chunk_size)
            last_offset = max(size - chunk_size, 0)
            f.seek(last_offset)
            last_chunk = f.read(chunk_size)

        combined = first_chunk + mid_chunk + last_chunk + size.to_bytes(8, 'little')
        return xxhash.xxh64(combined).hexdigest()


class MetadataExtractor:
    @staticmethod
    def get_date_taken(path: str) -> datetime | None:
        ext = os.path.splitext(path)[1].lower()

        if ext in PHOTO_EXTS:
            try:
                with Image.open(path) as img:
                    exif = img.getexif()
                    if exif:
                        for tag in (36867, 306, 36868, 36869):  # DateTimeOriginal, DateTime, DateTimeDigitized, etc.
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


def extract_worker(item: tuple[str, str]):
    path, checksum = item
    dt = MetadataExtractor.get_date_taken(path)
    iso_dt = dt.isoformat() if dt else None
    mod_time = FileUtils.get_file_mod_time(path)
    metadata_dict = {"date_taken": iso_dt, "mod_time": mod_time}
    return path, checksum, metadata_dict, iso_dt
