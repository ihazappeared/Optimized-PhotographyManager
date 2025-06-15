
import os
import json
from constants import CONFIG_PATH
from PySide6.QtWidgets import QMessageBox


class ConfigManager:
    @staticmethod
    def load() -> dict:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def save(config: dict) -> None:
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass
    def reset_cache_and_settings(self):
        base_dir = self.base_dir_edit.text().strip()
        config_path = os.path.expanduser("~/.photo_organizer_config.json")
        cache_path = os.path.join(base_dir, ".photo_metadata_cache.db") if base_dir else None

        msg = QMessageBox()
        msg.setWindowTitle("Reset Confirmation")
        msg.setText("This will delete your settings and cache files.\nAre you sure you want to continue?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec() == QMessageBox.Yes:
            try:
                if os.path.exists(config_path):
                    os.remove(config_path)
            except Exception:
                pass
            if cache_path and os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
            self.excluded_folders_list.clear()
            self.progress_bar.setValue(0)
            self.log_text.clear()
            self.base_dir_edit.clear()
            self.video_separate_checkbox.setChecked(False)
            self.radio_day.setChecked(True)

            self.log_signal.emit("Settings and cache reset completed.")
        

    def load_config(self):
        self.onedrive_warning_checkbox.setChecked(self.config.get("warn_onedrive", True))

        base_dir = self.config.get("base_dir", "")
        if base_dir:
            self.base_dir_edit.setText(base_dir)
        folder_structure = self.config.get("folder_structure", "day")
        if folder_structure == "day":
            self.radio_day.setChecked(True)
        elif folder_structure == "month_day":
            self.radio_month_day.setChecked(True)
        elif folder_structure == "year_month_day":
            self.radio_year_month_day.setChecked(True)
        elif folder_structure == "year_day":
            self.radio_year_day.setChecked(True)
        self.video_separate_checkbox.setChecked(self.config.get("separate_videos", False))
        excluded = self.config.get("excluded_folders", "")
        self.excluded_folders_list.clear()
        if isinstance(excluded, list):
            for folder in excluded:
                self.excluded_folders_list.addItem(folder)
        elif isinstance(excluded, str) and excluded:
            for folder in excluded.split(','):
                self.excluded_folders_list.addItem(folder.strip())
    def save_config(self):
        folder_struct_map = {
            0: "day",
            1: "month_day",
            2: "year_month_day",
            3: "year_day"
        }
        folder_struct_id = self.folder_struct_group.checkedId()
        folder_struct = folder_struct_map.get(folder_struct_id, "day")

        excluded = [self.excluded_folders_list.item(i).text() for i in range(self.excluded_folders_list.count())]
        config = {
            "base_dir": self.base_dir_edit.text(),
            "folder_structure": folder_struct,
            "separate_videos": self.video_separate_checkbox.isChecked(),
            "excluded_folders": excluded,
            "warn_onedrive": self.onedrive_warning_checkbox.isChecked()
        }
        ConfigManager.save(config)
