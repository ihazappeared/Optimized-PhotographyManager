# Photo Organizer

A multi-threaded desktop application to organize photos and videos into structured folders based on their metadata. Supports flexible folder naming schemes, video separation, excluded folders, and cache management — all through an intuitive Qt GUI.

---

## Features

- Extracts photo/video date metadata using EXIF or file modification time fallback  
- Organizes files into folders by day, month/day, year/month/day, or day-of-year  
- Separate folder for videos option  
- Exclude specific folders from scanning  
- Caches metadata for faster repeated runs  
- Multi-threaded processing for speed  
- Removes empty folders after organizing (optional)  
- Thread-safe file moving with duplicate filename resolution  
- Responsive GUI with progress bar and live logs  
- Save/load user settings and cache  
- Reset cache and settings option  

---

## Requirements

- Python 3.8+  
- PyQt5 or PySide2  
- Pillow (PIL)  
- psutil  
- Compatible with Windows, Linux, macOS (with some platform-specific behavior)

---

## Installation

1. Clone or download the repository.  
2. Install dependencies:  
   ``bash
   pip install PyQt5 Pillow psutil
 ``
## Run the app:

- bash
- Copy
- Edit
- python photo_organizer.py
- Usage
- Select the base directory containing your photos/videos.

- Choose the desired folder structure for organizing files:

- Day (DD-MM-YYYY)

- Month/Day (YYYY/Month/DD)

- Year/Month/Day (YYYY/MM/DD)

- Year/Day of Year (YYYY/DDD)

- Check the option to separate videos into their own Videos folder if desired.

- Add any folders to exclude from scanning.

- Optionally enable removing empty folders after organizing.

- Click Start Organizing. Progress and logs will update live.

- Reset settings and cache if needed via the reset button.

## Notes
The app respects hidden and system files when removing empty folders (Windows only).

Metadata caching speeds up repeated runs by avoiding re-extraction of unchanged files.

Duplicate filename conflicts are resolved by renaming files to avoid overwriting.

OneDrive running status is detected to warn about possible interference (disabled by default).

## Troubleshooting
Ensure you have read/write permissions on the base directory and any target folders.

If files are skipped or errors occur, check logs in the app window for details.

For large collections, initial runs may take time due to metadata extraction.

License
MIT License
