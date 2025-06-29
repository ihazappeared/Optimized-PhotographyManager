from PySide6.QtWidgets import QApplication
from gui import PhotoOrganizerGUI
import metadata_cache

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = PhotoOrganizerGUI()
    window.show()
    print(app.style().objectName())

    sys.exit(app.exec())