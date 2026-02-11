"""
Thumbnail generation utilities for image files.
"""

from contextlib import redirect_stderr
from io import StringIO
from PIL import Image
from pathlib import Path
from typing import Optional

from file_scanner import IMAGE_EXTENSIONS

THUMBNAIL_SIZE = (150, 150)


def create_thumbnail(file_path: str, size: tuple = THUMBNAIL_SIZE) -> Optional[Image.Image]:
    """
    Create a thumbnail from an image file.
    Suppresses libpng iCCP warnings and strips ICC profile to avoid Qt ICC warnings when displaying.
    """
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in IMAGE_EXTENSIONS:
        return None

    try:
        with redirect_stderr(StringIO()):
            with Image.open(file_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.thumbnail(size, Image.Resampling.LANCZOS)
                thumb = img.copy()
        # Strip ICC profile so Qt doesn't warn when loading the thumbnail as PNG
        if getattr(thumb, 'info', None) and 'icc_profile' in thumb.info:
            thumb.info.pop('icc_profile', None)
        return thumb
    except Exception:
        return None
