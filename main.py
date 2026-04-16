"""
Main application window for EXIF Data Extractor GUI.
"""

import sys
import os
from datetime import datetime

# Suppress Qt ICC profile warnings when loading thumbnails (unsupported profile class)
os.environ["QT_LOGGING_RULES"] = "qt.gui.icc=false"

import io
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog,
    QProgressBar, QStatusBar, QMessageBox, QHeaderView, QLabel,
    QMenu, QAction, QDialog, QTextEdit, QTextBrowser, QDialogButtonBox,
    QTableView,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPalette, QColor

from file_scanner import scan_directory, MEDIA_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from exif_extractor import extract_exif_data, get_all_exif_tags
from data_model import ExifData
from export_utils import export_to_csv, export_to_json, export_to_pdf, export_to_kmz
from map_utils import open_location_in_map
from thumbnail_utils import create_thumbnail
from exif_table_model import ExifTableModel
from exif_filter_proxy import ExifFilterProxy, ExifProxyFilters
from import_mode_dialog import choose_import_mode
from search_dialog import SearchDialog, SearchSettings
from filter_dialog import FilterDialog, FilterSettings


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
QTableWidget, QTableView {
    background-color: #1e1e1e;
    alternate-background-color: #262626;
    color: #d4d4d4;
    gridline-color: #3c3c3c;
    border: 1px solid #3c3c3c;
    selection-background-color: #094771;
    selection-color: #ffffff;
}
QTableWidget::item, QTableView::item {
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
QGroupBox {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 8px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    color: #d4d4d4;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #d4d4d4;
}
QLineEdit {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    padding: 4px 6px;
}
QLineEdit:focus {
    border-color: #0e639c;
}
QComboBox {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    padding: 3px 6px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #d4d4d4;
    selection-background-color: #094771;
    selection-color: #ffffff;
}
QDateEdit {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    padding: 3px 6px;
}
QCheckBox {
    color: #d4d4d4;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
}
QListWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
}
QListWidget::item {
    padding: 2px 4px;
}
QListWidget::item:hover {
    background-color: #2a2d2e;
}
QRadioButton {
    color: #d4d4d4;
    spacing: 6px;
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

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.open_search_dialog)
        controls_layout.addWidget(self.search_button)

        self.filter_button = QPushButton("Filter")
        self.filter_button.clicked.connect(self.open_filter_dialog)
        controls_layout.addWidget(self.filter_button)

        self.clear_search_filter_button = QPushButton("Clear Search/Filters")
        self.clear_search_filter_button.setEnabled(False)
        self.clear_search_filter_button.clicked.connect(self.clear_search_and_filters)
        controls_layout.addWidget(self.clear_search_filter_button)
        
        layout.addLayout(controls_layout)
        # Result count (small, unobtrusive)
        self.result_count_label = QLabel("")
        self.result_count_label.setStyleSheet("color: #888; font-size: 8pt;")
        layout.addWidget(self.result_count_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results table
        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        self.source_model = ExifTableModel([])
        self.proxy_model = ExifFilterProxy(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.table.setModel(self.proxy_model)

        self._filters = ExifProxyFilters()

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 192)
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(2, 138)
        self.table.setColumnWidth(3, 138)
        self.table.setColumnWidth(4, 153)
        self.table.setColumnWidth(5, 92)
        self.table.setColumnWidth(6, 110)
        self.table.setColumnWidth(7, 180)
        self.table.setColumnWidth(8, 168)
        self.table.setColumnWidth(9, 138)
        self.table.verticalHeader().setDefaultSectionSize(192)

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

<h3>Search</h3>
<p>Click the <b>Search</b> button in the toolbar to open the Search dialog. \
You can search across filenames, file paths, device make/model, serial \
numbers, software, GPS coordinates, timestamps, and any other extracted \
metadata.</p>
<ul>
  <li><b>Partial match</b> (default) &ndash; Case-insensitive substring \
search. Typing <code>iphone</code> matches &ldquo;iPhone 13 Pro Max&rdquo;.</li>
  <li><b>Exact match</b> &ndash; Uncheck &ldquo;Partial match&rdquo; to \
require that every keyword you type appears as a complete token in the \
row&rsquo;s metadata.</li>
  <li><b>GPS search</b> &ndash; Enter a single number like \
<code>34.0522</code> to match any latitude or longitude, or a pair like \
<code>34.0522,-118.2437</code> to match both.</li>
  <li><b>Include full metadata</b> &ndash; When checked, the search also \
looks through every EXIF/MediaInfo tag (not just the columns shown in the \
table). This is more thorough but slower on large collections.</li>
</ul>
<p>Click <b>Clear</b> in the Search dialog or <b>Clear Search/Filters</b> \
in the toolbar to reset the search and show all results again.</p>

<h3>Filter</h3>
<p>Click the <b>Filter</b> button to open the Filter dialog. Filters \
let you narrow results by specific criteria. All active filters are \
combined (AND logic), so each additional filter further restricts the \
visible results.</p>
<ul>
  <li><b>File type</b> &ndash; Show All files, Images only, or Videos only.</li>
  <li><b>GPS</b> &ndash; Show all files, only files that have GPS \
coordinates, or only files missing GPS.</li>
  <li><b>Serial number</b> &ndash; Show all files, only files with a serial \
number present, or only files missing a serial number.</li>
  <li><b>Date range</b> &ndash; Enable a From and/or To date to restrict \
results to files whose embedded timestamp falls within that range.</li>
  <li><b>Extensions / Make / Model / Software</b> &ndash; Multi-select lists \
populated from your loaded results. Check one or more items to show only \
matching files. If nothing is checked, no restriction is applied for that \
category.</li>
</ul>
<p>Click <b>Clear</b> in the Filter dialog or <b>Clear Search/Filters</b> \
in the toolbar to reset all filters and show all results again.</p>

<h3>Sorting</h3>
<p>Click any column header in the results table to sort by that column. \
Click again to reverse the sort order. Numeric columns (latitude, longitude, \
altitude) and date columns sort correctly by value, not alphabetically.</p>

<h3>Importing Additional Files</h3>
<p>When you import new files or folders and results are already loaded, \
you will be prompted to choose:</p>
<ul>
  <li><b>Replace</b> &ndash; Clear the existing results and load only the \
new files.</li>
  <li><b>Append</b> &ndash; Add the new files to the existing results. \
Duplicate files (same path) are automatically skipped.</li>
</ul>

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
<p style="color: {mc}; margin-top: 0;">Version 2.0</p>

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

        if not self._begin_import_flow(media_files):
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

        if not self._begin_import_flow(media_files):
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
        merged = self._merge_import_results(exif_data_list)
        self.exif_data_list = merged
        self._set_results(merged)
        self.progress_bar.setVisible(False)
        self.folder_button.setEnabled(True)
        self.export_csv_button.setEnabled(True)
        self.export_json_button.setEnabled(True)
        self.export_pdf_button.setEnabled(True)
        has_gps = any(exif_data.has_gps() for exif_data in merged)
        self.export_kmz_button.setEnabled(has_gps)
        self.status_bar.showMessage(f"Extracted metadata from {len(exif_data_list)} file(s)")
        self._update_result_count()
    
    def extraction_error(self, error_message):
        """Handle extraction errors."""
        QMessageBox.warning(self, "Extraction Error", f"An error occurred: {error_message}")
        self.folder_button.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def _set_results(self, exif_data_list):
        """Set results on the source model and refresh filter options."""
        for exif_data in exif_data_list:
            self._ensure_thumbnail_pixmap(exif_data)
        self.source_model.set_rows(exif_data_list)
        self._refresh_filter_options(exif_data_list)
        self._apply_filters()
    
    def show_context_menu(self, position):
        """Show context menu for table rows."""
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        source_index = self.proxy_model.mapToSource(index)
        exif_data = self.source_model.get_row(source_index.row())
        if exif_data is None:
            return
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
            for r in range(self.proxy_model.rowCount()):
                src = self.proxy_model.mapToSource(self.proxy_model.index(r, 0))
                exif_data = self.source_model.get_row(src.row())
                if exif_data and exif_data.has_gps():
                    open_location_in_map(exif_data.latitude, exif_data.longitude)
                    return
            QMessageBox.information(self, "No GPS Data", 
                                   "No GPS coordinates available in the selected files.")
            return
        
        # View first selected row with GPS data
        for row_index in selected_rows:
            src = self.proxy_model.mapToSource(row_index)
            exif_data = self.source_model.get_row(src.row())
            if exif_data and exif_data.has_gps():
                open_location_in_map(exif_data.latitude, exif_data.longitude)
                return
        
        QMessageBox.information(self, "No GPS Data", 
                               "The selected file(s) do not have GPS coordinates.")
    
    def export_to_csv(self):
        """Export EXIF data to CSV file."""
        export_rows = self._current_view_rows()
        if not export_rows:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            if export_to_csv(export_rows, file_path):
                QMessageBox.information(self, "Export Successful", 
                                       f"Data exported to {file_path}")
            else:
                QMessageBox.warning(self, "Export Failed", 
                                   "Failed to export data to CSV.")
    
    def export_to_json(self):
        """Export EXIF data to JSON file."""
        export_rows = self._current_view_rows()
        if not export_rows:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to JSON", "", "JSON Files (*.json)"
        )
        
        if file_path:
            if export_to_json(export_rows, file_path):
                QMessageBox.information(self, "Export Successful", 
                                       f"Data exported to {file_path}")
            else:
                QMessageBox.warning(self, "Export Failed", 
                                   "Failed to export data to JSON.")
    
    def export_to_pdf(self):
        """Export EXIF data to PDF file."""
        export_rows = self._current_view_rows()
        if not export_rows:
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

        self._pdf_worker = PDFExportWorker(export_rows, file_path)
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
        export_rows = self._current_view_rows()
        if not export_rows:
            return
        if not any(exif_data.has_gps() for exif_data in export_rows):
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
        if export_to_kmz(export_rows, file_path):
            QMessageBox.information(self, "Export Successful", f"Location data exported to {file_path}")
            self.status_bar.showMessage("KMZ export completed.")
        else:
            QMessageBox.warning(self, "Export Failed", "Failed to export to KMZ.")

    def _ensure_thumbnail_pixmap(self, exif_data: ExifData) -> None:
        if getattr(exif_data, "thumbnail_qpixmap", None) is not None:
            return
        if not exif_data.thumbnail:
            return
        try:
            img_bytes = io.BytesIO()
            exif_data.thumbnail.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            qimage = QImage.fromData(img_bytes.read())
            pixmap = QPixmap.fromImage(qimage)
            setattr(exif_data, "thumbnail_qpixmap", pixmap)
        except Exception:
            pass

    def _current_view_rows(self):
        rows = []
        for r in range(self.proxy_model.rowCount()):
            src = self.proxy_model.mapToSource(self.proxy_model.index(r, 0))
            exif = self.source_model.get_row(src.row())
            if exif is not None:
                rows.append(exif)
        return rows

    def _update_result_count(self):
        shown = self.proxy_model.rowCount()
        total = self.source_model.rowCount()
        self.result_count_label.setText(f"{shown} / {total} shown" if total else "")
        self.map_button.setEnabled(any(r.has_gps() for r in self._current_view_rows()))
        self.clear_search_filter_button.setEnabled(self._has_active_search_or_filters())

    def _refresh_filter_options(self, rows):
        self._filter_options = {
            "extensions": sorted({(r.extension or "").lower() for r in rows if (r.extension or "").strip()}),
            "makes": sorted({(r.make or "").strip() for r in rows if (r.make or "").strip()}),
            "models": sorted({(r.model or "").strip() for r in rows if (r.model or "").strip()}),
            "softwares": sorted({(r.software or "").strip() for r in rows if (r.software or "").strip()}),
        }

    def _apply_filters(self):
        self.proxy_model.set_filters(self._filters)
        self._update_result_count()

    def _has_active_search_or_filters(self) -> bool:
        f = self._filters
        if (f.query or "").strip():
            return True
        if f.include_full_metadata is True or f.partial_match is False:
            return True
        if f.file_type != "All" or f.gps != "Any" or f.serial_presence != "Any":
            return True
        if f.date_from is not None or f.date_to is not None:
            return True
        if f.extensions or f.makes or f.models or f.softwares:
            return True
        return False

    def open_search_dialog(self):
        initial = SearchSettings(
            query=self._filters.query,
            partial_match=self._filters.partial_match,
            include_full_metadata=self._filters.include_full_metadata,
        )
        dlg = SearchDialog(self, initial=initial)
        if dlg.exec_() != QDialog.Accepted:
            return
        res = dlg.result()
        if res is None:
            return
        self._filters.query = res.query
        self._filters.partial_match = res.partial_match
        self._filters.include_full_metadata = res.include_full_metadata
        self._apply_filters()

    def open_filter_dialog(self):
        options = getattr(self, "_filter_options", {"extensions": [], "makes": [], "models": [], "softwares": []})
        initial = FilterSettings(
            file_type=self._filters.file_type,
            gps=self._filters.gps,
            serial_presence=self._filters.serial_presence,
            date_from=self._filters.date_from,
            date_to=self._filters.date_to,
            extensions=set(self._filters.extensions),
            makes=set(self._filters.makes),
            models=set(self._filters.models),
            softwares=set(self._filters.softwares),
        )
        dlg = FilterDialog(self, initial=initial, options=options)
        if dlg.exec_() != QDialog.Accepted:
            return
        res = dlg.result()
        if res is None:
            return
        self._filters.file_type = res.file_type
        self._filters.gps = res.gps
        self._filters.serial_presence = res.serial_presence
        self._filters.date_from = res.date_from
        self._filters.date_to = res.date_to
        self._filters.extensions = set(res.extensions)
        self._filters.makes = set(res.makes)
        self._filters.models = set(res.models)
        self._filters.softwares = set(res.softwares)
        self._apply_filters()

    def clear_search_and_filters(self):
        self._filters = ExifProxyFilters()
        self._apply_filters()

    def _begin_import_flow(self, media_files) -> bool:
        if not media_files:
            return False

        self._import_mode = "replace"
        self.folder_button.setEnabled(False)

        if self.source_model.rowCount() > 0:
            choice = choose_import_mode(self, default_mode="replace")
            if choice.mode == "cancel":
                self.folder_button.setEnabled(True)
                self.status_bar.showMessage("Cancelled")
                return False
            self._import_mode = choice.mode

        return True

    def _merge_import_results(self, new_rows):
        mode = getattr(self, "_import_mode", "replace")
        if mode == "append":
            existing = self.source_model.rows()
            seen = {os.path.normcase(os.path.abspath(r.file_path)) for r in existing if r.file_path}
            to_add = []
            for r in new_rows:
                key = os.path.normcase(os.path.abspath(r.file_path)) if r.file_path else ""
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                to_add.append(r)
            return existing + to_add
        return list(new_rows)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

