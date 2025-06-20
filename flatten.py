import os
import shutil
import re
from typing import Optional

def flatten_folder_tree(root_dir: str, target_dir: str) -> None:
    """
    Move all files from root_dir (including all subdirectories) into target_dir,
    then remove all empty directories under root_dir.

    Args:
        root_dir: The root directory to flatten.
        target_dir: The directory where all files will be moved.

    Raises:
        ValueError: If target_dir is inside root_dir or vice versa, to avoid recursion issues.
    """
    root_dir = os.path.abspath(root_dir)
    target_dir = os.path.abspath(target_dir)

    if target_dir.startswith(root_dir) and target_dir != root_dir:
        raise ValueError("target_dir cannot be inside root_dir.")
    if root_dir.startswith(target_dir) and target_dir != root_dir:
        raise ValueError("root_dir cannot be inside target_dir.")

    os.makedirs(target_dir, exist_ok=True)

    existing_files = set(os.listdir(target_dir))

    for current_dir, _, files in os.walk(root_dir, topdown=False):
        for file in files:
            src_path = os.path.join(current_dir, file)
            if not os.path.isfile(src_path):
                continue  # Skip if not a file

            new_name = file
            base, ext = os.path.splitext(new_name)

            # Avoid overwriting by adding suffixes if name exists
            candidate_name = new_name
            counter = 1
            while candidate_name in existing_files:
                candidate_name = f"{base}_{counter}{ext}"
                counter += 1

            existing_files.add(candidate_name)
            dest_path = os.path.join(target_dir, candidate_name)
            shutil.move(src_path, dest_path)

        if current_dir != root_dir:
            try:
                os.rmdir(current_dir)
            except OSError:
                # Directory not empty or permission denied, skip removal
                pass

def clean_img_filenames(folder: str, recursive: bool = True, log_fn: Optional[callable] = None) -> None:
    """
    Rename files in `folder` to keep only the 'IMG_<digits>' pattern in their basename,
    removing any prefixes or suffixes outside this pattern.

    Args:
        folder: Directory to process.
        recursive: If True, process files in all subdirectories as well.
    """
    pattern = re.compile(r'IMG_(\d+)')

    if recursive:
        walker = os.walk(folder)
    else:
        walker = [(folder, [], os.listdir(folder))]

    for dirpath, _, files in walker:
        for filename in files:
            filepath = os.path.join(dirpath, filename)
            if not os.path.isfile(filepath):
                continue

            base, ext = os.path.splitext(filename)

            # Search for IMG_<digits> pattern anywhere in the filename
            match = pattern.search(base)
            if match:
                new_base = f"IMG_{match.group(1)}"
                # If new filename is already clean, skip renaming
                if new_base == base:
                    continue
                new_name = new_base + ext
                new_path = os.path.join(dirpath, new_name)

                # Handle potential naming conflicts by adding suffix _1, _2, ...
                counter = 1
                while os.path.exists(new_path):
                    new_name = f"{new_base}_{counter}{ext}"
                    new_path = os.path.join(dirpath, new_name)
                    counter += 1

                os.rename(filepath, new_path)
                if log_fn:
                    log_fn(f"Renamed: {filepath} -> {new_path}")
            else:
                # No IMG_<digits> pattern, skip or optionally handle differently
                pass
