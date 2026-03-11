"""
Main application window for EXIF Data Extractor GUI.
"""

import sys
import os

# Suppress Qt ICC profile warnings when loading thumbnails (unsupported profile class)
os.environ["QT_LOGGING_RULES"] = "qt.gui.icc=false"

import io
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog,
    QProgressBar, QStatusBar, QMessageBox, QHeaderView, QLabel,
    QMenu, QAction, QDialog, QTextEdit, QTextBrowser, QDialogButtonBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPalette, QColor

from file_scanner import scan_directory, MEDIA_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from exif_extractor import extract_exif_data, get_all_exif_tags
from data_model import ExifData
from export_utils import export_to_csv, export_to_json, export_to_pdf, export_to_kmz
from map_utils import open_location_in_map
from thumbnail_utils import create_thumbnail


class ExtractionWorker(QThread):
    """Worker thread for extracting metadata from media files."""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)  # list of ExifData
    error = pyqtSignal(str)  # error message
    
    def __init__(self, media_files, generate_thumbnails=False):
        super().__init__()
        self.media_files = media_files
        self.generate_thumbnails = generate_thumbnails
    
    def run(self):
        """Extract metadata from all media files."""
        import warnings
        import sys
        from io import StringIO
        from contextlib import redirect_stderr
        
        exif_data_list = []
        total = len(self.media_files)
        
        for i, file_path in enumerate(self.media_files):
            try:
                # Suppress all stderr and warnings (e.g. libpng iCCP, Qt ICC) during extraction and thumbnail creation
                stderr_capture = StringIO()
                with redirect_stderr(stderr_capture):
                    with warnings.catch_warnings():
                        warnings.filterwarnings('ignore')
                        exif_data = extract_exif_data(file_path)
                    if self.generate_thumbnails:
                        try:
                            thumbnail = create_thumbnail(file_path)
                            if thumbnail:
                                exif_data.thumbnail = thumbnail
                        except Exception:
                            pass
                exif_data_list.append(exif_data)
            except Exception as e:
                # Continue with next file if extraction fails
                # Still try to create a basic ExifData entry
                try:
                    from data_model import ExifData
                    import os
                    basic_data = ExifData(
                        file_path=file_path,
                        file_name=os.path.basename(file_path)
                    )
                    exif_data_list.append(basic_data)
                except Exception:
                    pass
            
            self.progress.emit(i + 1, total)
        
        self.finished.emit(exif_data_list)


class PDFExportWorker(QThread):
    """Worker thread for exporting EXIF data to PDF."""
    finished = pyqtSignal(bool)  # True if success, False otherwise

    def __init__(self, exif_data_list, file_path):
        super().__init__()
        self.exif_data_list = exif_data_list
        self.file_path = file_path

    def run(self):
        from export_utils import export_to_pdf
        success = export_to_pdf(self.exif_data_list, self.file_path)
        self.finished.emit(success)


DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #1e1e1e;
    color: #d4d4d4;
}
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
}
QMenuBar {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border-bottom: 1px solid #3c3c3c;
}
QMenuBar::item:selected {
    background-color: #094771;
}
QMenu {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
}
QMenu::item:selected {
    background-color: #094771;
}
QMenu::separator {
    height: 1px;
    background-color: #3c3c3c;
}
QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: 1px solid #1177bb;
    padding: 5px 16px;
    border-radius: 2px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #1177bb;
}
QPushButton:pressed {
    background-color: #094771;
}
QPushButton:disabled {
    background-color: #3c3c3c;
    color: #6e6e6e;
    border-color: #3c3c3c;
}
QTableWidget {
    background-color: #1e1e1e;
    alternate-background-color: #262626;
    color: #d4d4d4;
    gridline-color: #3c3c3c;
    border: 1px solid #3c3c3c;
    selection-background-color: #094771;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    padding: 4px;
    font-weight: bold;
}
QProgressBar {
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    text-align: center;
    color: #d4d4d4;
}
QProgressBar::chunk {
    background-color: #0e639c;
}
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
}
QLabel {
    color: #d4d4d4;
}
QTextBrowser, QTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
}
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #424242;
    min-height: 20px;
    border-radius: 3px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #525252;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 12px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #424242;
    min-width: 20px;
    border-radius: 3px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #525252;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QMessageBox {
    background-color: #1e1e1e;
}
QMessageBox QLabel {
    color: #d4d4d4;
}
QDialogButtonBox QPushButton {
    min-width: 70px;
}
QFileDialog {
    background-color: #1e1e1e;
    color: #d4d4d4;
}
"""


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.exif_data_list = []
        self.current_folder = None
        self._dark_mode = False
        self._settings = QSettings("EXIFDataExtractor", "EXIFDataExtractor")
        self.init_ui()
        if self._settings.value("dark_mode", "false") == "true":
            self._dark_mode_action.setChecked(True)
            self._apply_dark_mode(True)
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("EXIF Data Extractor")
        self.setGeometry(50, 50, 1600, 900)
        self.setAcceptDrops(True)
        self._create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        self.folder_button = QPushButton("Import Files or Folder")
        self.folder_button.clicked.connect(self.select_folder)
        controls_layout.addWidget(self.folder_button)
        
        self.folder_label = QLabel("")
        controls_layout.addWidget(self.folder_label)
        self.drop_hint = QLabel("or drag and drop here")
        self.drop_hint.setStyleSheet("color: #888; font-style: italic; font-size: 8pt;")
        controls_layout.addWidget(self.drop_hint)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(10)  # Added thumbnail column
        self.table.setHorizontalHeaderLabels([
            "Thumbnail", "File Name", "Timestamp", "Latitude", "Longitude", "Altitude",
            "Make", "Model", "Serial Number", "Software"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # Allow manual column resizing
        # Set initial column widths (ensure headers are not truncated)
        self.table.setColumnWidth(0, 192)  # Thumbnail
        self.table.setColumnWidth(1, 240)  # File Name
        self.table.setColumnWidth(2, 138)  # Timestamp
        self.table.setColumnWidth(3, 138)  # Latitude
        self.table.setColumnWidth(4, 153)  # Longitude
        self.table.setColumnWidth(5, 92)   # Altitude
        self.table.setColumnWidth(6, 110)  # Make
        self.table.setColumnWidth(7, 180)  # Model
        self.table.setColumnWidth(8, 168)  # Serial Number
        self.table.setColumnWidth(9, 138)  # Software
        # Set row height for thumbnails
        self.table.verticalHeader().setDefaultSectionSize(192)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        
        self.map_button = QPushButton("View on Map")
        self.map_button.setEnabled(False)
        self.map_button.clicked.connect(self.view_selected_on_map)
        buttons_layout.addWidget(self.map_button)
        
        buttons_layout.addStretch()
        
        self.export_csv_button = QPushButton("Export to CSV")
        self.export_csv_button.setEnabled(False)
        self.export_csv_button.clicked.connect(self.export_to_csv)
        buttons_layout.addWidget(self.export_csv_button)
        
        self.export_json_button = QPushButton("Export to JSON")
        self.export_json_button.setEnabled(False)
        self.export_json_button.clicked.connect(self.export_to_json)
        buttons_layout.addWidget(self.export_json_button)
        
        self.export_pdf_button = QPushButton("Export to PDF")
        self.export_pdf_button.setEnabled(False)
        self.export_pdf_button.clicked.connect(self.export_to_pdf)
        buttons_layout.addWidget(self.export_pdf_button)
        
        self.export_kmz_button = QPushButton("Export to KMZ")
        self.export_kmz_button.setEnabled(False)
        self.export_kmz_button.clicked.connect(self.export_to_kmz_handler)
        buttons_layout.addWidget(self.export_kmz_button)
        
        layout.addLayout(buttons_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _create_menu_bar(self):
        """Build the application menu bar."""
        menu_bar = self.menuBar()

        # --- File menu ---
        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open Folder...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("Select a folder to scan for media files")
        open_action.triggered.connect(self.select_folder)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        self._dark_mode_action = QAction("&Dark Mode", self)
        self._dark_mode_action.setCheckable(True)
        self._dark_mode_action.setStatusTip("Toggle dark mode appearance")
        self._dark_mode_action.triggered.connect(self._toggle_dark_mode)
        file_menu.addAction(self._dark_mode_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Help menu ---
        help_menu = menu_bar.addMenu("&Help")

        help_action = QAction("&Help", self)
        help_action.setShortcut("F1")
        help_action.setStatusTip("Show application help")
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.setStatusTip("About EXIF Data Extractor")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _toggle_dark_mode(self, checked):
        """Toggle dark mode on or off and persist the preference."""
        self._apply_dark_mode(checked)
        self._settings.setValue("dark_mode", "true" if checked else "false")

    def _apply_dark_mode(self, enabled):
        """Apply or remove the dark mode stylesheet."""
        self._dark_mode = enabled
        app = QApplication.instance()
        if enabled:
            app.setStyleSheet(DARK_STYLESHEET)
            self.drop_hint.setStyleSheet(
                "color: #888; font-style: italic; font-size: 8pt;"
            )
        else:
            app.setStyleSheet("")
            self.drop_hint.setStyleSheet(
                "color: #888; font-style: italic; font-size: 8pt;"
            )

    def _html_body_style(self):
        """Return an inline CSS body style string that matches the current theme."""
        if self._dark_mode:
            return (
                'font-family: Segoe UI, Arial, sans-serif; font-size: 9pt; '
                'line-height: 1.45; color: #d4d4d4; background-color: #1e1e1e;'
            )
        return (
            'font-family: Segoe UI, Arial, sans-serif; font-size: 9pt; '
            'line-height: 1.45; color: #222;'
        )

    def _html_heading_color(self):
        """Return an appropriate heading color for the current theme."""
        return "#569cd6" if self._dark_mode else ""

    def _html_muted_color(self):
        """Return a muted/secondary text color for the current theme."""
        return "#808080" if self._dark_mode else "#666"

    def _html_table_border(self):
        """Return table cell bottom-border color for the current theme."""
        return "#3c3c3c" if self._dark_mode else "#ddd"

    def _html_link_color(self):
        """Return link color for the current theme."""
        return "#3794ff" if self._dark_mode else ""

    def _show_help(self):
        """Show the Help dialog."""
        image_exts = ", ".join(sorted(IMAGE_EXTENSIONS))
        video_exts = ", ".join(sorted(VIDEO_EXTENSIONS))
        bs = self._html_body_style()
        hc = self._html_heading_color()
        mc = self._html_muted_color()
        lc = self._html_link_color()
        h_style = f' style="color: {hc};"' if hc else ""
        a_style = f"a {{ color: {lc}; }}" if lc else ""

        help_text = f"""\
<body style="{bs}">
<style>{a_style}</style>

<h2 style="margin-bottom: 2px;{f' color: {hc};' if hc else ''}">EXIF Data Extractor</h2>
<p style="color: {mc}; margin-top: 0;">User Guide</p>

<h3>Overview</h3>
<p>EXIF Data Extractor reads embedded metadata from image and video files, \
including timestamps, GPS coordinates, device identifiers, and more. It \
is designed for investigative, forensic, and analytical workflows where \
understanding the origin and context of media files is important.</p>

<h3>Importing Files</h3>
<p>There are three ways to load media files for analysis:</p>
<ol>
  <li><b>Import Files or Folder button</b> &ndash; Click the button in the \
toolbar, or use <b>File &rarr; Open Folder</b> (<b>Ctrl+O</b>). You will be \
prompted to select a folder. All sub-folders are scanned recursively, so \
you only need to point to the top-level directory.</li>
  <li><b>Drag &amp; Drop a Folder</b> &ndash; Drag any folder from Windows \
Explorer directly onto the application window. It will be scanned the same \
way as the button above.</li>
  <li><b>Drag &amp; Drop Individual Files</b> &ndash; Drag one or more \
image or video files onto the window. Only supported file types will be \
processed; unsupported files are silently skipped.</li>
</ol>

<h3>Thumbnails</h3>
<p>After importing, you will be asked whether to generate thumbnails. \
Thumbnails provide a visual preview in the results table and are included \
in PDF and KMZ exports.</p>
<ul>
  <li><b>Images</b> &ndash; A scaled-down copy of the image is generated \
using Pillow. HEIC/HEIF files are supported via the pillow-heif plugin.</li>
  <li><b>Videos</b> &ndash; A single frame near the beginning of the video \
is extracted using OpenCV.</li>
</ul>
<p>Thumbnail generation is optional. It increases processing time, \
especially for large collections or high-resolution video files. You can \
choose <b>No</b> to skip thumbnails and still extract all metadata.</p>

<h3>Results Table</h3>
<p>Each row represents one file. The columns are:</p>
<table cellpadding="3" cellspacing="0" style="border-collapse: collapse;" \
width="100%">
  <tr><td width="130"><b>Thumbnail</b></td>\
<td>Visual preview of the file (when enabled). Shows "No thumbnail" if \
generation was skipped or failed.</td></tr>
  <tr><td><b>File Name</b></td>\
<td>The name of the file on disk (not the full path).</td></tr>
  <tr><td><b>Timestamp</b></td>\
<td>The date and time the media was originally created, as recorded in the \
file&rsquo;s metadata. For images this comes from EXIF tags \
(DateTimeOriginal, DateTimeDigitized, or DateTime). For videos it comes \
from the container&rsquo;s encoded_date, recorded_date, or tagged_date. \
This is <b>not</b> the filesystem modification date.</td></tr>
  <tr><td><b>Latitude</b></td>\
<td>GPS latitude in decimal degrees. Positive values are North, negative \
values are South.</td></tr>
  <tr><td><b>Longitude</b></td>\
<td>GPS longitude in decimal degrees. Positive values are East, negative \
values are West.</td></tr>
  <tr><td><b>Altitude</b></td>\
<td>GPS altitude in meters above (or below) sea level, if recorded by \
the device.</td></tr>
  <tr><td><b>Make</b></td>\
<td>The manufacturer of the device (e.g. Apple, Samsung, Canon). For \
videos this may come from the container&rsquo;s &ldquo;performer&rdquo; \
or Apple QuickTime make field.</td></tr>
  <tr><td><b>Model</b></td>\
<td>The specific device model (e.g. iPhone 13 Pro Max, Galaxy A54 5G).</td></tr>
  <tr><td><b>Serial Number</b></td>\
<td>The device&rsquo;s serial number, if embedded by the manufacturer. \
Not all devices record this.</td></tr>
  <tr><td><b>Software</b></td>\
<td>The firmware version or application used to create the file \
(e.g. iOS version, Android version, Adobe Lightroom).</td></tr>
</table>

<h3>Viewing All Metadata</h3>
<p>Right-click any row in the table and choose <b>View all EXIF / Metadata</b> \
to open a detailed dialog showing every metadata tag in the file.</p>
<ul>
  <li><b>For images</b> &ndash; Displays all EXIF, GPS, and Apple MakerNote \
tags (exposure settings, lens info, focus data, white balance, orientation, \
SubSecTime, and proprietary vendor fields).</li>
  <li><b>For videos</b> &ndash; Displays the complete MediaInfo output across \
all tracks (General, Video, Audio, Text). This includes codec details, bit \
rates, frame rates, color science, duration, container metadata, and any \
embedded tags like Android version or Apple QuickTime fields.</li>
</ul>
<p>The dialog includes a <b>Copy</b> button to copy all metadata to the \
clipboard for pasting into reports or other applications.</p>

<h3>Map View</h3>
<p>Select one or more rows in the table and click <b>View on Map</b> to open \
the GPS coordinates in Google Maps in your default web browser. If no row is \
selected, the first file with GPS data will be used. The button is only \
enabled when at least one file in the results has GPS coordinates.</p>

<h3>Exporting</h3>
<p>Four export formats are available. All exports include every file in the \
current results.</p>
<table cellpadding="3" cellspacing="0" style="border-collapse: collapse;" \
width="100%">
  <tr><td width="60"><b>CSV</b></td>\
<td>Comma-separated values. Opens directly in Excel, Google Sheets, or any \
spreadsheet application. Contains one row per file with all extracted \
fields. Useful for sorting, filtering, and pivot table analysis.</td></tr>
  <tr><td><b>JSON</b></td>\
<td>Structured data in JSON format. Ideal for programmatic analysis, \
importing into databases, feeding into scripts, or integrating with other \
tools and case management systems.</td></tr>
  <tr><td><b>PDF</b></td>\
<td>A formatted, printable report in landscape layout. Includes thumbnails \
(if generated), all metadata columns, and clickable GPS links that open \
in Google Maps. Suitable for case files and documentation.</td></tr>
  <tr><td><b>KMZ</b></td>\
<td>A Google Earth file containing a placemark for every GPS-tagged file. \
Each placemark includes the file name, timestamp, device info, and \
thumbnail (if generated) in its pop-up balloon. Only available when at \
least one file has GPS coordinates.</td></tr>
</table>

<h3>How Image vs. Video Extraction Works</h3>
<p><b>Images</b> are processed using the exifread and Pillow libraries, \
which parse the EXIF/TIFF metadata block embedded in the file. This \
captures date/time, GPS, device make/model, serial numbers, lens info, \
exposure settings, and Apple MakerNote data.</p>
<p><b>Videos</b> are processed using pymediainfo (a Python wrapper around \
the MediaInfo library). This reads container-level metadata from MP4, MOV, \
AVI, MKV, and other formats. GPS coordinates in videos are typically \
stored as ISO 6709 location strings and are automatically parsed into \
decimal latitude/longitude/altitude.</p>

<h3>Supported File Formats</h3>
<p><b>Images ({len(IMAGE_EXTENSIONS)}):</b> {image_exts}</p>
<p><b>Videos ({len(VIDEO_EXTENSIONS)}):</b> {video_exts}</p>

<h3>Tips</h3>
<ul>
  <li>Not all files contain metadata. Some applications strip EXIF data \
when sharing or uploading. If a file appears with no data, try \
right-clicking and viewing all metadata to confirm.</li>
  <li>GPS coordinates may not be present if the device had location \
services disabled when the file was created.</li>
  <li>The Timestamp column shows the <b>embedded creation date</b>, not \
the filesystem date. If a file was copied or transferred, the filesystem \
date may differ from the original creation date shown here.</li>
  <li>For large folders, skipping thumbnails significantly speeds up \
processing. You can always re-scan with thumbnails enabled later.</li>
</ul>

</body>
"""
        dialog = QDialog(self, Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        dialog.setWindowTitle("Help — EXIF Data Extractor")
        dlg_layout = QVBoxLayout(dialog)
        text_widget = QTextBrowser()
        text_widget.setHtml(help_text)
        dlg_layout.addWidget(text_widget)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        dlg_layout.addLayout(btn_layout)
        dialog.resize(650, 650)
        dialog.exec_()

    def _show_about(self):
        """Show the About dialog."""
        bs = self._html_body_style()
        hc = self._html_heading_color()
        mc = self._html_muted_color()
        lc = self._html_link_color()
        a_style = f"a {{ color: {lc}; }}" if lc else ""

        about_text = f"""\
<body style="{bs}">
<style>{a_style}</style>

<h2 style="margin-bottom: 2px;{f' color: {hc};' if hc else ''}">EXIF Data Extractor</h2>
<p style="color: {mc}; margin-top: 0;">Version 1.1</p>

<p>A desktop application for extracting, viewing, and exporting EXIF and \
metadata from digital image and video files. Designed for investigative, \
forensic, and analytical use cases where understanding the origin, timing, \
and location context of media files is essential.</p>

<h3>What It Does</h3>
<ul>
  <li><b>Extracts key metadata</b> &ndash; Date/time of creation, GPS \
coordinates (latitude, longitude, altitude), device make and model, serial \
numbers, and software/firmware versions.</li>
  <li><b>Supports images and videos</b> &ndash; Reads EXIF data from \
{len(IMAGE_EXTENSIONS)} image formats (JPEG, HEIC, CR2, NEF, DNG, etc.) \
and container metadata from {len(VIDEO_EXTENSIONS)} video formats (MP4, \
MOV, AVI, MKV, MTS, etc.).</li>
  <li><b>Full metadata inspection</b> &ndash; Right-click any file to view \
the complete list of every embedded metadata tag, including exposure \
settings, lens data, color profiles, codec details, and proprietary \
manufacturer fields.</li>
  <li><b>Thumbnail generation</b> &ndash; Creates visual previews for both \
images and videos. Video thumbnails are captured from an early frame.</li>
  <li><b>GPS visualization</b> &ndash; Opens file coordinates directly in \
Google Maps for quick geolocation review.</li>
  <li><b>Multiple export formats</b> &ndash; Export results to CSV \
(spreadsheets), JSON (programmatic use), PDF (formatted reports with \
thumbnails and clickable GPS links), and KMZ (Google Earth placemarks \
with thumbnails and file details).</li>
  <li><b>Drag-and-drop support</b> &ndash; Import folders or individual \
files by dragging them directly onto the application window.</li>
  <li><b>Recursive scanning</b> &ndash; Automatically scans all \
sub-folders within a selected directory.</li>
</ul>

<h3>Technology &amp; Libraries</h3>
<table cellpadding="3" cellspacing="0" style="border-collapse: collapse;">
  <tr><td width="150"><b>GUI Framework</b></td><td>PyQt5</td></tr>
  <tr><td><b>Image EXIF</b></td>\
<td>exifread &ndash; Pure-Python EXIF parser</td></tr>
  <tr><td><b>Image Processing</b></td>\
<td>Pillow (PIL) &ndash; Image loading and thumbnail generation</td></tr>
  <tr><td><b>HEIC/HEIF Support</b></td>\
<td>pillow-heif &ndash; Enables Pillow to decode Apple HEIC files</td></tr>
  <tr><td><b>Video Metadata</b></td>\
<td>pymediainfo &ndash; Python wrapper for \
<a href="https://mediaarea.net/en/MediaInfo">MediaInfo</a></td></tr>
  <tr><td><b>Video Thumbnails</b></td>\
<td>OpenCV (opencv-python-headless) &ndash; Frame extraction</td></tr>
  <tr><td><b>PDF Export</b></td>\
<td>ReportLab &ndash; PDF generation with images and formatted tables</td></tr>
  <tr><td><b>Date Handling</b></td>\
<td>python-dateutil &ndash; Flexible date/time string parsing</td></tr>
</table>

<h3>Use Cases</h3>
<ul>
  <li><b>Digital forensics</b> &ndash; Identify when and where media files \
were created and which device produced them.</li>
  <li><b>Investigations</b> &ndash; Correlate GPS coordinates and timestamps \
across multiple files to establish timelines and locations.</li>
  <li><b>Evidence documentation</b> &ndash; Generate PDF reports or KMZ \
map files for inclusion in case files.</li>
</ul>

<h3>Credits &amp; Acknowledgements</h3>
<p>Video metadata extraction is powered by \
<a href="https://mediaarea.net/en/MediaInfo">MediaInfo</a> \
(&copy; MediaArea.net SARL) via the \
<a href="https://pymediainfo.readthedocs.io/">pymediainfo</a> Python wrapper.</p>
<p>Image EXIF parsing uses \
<a href="https://pypi.org/project/ExifRead/">exifread</a> by ianaré sévi \
and <a href="https://python-pillow.org/">Pillow</a> by the Pillow \
contributors.</p>
<p>HEIC/HEIF support provided by \
<a href="https://github.com/bigcat88/pillow_heif">pillow-heif</a>.</p>
<p>Video frame extraction uses \
<a href="https://opencv.org/">OpenCV</a> (headless build).</p>

<hr>
<p style="color: {mc}; font-size: 8pt;">Built with Python and open-source \
libraries. For questions or issues, contact the developer, Patrick Koebbe \
(patrick.koebbe@gmail.com).</p>

</body>
"""
        dialog = QDialog(self, Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        dialog.setWindowTitle("About — EXIF Data Extractor")
        dlg_layout = QVBoxLayout(dialog)
        text_widget = QTextBrowser()
        text_widget.setOpenExternalLinks(True)
        text_widget.setHtml(about_text)
        dlg_layout.addWidget(text_widget)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        dlg_layout.addLayout(btn_layout)
        dialog.resize(600, 600)
        dialog.exec_()

    def select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.current_folder = folder
            self.folder_label.setText(f"Folder: {os.path.basename(folder)}")
            self.scan_folder(folder)
    
    def dragEnterEvent(self, event):
        """Accept drag events that contain file/folder URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle dropped files and folders."""
        urls = event.mimeData().urls()
        if not urls:
            return

        folders = []
        files = []
        for url in urls:
            path = url.toLocalFile()
            if not path:
                continue
            if os.path.isdir(path):
                folders.append(path)
            elif os.path.isfile(path):
                if Path(path).suffix.lower() in MEDIA_EXTENSIONS:
                    files.append(path)

        if folders:
            folder = folders[0]
            self.current_folder = folder
            self.folder_label.setText(f"Folder: {os.path.basename(folder)}")
            self.scan_folder(folder)
        elif files:
            parent = str(Path(files[0]).parent)
            self.current_folder = parent
            self.folder_label.setText(f"Dropped {len(files)} file(s)")
            self._process_file_list(sorted(files))

    def _process_file_list(self, media_files):
        """Prompt for thumbnails and start extraction on an explicit list of files."""
        if not media_files:
            QMessageBox.information(self, "No Media Files",
                                   "None of the dropped files are supported media types.")
            return

        self.folder_button.setEnabled(False)

        reply = QMessageBox.question(
            self,
            "Generate Thumbnails?",
            f"Found {len(media_files)} file(s).\n\nGenerate thumbnails? (Slower processing, but shows previews in the table and PDF export. Only applies to image files.)",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.No
        )
        if reply == QMessageBox.Cancel:
            self.folder_button.setEnabled(True)
            self.status_bar.showMessage("Cancelled")
            return

        generate_thumbnails = (reply == QMessageBox.Yes)

        self.status_bar.showMessage(f"Processing {len(media_files)} file(s). Extracting metadata...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(media_files))
        self.progress_bar.setValue(0)

        self.worker = ExtractionWorker(media_files, generate_thumbnails=generate_thumbnails)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.extraction_finished)
        self.worker.error.connect(self.extraction_error)
        self.worker.start()

    def scan_folder(self, folder_path):
        """Scan folder for media files and extract metadata."""
        self.status_bar.showMessage("Scanning folder for media files...")
        self.folder_button.setEnabled(False)
        
        media_files = scan_directory(folder_path, recursive=True)

        if not media_files:
            QMessageBox.information(self, "No Media Files Found",
                                   "No media files found in the selected folder.")
            self.folder_button.setEnabled(True)
            self.status_bar.showMessage("No media files found")
            return

        reply = QMessageBox.question(
            self,
            "Generate Thumbnails?",
            f"Found {len(media_files)} file(s).\n\nGenerate thumbnails? (Slower processing, but shows previews in the table and PDF export. Only applies to image files.)",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.No
        )
        if reply == QMessageBox.Cancel:
            self.folder_button.setEnabled(True)
            self.status_bar.showMessage("Cancelled")
            return

        generate_thumbnails = (reply == QMessageBox.Yes)

        self.status_bar.showMessage(f"Found {len(media_files)} file(s). Extracting metadata...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(media_files))
        self.progress_bar.setValue(0)

        self.worker = ExtractionWorker(media_files, generate_thumbnails=generate_thumbnails)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.extraction_finished)
        self.worker.error.connect(self.extraction_error)
        self.worker.start()
    
    def update_progress(self, current, total):
        """Update progress bar."""
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Processing {current} of {total} files...")
    
    def extraction_finished(self, exif_data_list):
        """Handle completion of metadata extraction."""
        self.exif_data_list = exif_data_list
        self.populate_table(exif_data_list)
        self.progress_bar.setVisible(False)
        self.folder_button.setEnabled(True)
        self.export_csv_button.setEnabled(True)
        self.export_json_button.setEnabled(True)
        self.export_pdf_button.setEnabled(True)
        has_gps = any(exif_data.has_gps() for exif_data in exif_data_list)
        self.export_kmz_button.setEnabled(has_gps)
        self.status_bar.showMessage(f"Extracted metadata from {len(exif_data_list)} file(s)")
    
    def extraction_error(self, error_message):
        """Handle extraction errors."""
        QMessageBox.warning(self, "Extraction Error", f"An error occurred: {error_message}")
        self.folder_button.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def populate_table(self, exif_data_list):
        """Populate the results table with EXIF data."""
        self.table.setRowCount(len(exif_data_list))
        
        for row, exif_data in enumerate(exif_data_list):
            # Thumbnail (column 0)
            if exif_data.thumbnail:
                # Convert PIL Image to QPixmap
                try:
                    # Convert PIL Image to bytes
                    img_bytes = io.BytesIO()
                    exif_data.thumbnail.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    
                    # Create QImage from bytes
                    qimage = QImage.fromData(img_bytes.read())
                    pixmap = QPixmap.fromImage(qimage)
                    
                    # Create item with pixmap
                    thumbnail_item = QTableWidgetItem()
                    thumbnail_item.setData(Qt.DecorationRole, pixmap)
                    thumbnail_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 0, thumbnail_item)
                except Exception:
                    # If thumbnail display fails, show placeholder
                    self.table.setItem(row, 0, QTableWidgetItem("No preview"))
            else:
                self.table.setItem(row, 0, QTableWidgetItem("No thumbnail"))
            
            # File Name (column 1)
            self.table.setItem(row, 1, QTableWidgetItem(exif_data.file_name))
            
            # Timestamp (column 2) — EXIF encoded date (DateTimeOriginal, DateTimeDigitized, or DateTime)
            date_str = exif_data.date_taken.strftime("%Y-%m-%d %H:%M:%S") if exif_data.date_taken else ""
            date_item = QTableWidgetItem(date_str)
            date_item.setToolTip("EXIF encoded date: DateTimeOriginal, DateTimeDigitized, or DateTime")
            self.table.setItem(row, 2, date_item)
            
            # Latitude (column 3)
            lat_str = f"{exif_data.latitude:.6f}" if exif_data.latitude is not None else ""
            self.table.setItem(row, 3, QTableWidgetItem(lat_str))
            
            # Longitude (column 4)
            lon_str = f"{exif_data.longitude:.6f}" if exif_data.longitude is not None else ""
            self.table.setItem(row, 4, QTableWidgetItem(lon_str))
            
            # Altitude (column 5)
            alt_str = f"{exif_data.altitude:.2f}" if exif_data.altitude is not None else ""
            self.table.setItem(row, 5, QTableWidgetItem(alt_str))
            
            # Make (column 6)
            self.table.setItem(row, 6, QTableWidgetItem(exif_data.make or ""))
            
            # Model (column 7)
            self.table.setItem(row, 7, QTableWidgetItem(exif_data.model or ""))
            
            # Serial Number (column 8)
            self.table.setItem(row, 8, QTableWidgetItem(exif_data.serial_number or ""))
            
            # Software (column 9)
            self.table.setItem(row, 9, QTableWidgetItem(exif_data.software or ""))
        
        # Enable map button if any row has GPS data
        has_gps = any(exif_data.has_gps() for exif_data in exif_data_list)
        self.map_button.setEnabled(has_gps)
    
    def show_context_menu(self, position):
        """Show context menu for table rows."""
        item = self.table.itemAt(position)
        if item is None:
            return
        row = item.row()
        if row < 0 or row >= len(self.exif_data_list):
            return
        exif_data = self.exif_data_list[row]
        menu = QMenu(self)
        view_exif_action = QAction("View all EXIF / Metadata", self)
        view_exif_action.triggered.connect(
            lambda checked=False, fp=exif_data.file_path, fn=exif_data.file_name: self._show_all_exif_dialog(fp, fn)
        )
        menu.addAction(view_exif_action)
        menu.exec_(self.table.viewport().mapToGlobal(position))

    def _show_all_exif_dialog(self, file_path: str, file_name: str):
        """Show a modal dialog with all EXIF/metadata tags for the given file."""
        try:
            tags = get_all_exif_tags(file_path)
        except Exception:
            tags = []
        if not tags:
            QMessageBox.information(
                self,
                "No EXIF data",
                "No EXIF or metadata could be read from this file. The file may be missing, unsupported, or contain no metadata.",
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"EXIF / Metadata — {file_name}")
        layout = QVBoxLayout(dialog)
        path_label = QLabel(file_path)
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(path_label)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFontFamily("Consolas")
        text.setStyleSheet("font-size: 9pt;")
        lines = [f"{name}: {value}" for name, value in tags]
        text.setPlainText("\n".join(lines))
        layout.addWidget(text)
        plain_content = "\n".join(lines)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(plain_content))
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        dialog.resize(560, 480)
        dialog.exec_()
    
    def view_selected_on_map(self):
        """View GPS location of selected row(s) on map."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            # If no row selected, check if any row has GPS and use first one
            for i, exif_data in enumerate(self.exif_data_list):
                if exif_data.has_gps():
                    open_location_in_map(exif_data.latitude, exif_data.longitude)
                    return
            QMessageBox.information(self, "No GPS Data", 
                                   "No GPS coordinates available in the selected files.")
            return
        
        # View first selected row with GPS data
        for row_index in selected_rows:
            row = row_index.row()
            if row < len(self.exif_data_list):
                exif_data = self.exif_data_list[row]
                if exif_data.has_gps():
                    open_location_in_map(exif_data.latitude, exif_data.longitude)
                    return
        
        QMessageBox.information(self, "No GPS Data", 
                               "The selected file(s) do not have GPS coordinates.")
    
    def export_to_csv(self):
        """Export EXIF data to CSV file."""
        if not self.exif_data_list:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            if export_to_csv(self.exif_data_list, file_path):
                QMessageBox.information(self, "Export Successful", 
                                       f"Data exported to {file_path}")
            else:
                QMessageBox.warning(self, "Export Failed", 
                                   "Failed to export data to CSV.")
    
    def export_to_json(self):
        """Export EXIF data to JSON file."""
        if not self.exif_data_list:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to JSON", "", "JSON Files (*.json)"
        )
        
        if file_path:
            if export_to_json(self.exif_data_list, file_path):
                QMessageBox.information(self, "Export Successful", 
                                       f"Data exported to {file_path}")
            else:
                QMessageBox.warning(self, "Export Failed", 
                                   "Failed to export data to JSON.")
    
    def export_to_pdf(self):
        """Export EXIF data to PDF file."""
        if not self.exif_data_list:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to PDF", "", "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        # Show progress: indeterminate bar + status
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("Exporting to PDF...")
        self.export_csv_button.setEnabled(False)
        self.export_json_button.setEnabled(False)
        self.export_pdf_button.setEnabled(False)
        self.export_kmz_button.setEnabled(False)

        self._pdf_worker = PDFExportWorker(self.exif_data_list, file_path)
        self._pdf_worker.finished.connect(self._on_pdf_export_finished)
        self._pdf_worker.start()

    def _on_pdf_export_finished(self, success):
        """Handle PDF export worker completion."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.export_csv_button.setEnabled(True)
        self.export_json_button.setEnabled(True)
        self.export_pdf_button.setEnabled(True)
        has_gps = any(exif_data.has_gps() for exif_data in self.exif_data_list)
        self.export_kmz_button.setEnabled(has_gps)

        if success:
            self.status_bar.showMessage("PDF export completed successfully.")
            QMessageBox.information(self, "Export Successful",
                                    f"Data exported to {self._pdf_worker.file_path}")
        else:
            self.status_bar.showMessage("PDF export failed.")
            QMessageBox.warning(self, "Export Failed",
                                "Failed to export data to PDF. Make sure reportlab is installed.")

    def export_to_kmz_handler(self):
        """Export location data to a KMZ file for Google Earth."""
        if not self.exif_data_list:
            return
        if not any(exif_data.has_gps() for exif_data in self.exif_data_list):
            QMessageBox.information(
                self,
                "No GPS Data",
                "No files with GPS coordinates to export. Export to KMZ is only available when at least one file has location data.",
            )
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to KMZ", "", "KMZ Files (*.kmz)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith('.kmz'):
            file_path = file_path + '.kmz'
        if export_to_kmz(self.exif_data_list, file_path):
            QMessageBox.information(self, "Export Successful", f"Location data exported to {file_path}")
            self.status_bar.showMessage("KMZ export completed.")
        else:
            QMessageBox.warning(self, "Export Failed", "Failed to export to KMZ.")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

