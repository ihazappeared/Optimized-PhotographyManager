import os
import json
from PySide6.QtGui import QIcon

PHOTO_EXTS = ('.jpg', '.jpeg', '.png')
RAW_EXTS = ('.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2')
VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.mts', '.m2ts', '.wmv')

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".photo_organizer_config.json")
REG_NAME = "PhotoWatchdog"
WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


main_icon = QIcon.fromTheme("camera-photo")

EXTS = PHOTO_EXTS + RAW_EXTS
file_exts = EXTS + VIDEO_EXTS

class ConfigManager:
    @staticmethod
    def load() -> dict:
        if not os.path.exists(CONFIG_PATH):
            return {}
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def save(config: dict) -> None:
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass
