from PySide6.QtWidgets import QApplication
from gui import PhotoOrganizerGUI

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = PhotoOrganizerGUI()
    window.show()
    sys.exit(app.exec())