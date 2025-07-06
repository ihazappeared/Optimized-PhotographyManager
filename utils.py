import psutil
import multiprocessing


class SystemUtils:
    @staticmethod
    def get_system_specs() -> tuple[float, int]:
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        cpu_count = multiprocessing.cpu_count()
        return ram_gb, cpu_count

    @staticmethod
    def auto_tune_batch_size(min_size=100, max_size=5000) -> int:
        ram_gb, cpu_count = SystemUtils.get_system_specs()

        ram_factor = min(ram_gb / 8, 1)
        cpu_factor = min(cpu_count / 4, 1)

        avg_factor = (ram_factor + cpu_factor) / 2

        base_scale = 200 * (0.5 + 0.5 * avg_factor)

        batch_size = int(max(min_size, min(max_size, base_scale)))

        return batch_size
