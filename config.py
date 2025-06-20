import os
import json
from constants import CONFIG_PATH


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
