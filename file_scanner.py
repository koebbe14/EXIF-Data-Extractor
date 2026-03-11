"""
File scanner module for finding media files in a directory.
Recursively scans for common image and video formats.
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

# Supported video file extensions
VIDEO_EXTENSIONS = {
    '.mp4', '.m4v', '.mov', '.avi', '.mkv',
    '.wmv', '.asf', '.flv', '.webm',
    '.3gp', '.3g2', '.mts', '.m2ts', '.ts',
    '.vob', '.mpg', '.mpeg', '.ogv',
}

MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def is_video_file(file_path: str) -> bool:
    """Check whether a file path has a video extension."""
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


def scan_directory(directory: str, recursive: bool = True) -> List[str]:
    """
    Scan a directory for media files (images and videos).

    Args:
        directory: Path to the directory to scan
        recursive: If True, scan subdirectories recursively

    Returns:
        List of file paths to media files
    """
    media_files = []
    directory_path = Path(directory)

    if not directory_path.exists() or not directory_path.is_dir():
        return media_files

    if recursive:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in MEDIA_EXTENSIONS:
                    media_files.append(str(file_path))
    else:
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in MEDIA_EXTENSIONS:
                media_files.append(str(file_path))

    return sorted(media_files)
