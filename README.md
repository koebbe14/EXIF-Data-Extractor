# EXIF Data Extractor

A desktop application for extracting, viewing, and exporting EXIF and metadata from digital image and video files. Built with Python and PyQt5, it is designed for investigative, forensic, and analytical workflows where understanding the origin, timing, and location context of media files is essential.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## Features

- **Image & Video Metadata Extraction** — Reads EXIF data from 20 image formats and container metadata from 18 video formats
- **Key Fields Extracted** — Date/time of creation, GPS coordinates (latitude, longitude, altitude), device make and model, serial numbers, and software/firmware versions
- **Full Metadata Inspection** — Right-click any file to view every embedded metadata tag, including exposure settings, lens data, color profiles, codec details, and proprietary manufacturer fields
- **Search** — Global search across filenames, metadata fields, GPS coordinates, and serial numbers with partial or exact matching. Optional deep search through all EXIF/MediaInfo tags
- **Filter** — Narrow results by file type (images/videos), GPS availability, serial number presence, date range, file extension, make, model, and software. Filters are combined with AND logic
- **Sorting** — Click any column header to sort results. Numeric and date columns sort by value, not alphabetically
- **Append or Replace Import** — When importing additional files with results already loaded, choose to replace existing data or append new files (duplicates are automatically skipped)
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

### From Source

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

### Standalone Executable

A pre-built `.exe` is available on the [Releases](https://github.com/YOUR_USERNAME/EXIF-Data-Extractor/releases) page. No Python installation required — just download and run.

To build the executable yourself:
```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --icon=icon.ico --name "EXIF Data Extractor" main.py
```
The output will be in the `dist/` folder.

---

## Usage

### Importing Files

There are three ways to load media files:

1. **Import Files or Folder** — Click the button or use `File > Open Folder` (`Ctrl+O`). Select a folder and all sub-folders will be scanned recursively.
2. **Drag & Drop a Folder** — Drag any folder from Windows Explorer onto the application window.
3. **Drag & Drop Individual Files** — Drag one or more files onto the window. Unsupported file types are silently skipped.

### Search

Click the **Search** button in the toolbar to open the Search dialog:

- **Partial match** (default) — Case-insensitive substring search across all parsed fields (filename, path, make, model, serial, software, GPS, timestamp)
- **Exact match** — Uncheck "Partial match" to require each keyword to appear as a complete token
- **GPS search** — Enter `34.0522` to match any latitude or longitude, or `34.0522,-118.2437` to match both
- **Include full metadata** — Also searches all EXIF/MediaInfo tags, not just the table columns (slower on large collections)

Click **Clear** in the Search dialog or **Clear Search/Filters** in the toolbar to reset.

### Filter

Click the **Filter** button in the toolbar to open the Filter dialog. All filters are combined (AND logic):

- **File type** — All / Images only / Videos only
- **GPS** — Any / Has GPS / Missing GPS
- **Serial number** — Any / Present / Missing
- **Date range** — Enable From and/or To dates to restrict results by embedded timestamp
- **Extensions / Make / Model / Software** — Multi-select checklists populated from your loaded results. Check items to show only matching files

Click **Clear** in the Filter dialog or **Clear Search/Filters** in the toolbar to reset all filters.

### Sorting

Click any column header in the results table to sort by that column. Click again to reverse the order. Numeric columns (latitude, longitude, altitude) and date columns sort correctly by value.

### Importing Additional Files

When you import new files while results are already loaded, a dialog asks you to choose:

- **Replace** — Clear existing results and load only the new files
- **Append** — Add new files to the existing results (duplicate file paths are automatically skipped)

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

---

## Project Structure

```
EXIF Data Extractor/
├── main.py                 # Application entry point and GUI (PyQt5)
├── file_scanner.py         # Directory scanning and file type detection
├── exif_extractor.py       # EXIF/metadata extraction (images and videos)
├── data_model.py           # ExifData dataclass
├── exif_table_model.py     # QAbstractTableModel for the results table
├── exif_filter_proxy.py    # QSortFilterProxyModel for search, filter, and sorting
├── search_dialog.py        # Search dialog UI
├── filter_dialog.py        # Filter dialog UI
├── import_mode_dialog.py   # Replace/Append import dialog
├── export_utils.py         # CSV, JSON, PDF, and KMZ export
├── map_utils.py            # Google Maps integration
├── thumbnail_utils.py      # Thumbnail generation (images and videos)
├── requirements.txt        # Python dependencies
├── icon.ico                # Application icon
└── README.md
```

---

## Dependencies

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

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Author

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
