"""
File scanner module for finding image files in a directory.
Recursively scans for common image formats.
"""

import os
from pathlib import Path
from typing import List


# Supported image file extensions
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.tiff', '.tif',
    '.heic', '.heif', '.cr2', '.nef', '.arw',
    '.dng', '.orf', '.raf', '.rw2', '.pef',
    '.srw', '.x3f', '.bmp', '.gif', '.webp'
}


def scan_directory(directory: str, recursive: bool = True) -> List[str]:
    """
    Scan a directory for image files.

    Args:
        directory: Path to the directory to scan
        recursive: If True, scan subdirectories recursively

    Returns:
        List of file paths to image files
    """
    image_files = []
    directory_path = Path(directory)

    if not directory_path.exists() or not directory_path.is_dir():
        return image_files

    if recursive:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                    image_files.append(str(file_path))
    else:
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
                image_files.append(str(file_path))

    return sorted(image_files)
