"""
EXIF data extraction module for image files.
Extracts only date/time, GPS coordinates, and device identifiers.
Excludes exposure settings and image metadata.
"""

import exifread
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from typing import List, Optional, Tuple
from data_model import ExifData
import os
import warnings
from pathlib import Path
from contextlib import redirect_stderr
from io import StringIO

# Increase PIL image size limit to handle large images (we only read EXIF, not the full image)
Image.MAX_IMAGE_PIXELS = None  # Disable decompression bomb check
warnings.filterwarnings('ignore', category=Image.DecompressionBombWarning)


def _convert_to_decimal(degrees, minutes, seconds, ref):
    """
    Convert GPS coordinates from degrees/minutes/seconds to decimal.
    """
    decimal = float(degrees) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal


def _get_gps_data(exif_data):
    """
    Extract GPS coordinates from EXIF data (PIL format).
    """
    if 'GPSInfo' not in exif_data:
        return None, None, None

    gps_info = exif_data['GPSInfo']
    lat = lon = alt = None

    if 2 in gps_info and 3 in gps_info:
        lat_deg, lat_min, lat_sec = gps_info[2][0], gps_info[2][1], gps_info[2][2]
        lat_ref = gps_info[3]
        lat = _convert_to_decimal(lat_deg, lat_min, lat_sec, lat_ref)

    if 4 in gps_info and 5 in gps_info:
        lon_deg, lon_min, lon_sec = gps_info[4][0], gps_info[4][1], gps_info[4][2]
        lon_ref = gps_info[5]
        lon = _convert_to_decimal(lon_deg, lon_min, lon_sec, lon_ref)

    if 6 in gps_info:
        alt = float(gps_info[6])

    return lat, lon, alt


def _parse_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse EXIF datetime string to datetime object.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        pass

    try:
        from dateutil import parser as dateutil_parser
        return dateutil_parser.parse(date_str)
    except Exception:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(date_str.replace('Z', '').split('.')[0].strip(), fmt)
        except (ValueError, TypeError):
            continue
    return None


# Tag keys that contain binary data; show a short summary instead of raw bytes
_BINARY_TAGS = frozenset({
    'JPEGThumbnail', 'TIFFThumbnail', 'EXIF MakerNote', 'EXIF Makernote',
    'InteroperabilityTag', 'Image Tag 0x927C', 'Image Tag 0x9C9B', 'Image Tag 0x9C9C',
})


def get_all_exif_tags(file_path: str) -> List[Tuple[str, str]]:
    """
    Read all EXIF/metadata tags from an image file for display.
    Returns a sorted list of (tag_name, value_str). Binary tags are summarized as "(binary, N bytes)".
    On error returns an empty list.
    """
    result: List[Tuple[str, str]] = []
    seen: set = set()

    def add_tag(name: str, value_str: str) -> None:
        if name in seen:
            return
        seen.add(name)
        result.append((name, value_str))

    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f)
    except (OSError, IOError, ValueError):
        return []

    for tag_name, value in tags.items():
        if tag_name in _BINARY_TAGS or isinstance(value, (bytes, bytearray)):
            try:
                size = len(value)
            except (TypeError, AttributeError):
                size = 0
            add_tag(tag_name, f"(binary, {size} bytes)")
        else:
            try:
                add_tag(tag_name, str(value).strip())
            except Exception:
                add_tag(tag_name, "(unable to convert)")

    if not result:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')
                with redirect_stderr(StringIO()):
                    with Image.open(file_path) as img:
                        if hasattr(img, '_getexif') and img._getexif() is not None:
                            for tag_id, value in img._getexif().items():
                                name = TAGS.get(tag_id, f"Tag {tag_id}")
                                if name in seen:
                                    continue
                                seen.add(name)
                                try:
                                    result.append((name, str(value).strip()))
                                except Exception:
                                    result.append((name, "(unable to convert)"))
        except Exception:
            pass

    return sorted(result, key=lambda x: x[0])


def extract_exif_data(file_path: str) -> ExifData:
    """
    Extract EXIF data from an image file.
    Only extracts date/time, GPS coordinates, and device identifiers.
    """
    file_name = os.path.basename(file_path)
    exif_data = ExifData(file_path=file_path, file_name=file_name)

    try:
        stderr_capture = StringIO()
        with redirect_stderr(stderr_capture):
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

            for date_tag in ['EXIF DateTimeOriginal', 'Image DateTime', 'EXIF DateTimeDigitized']:
                if date_tag in tags:
                    date_str = str(tags[date_tag])
                    exif_data.date_taken = _parse_datetime(date_str)
                    if exif_data.date_taken:
                        break

            if 'Image Make' in tags:
                exif_data.make = str(tags['Image Make']).strip()
            if 'Image Model' in tags:
                exif_data.model = str(tags['Image Model']).strip()
            if 'EXIF BodySerialNumber' in tags:
                exif_data.serial_number = str(tags['EXIF BodySerialNumber']).strip()
            elif 'Image SerialNumber' in tags:
                exif_data.serial_number = str(tags['Image SerialNumber']).strip()
            if 'Image Software' in tags:
                exif_data.software = str(tags['Image Software']).strip()

            if 'GPS GPSLatitude' in tags and 'GPS GPSLatitudeRef' in tags:
                lat_deg = tags['GPS GPSLatitude'].values[0]
                lat_min = tags['GPS GPSLatitude'].values[1]
                lat_sec = tags['GPS GPSLatitude'].values[2]
                lat_ref = str(tags['GPS GPSLatitudeRef'])
                exif_data.latitude = _convert_to_decimal(lat_deg, lat_min, lat_sec, lat_ref)

            if 'GPS GPSLongitude' in tags and 'GPS GPSLongitudeRef' in tags:
                lon_deg = tags['GPS GPSLongitude'].values[0]
                lon_min = tags['GPS GPSLongitude'].values[1]
                lon_sec = tags['GPS GPSLongitude'].values[2]
                lon_ref = str(tags['GPS GPSLongitudeRef'])
                exif_data.longitude = _convert_to_decimal(lon_deg, lon_min, lon_sec, lon_ref)

            if 'GPS GPSAltitude' in tags:
                alt = tags['GPS GPSAltitude']
                exif_data.altitude = float(alt.values[0])
                if 'GPS GPSAltitudeRef' in tags and str(tags['GPS GPSAltitudeRef']) == '1':
                    exif_data.altitude = -exif_data.altitude

        if not exif_data.has_gps():
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore')
                    try:
                        with redirect_stderr(StringIO()):
                            with Image.open(file_path) as img:
                                if hasattr(img, '_getexif') and img._getexif() is not None:
                                    exif_dict = img._getexif()
                                    lat, lon, alt = _get_gps_data(exif_dict)
                                    if lat is not None:
                                        exif_data.latitude = lat
                                    if lon is not None:
                                        exif_data.longitude = lon
                                    if alt is not None:
                                        exif_data.altitude = alt
                                    if exif_data.date_taken is None:
                                        for tag_id, value in exif_dict.items():
                                            tag = TAGS.get(tag_id, tag_id)
                                            if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                                                exif_data.date_taken = _parse_datetime(str(value))
                                                if exif_data.date_taken:
                                                    break
                                    if not exif_data.make:
                                        for tag_id, value in exif_dict.items():
                                            tag = TAGS.get(tag_id, tag_id)
                                            if tag == 'Make':
                                                exif_data.make = str(value).strip()
                                            elif tag == 'Model':
                                                exif_data.model = str(value).strip()
                                            elif tag == 'Software':
                                                exif_data.software = str(value).strip()
                    except (Exception, IOError, OSError):
                        pass
            except Exception:
                pass

    except Exception:
        pass

    return exif_data
