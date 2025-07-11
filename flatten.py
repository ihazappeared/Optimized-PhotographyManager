import os
import shutil
import re
from typing import Optional, Callable
from collections import deque


def flatten_folder_tree(root_dir: str, target_dir: str) -> None:
    root_dir, target_dir = map(os.path.abspath, (root_dir, target_dir))
    if (target_dir.startswith(root_dir) or root_dir.startswith(target_dir)) and root_dir != target_dir:
        raise ValueError("Directories cannot be nested inside each other.")

    os.makedirs(target_dir, exist_ok=True)
    existing = set(os.listdir(target_dir))

    stack = deque()
    for dirpath, _, files in os.walk(root_dir, topdown=False):
        stack.append((dirpath, files))

    while stack:
        dirpath, files = stack.pop()
        for f in files:
            src = os.path.join(dirpath, f)
            if not os.path.isfile(src):
                continue

            name, ext = os.path.splitext(f)
            new_name = f
            count = 1
            while new_name in existing:
                new_name = f"{name}_{count}{ext}"
                count += 1
            existing.add(new_name)

            shutil.move(src, os.path.join(target_dir, new_name))

        if dirpath != root_dir:
            try:
                os.rmdir(dirpath)
            except OSError:
                pass


def clean_img_filenames(folder: str, recursive: bool = True, log_fn: Optional[Callable[[str], None]] = None) -> None:
    pattern = re.compile(r'IMG_(\d+)')
    walk = os.walk(folder) if recursive else [(folder, [], os.listdir(folder))]

    for dirpath, _, files in walk:
        existing = set(files)

        for f in files:
            path = os.path.join(dirpath, f)
            if not os.path.isfile(path):
                continue

            base, ext = os.path.splitext(f)
            match = pattern.search(base)
            if not match:
                continue

            new_base = f"IMG_{match.group(1)}"
            if new_base == base:
                continue

            new_name = f"{new_base}{ext}"
            count = 1
            while new_name in existing or os.path.exists(os.path.join(dirpath, new_name)):
                new_name = f"{new_base}_{count}{ext}"
                count += 1

            new_path = os.path.join(dirpath, new_name)
            os.rename(path, new_path)
            existing.remove(f)
            existing.add(new_name)

            if log_fn:
                log_fn(f"Renamed: {path} -> {new_path}")
