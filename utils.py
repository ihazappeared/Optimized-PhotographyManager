import psutil


class SystemUtils:
    @staticmethod
    def is_onedrive_running() -> bool:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'onedrive' in proc.info['name'].lower():
                return True
        return False