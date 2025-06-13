import sys
import os
import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PIL import Image
from PIL.ExifTags import TAGS
import rawpy
import csv

def get_exif_creation_time(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            return None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id)
            if tag == 'DateTimeOriginal':
                return value
        return None
    except Exception:
        return None

def get_raw_creation_time(raw_path):
    try:
        with rawpy.imread(raw_path) as raw:
            metadata = raw.metadata

            shot_time = getattr(metadata, 'shot_time', None)
            if shot_time:
                return shot_time.strftime('%Y:%m:%d %H:%M:%S')

            datetime_original = getattr(metadata, 'datetime_original', None)
            if datetime_original:
                return datetime_original.strftime('%Y:%m:%d %H:%M:%S')

            exif_dt = getattr(metadata, 'exif_datetime', None)
            if exif_dt:
                return exif_dt.strftime('%Y:%m:%d %H:%M:%S')

            # Fallback to file modification time if no metadata found
            ts = os.path.getmtime(raw_path)
            fallback_time = datetime.datetime.fromtimestamp(ts)
            return fallback_time.strftime('%Y:%m:%d %H:%M:%S')

    except Exception:
        return None

def get_creation_time(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    raw_extensions = ('.cr2', '.nef', '.arw', '.dng', '.rw2', '.orf')

    if ext in raw_extensions:
        return get_raw_creation_time(file_path)
    else:
        return get_exif_creation_time(file_path)

class WorkerThread(QThread):
    progress = Signal(int)
    result = Signal(dict)
    finished = Signal()
    raw_found = Signal(bool)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        supported_extensions = ('.jpg', '.jpeg', '.tiff', '.png', '.cr2', '.nef', '.arw', '.dng', '.rw2', '.orf')
        raw_extensions = ('.cr2', '.nef', '.arw', '.dng', '.rw2', '.orf')
        results = {}
        files_list = []

        raw_files_found = False

        for root, _, files in os.walk(self.folder_path):
            for filename in files:
                if filename.lower().endswith(supported_extensions):
                    full_path = os.path.join(root, filename)
                    files_list.append(full_path)
                    if filename.lower().endswith(raw_extensions):
                        raw_files_found = True

        total_files = len(files_list)
        for i, file_path in enumerate(files_list):
            creation_time = get_creation_time(file_path)
            results[file_path] = creation_time
            self.progress.emit(int((i+1)/total_files*100))

        self.result.emit(results)
        self.raw_found.emit(raw_files_found)
        self.finished.emit()

class PhotoMetadataApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Creation Time Extractor")
        self.resize(800, 600)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Select folder and click 'Scan'")
        self.layout.addWidget(self.label)

        self.btn_select = QPushButton("Select Folder")
        self.btn_select.clicked.connect(self.select_folder)
        self.layout.addWidget(self.btn_select)

        self.btn_scan = QPushButton("Scan Folder")
        self.btn_scan.setEnabled(False)
        self.btn_scan.clicked.connect(self.start_scan)
        self.layout.addWidget(self.btn_scan)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["File Path", "Creation Time", "File Type"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)

        self.btn_export = QPushButton("Export to CSV")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_csv)
        self.layout.addWidget(self.btn_export)

        self.folder_path = None
        self.results = {}
        self.raw_files_found = False

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", os.path.expanduser("~"))
        if folder:
            self.folder_path = folder
            self.label.setText(f"Selected folder: {folder}")
            self.btn_scan.setEnabled(True)
            self.table.setRowCount(0)
            self.btn_export.setEnabled(False)
            self.results = {}
            self.raw_files_found = False

    def start_scan(self):
        if not self.folder_path:
            return
        self.btn_scan.setEnabled(False)
        self.btn_select.setEnabled(False)
        self.label.setText("Scanning... Please wait.")
        self.thread = WorkerThread(self.folder_path)
        self.thread.progress.connect(self.update_progress)
        self.thread.result.connect(self.show_results)
        self.thread.raw_found.connect(self.set_raw_flag)
        self.thread.finished.connect(self.scan_finished)
        self.thread.start()

    def update_progress(self, val):
        self.label.setText(f"Scanning... {val}%")

    def set_raw_flag(self, found):
        self.raw_files_found = found

    def show_results(self, results):
        self.results = results
        self.table.setRowCount(len(results))
        raw_extensions = ('.cr2', '.nef', '.arw', '.dng', '.rw2', '.orf')
        for row, (file_path, creation_time) in enumerate(results.items()):
            self.table.setItem(row, 0, QTableWidgetItem(file_path))
            self.table.setItem(row, 1, QTableWidgetItem(creation_time or "No data"))
            ext = os.path.splitext(file_path)[1].lower()
            file_type = "RAW" if ext in raw_extensions else "Image"
            self.table.setItem(row, 2, QTableWidgetItem(file_type))

    def scan_finished(self):
        msg = "Scan complete."
        if self.raw_files_found:
            msg += " RAW files were detected and processed."
        self.label.setText(msg)
        self.btn_scan.setEnabled(True)
        self.btn_select.setEnabled(True)
        if self.results:
            self.btn_export.setEnabled(True)

    def export_csv(self):
        if not self.results:
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "photo_metadata.csv", "CSV Files (*.csv)")
        if save_path:
            try:
                raw_extensions = ('.cr2', '.nef', '.arw', '.dng', '.rw2', '.orf')
                with open(save_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["File Path", "Creation Time", "File Type"])
                    for file_path, creation_time in self.results.items():
                        ext = os.path.splitext(file_path)[1].lower()
                        file_type = "RAW" if ext in raw_extensions else "Image"
                        writer.writerow([file_path, creation_time or "No data", file_type])
                QMessageBox.information(self, "Export Successful", f"Data exported to {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Error: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhotoMetadataApp()
    window.show()
    sys.exit(app.exec())
