# EXIF Data Extractor

A desktop application for extracting, viewing, and exporting EXIF and metadata from digital image and video files. Built with Python and PyQt5, it is designed for investigative, forensic, and analytical workflows where understanding the origin, timing, and location context of media files is essential.

![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)

---

## Features

- **Image & Video Metadata Extraction** — Reads EXIF data from 20 image formats and container metadata from 18 video formats
- **Key Fields Extracted** — Date/time of creation, GPS coordinates (latitude, longitude, altitude), device make and model, serial numbers, and software/firmware versions
- **Full Metadata Inspection** — Right-click any file to view every embedded metadata tag, including exposure settings, lens data, color profiles, codec details, and proprietary manufacturer fields
- **Thumbnail Generation** — Visual previews for both images and videos; video thumbnails are captured from an early frame
- **GPS Visualization** — Open file coordinates directly in Google Maps
- **Multiple Export Formats** — CSV, JSON, PDF (formatted reports with thumbnails and clickable GPS links), and KMZ (Google Earth placemarks with thumbnails)
- **Drag-and-Drop Support** — Import folders or individual files by dragging them onto the application window
- **Recursive Scanning** — Automatically scans all sub-folders within a selected directory
- **Dark Mode** — Toggle between light and dark themes from the File menu; preference is saved between sessions
- **Standalone Executable** — Can be packaged as a single `.exe` with PyInstaller

---

## Screenshots

<!-- Add screenshots of your application here -->
<!-- ![Main Window](screenshots/main_window.png) -->
<!-- ![Dark Mode](screenshots/dark_mode.png) -->

---

## Supported File Formats

### Images (20 formats)

| Format | Extensions |
|--------|-----------|
| Standard | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.webp`, `.tiff`, `.tif` |
| Apple | `.heic`, `.heif` |
| RAW | `.cr2` (Canon), `.nef` (Nikon), `.arw` (Sony), `.dng` (Adobe), `.orf` (Olympus), `.raf` (Fuji), `.rw2` (Panasonic), `.pef` (Pentax), `.srw` (Samsung), `.x3f` (Sigma) |

### Videos (18 formats)

| Format | Extensions |
|--------|-----------|
| Common | `.mp4`, `.m4v`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.webm`, `.flv` |
| Broadcast/DVD | `.mts`, `.m2ts`, `.ts`, `.vob`, `.mpg`, `.mpeg` |
| Other | `.asf`, `.3gp`, `.3g2`, `.ogv` |

---

## Extracted Metadata Fields

| Field | Description |
|-------|-------------|
| **Thumbnail** | Visual preview of the file (optional) |
| **File Name** | Name of the file on disk |
| **Timestamp** | Original creation date/time from EXIF (images) or container metadata (videos) — not the filesystem date |
| **Latitude** | GPS latitude in decimal degrees |
| **Longitude** | GPS longitude in decimal degrees |
| **Altitude** | GPS altitude in meters above/below sea level |
| **Make** | Device manufacturer (e.g., Apple, Samsung, Canon) |
| **Model** | Device model (e.g., iPhone 13 Pro Max, Galaxy A54 5G) |
| **Serial Number** | Device serial number, if embedded |
| **Software** | Firmware or application used to create the file |

---

## Installation

### Prerequisites

- Python 3.8 or higher
- MediaInfo library (bundled automatically on Windows via the `pymediainfo` pip package)

### Standalone Executable

A pre-built `.exe` is available on the [Releases](https://github.com/koebbe14/EXIF-Data-Extractor/releases) page. No Python installation required — just download and run.


#### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/EXIF-Data-Extractor.git
   cd EXIF-Data-Extractor
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```



## Usage

### Importing Files

There are three ways to load media files:

1. **Import Files or Folder** — Click the button or use `File > Open Folder` (`Ctrl+O`). Select a folder and all sub-folders will be scanned recursively.
2. **Drag & Drop a Folder** — Drag any folder from Windows Explorer onto the application window.
3. **Drag & Drop Individual Files** — Drag one or more files onto the window. Unsupported file types are silently skipped.

### Viewing Metadata

- The results table shows key metadata for each file
- **Right-click** any row and select **View all EXIF / Metadata** to see every tag in the file
- For images: all EXIF, GPS, MakerNote, and vendor-specific fields
- For videos: complete MediaInfo output across all tracks (General, Video, Audio, Text)

### GPS & Map View

Select a row with GPS data and click **View on Map** to open the coordinates in Google Maps.

### Exporting

| Format | Description |
|--------|-------------|
| **CSV** | Comma-separated values for spreadsheets (Excel, Google Sheets). One row per file. |
| **JSON** | Structured data for programmatic use, databases, or case management systems. |
| **PDF** | Formatted landscape report with thumbnails and clickable GPS links. Suitable for case files. |
| **KMZ** | Google Earth placemarks with thumbnails and file details for every GPS-tagged file. |

### Dark Mode

Toggle dark mode from `File > Dark Mode`. The preference persists between sessions.

---

## How It Works

### Image Metadata
Image EXIF data is extracted using [exifread](https://pypi.org/project/ExifRead/) and [Pillow](https://python-pillow.org/). These libraries parse the EXIF/TIFF metadata block embedded in image files, capturing date/time, GPS, device identifiers, exposure parameters, lens information, and vendor-specific MakerNote data. HEIC/HEIF support is provided by [pillow-heif](https://github.com/bigcat88/pillow_heif).

### Video Metadata
Video metadata is extracted using [pymediainfo](https://pymediainfo.readthedocs.io/), a Python wrapper for the [MediaInfo](https://mediaarea.net/en/MediaInfo) library. This reads container-level and track-level metadata from standard video formats. GPS coordinates stored as ISO 6709 location strings are automatically parsed into decimal latitude, longitude, and altitude.

### Thumbnails
- **Images** — Scaled-down copies generated by Pillow
- **Videos** — A frame near the start of the clip captured by [OpenCV](https://opencv.org/)


## Dependencies

All Dependencies are packaged in the .EXE

| Package | Purpose |
|---------|---------|
| [PyQt5](https://pypi.org/project/PyQt5/) | GUI framework |
| [exifread](https://pypi.org/project/ExifRead/) | Pure-Python EXIF parser for images |
| [Pillow](https://python-pillow.org/) | Image processing and thumbnail generation |
| [pillow-heif](https://github.com/bigcat88/pillow_heif) | HEIC/HEIF image support for Pillow |
| [pymediainfo](https://pymediainfo.readthedocs.io/) | Video metadata extraction (MediaInfo wrapper) |
| [opencv-python-headless](https://pypi.org/project/opencv-python-headless/) | Video frame extraction for thumbnails |
| [ReportLab](https://pypi.org/project/reportlab/) | PDF report generation |
| [python-dateutil](https://pypi.org/project/python-dateutil/) | Flexible date/time string parsing |

---

## Use Cases

- **Digital Forensics** — Identify when and where media files were created and which device produced them
- **Investigations** — Correlate GPS coordinates and timestamps across multiple files to establish timelines and locations
- **Evidence Documentation** — Generate PDF reports or KMZ map files for inclusion in case files

---

## Contributing

Contributions are welcome. Please open an issue to discuss proposed changes before submitting a pull request.

---

## License

Permission is hereby granted to law-enforcement agencies, digital-forensic analysts, and authorized investigative personnel ("Authorized Users") to use and copy this software for the purpose of criminal investigations, evidence review, training, or internal operational use.

The following conditions apply:

Redistribution: This software may not be sold, published, or redistributed to the general public. Redistribution outside an authorized agency requires written permission from the developer.

No Warranty: This software is provided "AS IS," without warranty of any kind, express or implied, including but not limited to the warranties of accuracy, completeness, performance, non-infringement, or fitness for a particular purpose. The developer shall not be liable for any claim, damages, or other liability arising from the use of this software, including the handling of digital evidence.

Evidence Integrity: Users are responsible for maintaining forensic integrity and chain of custody when handling evidence. This software does not alter source evidence files and is intended only for analysis and review.

Modifications: Agencies and investigators may modify the software for internal purposes. Modified versions may not be publicly distributed without permission from the developer.

Logging & Privacy: Users are responsible for controlling log files and output generated during use of the software to prevent unauthorized disclosure of sensitive or personally identifiable information.

Compliance: Users agree to comply with all applicable laws, departmental policies, and legal requirements when using the software.

By using this software, the user acknowledges that they have read, understood, and agreed to the above terms.

---

## Developer

**Patrick Koebbe**
- Email: patrick.koebbe@gmail.com

---

## Acknowledgements

- [MediaInfo](https://mediaarea.net/en/MediaInfo) by MediaArea.net SARL
- [exifread](https://pypi.org/project/ExifRead/) by ianaré sévi
- [Pillow](https://python-pillow.org/) by the Pillow contributors
- [pillow-heif](https://github.com/bigcat88/pillow_heif) by bigcat88
- [OpenCV](https://opencv.org/) (headless build)
- [ReportLab](https://www.reportlab.com/)
