import os
import json
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
from datetime import datetime
from metadata_cache import MetadataCache
from PIL import Image, UnidentifiedImageError
from constants import PHOTO_EXTS
from file_ops import FileUtils

class FileGatherer:
    @staticmethod
    def scan_files(base: str, exts: tuple, excluded_folders: list | None = None):
        excluded_abs = [os.path.abspath(x) for x in (excluded_folders or [])]

        for root, _, files in FileUtils.fast_walk(base):
            absroot = os.path.abspath(root)
            if any(absroot.startswith(e + os.sep) for e in excluded_abs):
                continue
            for f in files:
                if f in ("photo_organizer_log.txt", ".photo_metadata_cache.db"):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in exts:
                    yield os.path.join(root, f)

    @staticmethod
    def gather_files_with_metadata(base: str, exts: tuple, cache: 'MetadataCache', excluded_folders: list | None = None):
        """
        Yields tuples of (filepath, date_taken_iso) for all files with valid metadata.
        Uses cache to avoid re-reading metadata if checksum matches.
        Extracts metadata in parallel for uncached or changed files.
        """
        pending = []
        all_paths = set()

        for full_path in FileGatherer.scan_files(base, exts, excluded_folders):
            all_paths.add(full_path)

            checksum = MetadataCache.compute_checksum(full_path)
            cache_entry = cache.get_metadata_by_path(full_path)

            if cache_entry and cache_entry.get("checksum") == checksum:
                meta = json.loads(cache_entry.get("metadata_json"))
                yield full_path, meta.get("date_taken")
            else:
                pending.append((full_path, checksum))

        if pending:
            batch_size = 200
            batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]

            for batch in batches:
                with ProcessPoolExecutor(max_workers=min(cpu_count(), 4)) as executor:
                    # extract_worker must take (path, checksum) and return (path, checksum, metadata_dict, iso_dt)
                    for path, checksum, metadata_dict, iso_dt in executor.map(extract_worker, batch):
                        cache.store(checksum, metadata_dict, path)
                        yield path, iso_dt

        cache.prune_orphaned_paths(all_paths)
        cache.close()
        
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





def read_metadata(self, path):
    cached = self.cache.get(path)
    if cached:
        return (path, cached['date_taken_iso'])
    date_taken_iso = FileGatherer.get_metadata_date(path)  # your method to extract date
    self.cache.set(path, {'date_taken_iso': date_taken_iso})
    return (path, date_taken_iso)

def extract_worker(item):
    path, checksum = item
    dt = MetadataExtractor.get_date_taken(path)
    iso_dt = dt.isoformat() if dt else None
    mod_time = FileUtils.get_file_mod_time(path)
    metadata_dict = {"date_taken": iso_dt, "mod_time": mod_time}
    return path, checksum, metadata_dict, iso_dt

