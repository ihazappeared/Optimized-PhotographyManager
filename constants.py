import os

PHOTO_EXTS = ('.jpg', '.jpeg', '.png')
RAW_EXTS = ('.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2')
VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.mts', '.m2ts', '.wmv')

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".photo_organizer_config.json")
CACHE_FILENAME = ".photo_metadata_cache.json"

exts = PHOTO_EXTS + RAW_EXTS
file_exts = exts + VIDEO_EXTS