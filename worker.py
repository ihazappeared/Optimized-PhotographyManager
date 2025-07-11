from PySide6.QtCore import QThread
from organizer import PhotoOrganizer


class WorkerThread(QThread):
    def __init__(self, organizer: PhotoOrganizer):
        super().__init__()
        self.organizer = organizer

    def run(self) -> None:
        self.organizer.organize()
