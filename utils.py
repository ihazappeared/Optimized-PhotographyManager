import psutil
import multiprocessing


class SystemUtils:
    @staticmethod
    def is_onedrive_running() -> bool:
        """
        Check if any running process contains 'onedrive' in its name (case-insensitive).
        """
        for proc in psutil.process_iter(['name']):
            name = proc.info.get('name')
            if name and 'onedrive' in name.lower():
                return True
        return False

    @staticmethod
    def get_system_specs() -> tuple[float, int]:
        """
        Return system RAM in gigabytes and CPU core count.
        """
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        cpu_count = multiprocessing.cpu_count()
        return ram_gb, cpu_count

    @staticmethod
    def auto_tune_batch_size(min_size=100, max_size=5000) -> int:
        """
        Calculate a batch size for processing based on system RAM and CPU count.

        Scaling is normalized against 8GB RAM and 4 CPU cores,
        with output clamped between min_size and max_size.
        """
        ram_gb, cpu_count = SystemUtils.get_system_specs()

        # Normalize factors (cap at 1 to avoid overly large scale)
        ram_factor = min(ram_gb / 8, 1)
        cpu_factor = min(cpu_count / 4, 1)

        # Compute average factor
        avg_factor = (ram_factor + cpu_factor) / 2

        # Base scale adjusted by average factor (between 100 and 200)
        base_scale = 200 * (0.5 + 0.5 * avg_factor)

        # Clamp scale to min and max sizes
        batch_size = int(max(min_size, min(max_size, base_scale)))

        return batch_size
