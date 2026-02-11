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
    QMenu, QAction, QDialog, QTextEdit, QDialogButtonBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QImage

from file_scanner import scan_directory
from exif_extractor import extract_exif_data, get_all_exif_tags
from data_model import ExifData
from export_utils import export_to_csv, export_to_json, export_to_pdf, export_to_kmz
from map_utils import open_location_in_map
from thumbnail_utils import create_thumbnail


class ExtractionWorker(QThread):
    """Worker thread for extracting EXIF data from images."""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)  # list of ExifData
    error = pyqtSignal(str)  # error message
    
    def __init__(self, image_files, generate_thumbnails=False):
        super().__init__()
        self.image_files = image_files
        self.generate_thumbnails = generate_thumbnails
    
    def run(self):
        """Extract EXIF data from all image files."""
        import warnings
        import sys
        from io import StringIO
        from contextlib import redirect_stderr
        
        exif_data_list = []
        total = len(self.image_files)
        
        for i, file_path in enumerate(self.image_files):
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


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.exif_data_list = []
        self.current_folder = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("EXIF Data Extractor")
        self.setGeometry(100, 100, 2700, 1575)  # 50% larger than 1800x1050
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.clicked.connect(self.select_folder)
        controls_layout.addWidget(self.folder_button)
        
        self.folder_label = QLabel("No folder selected")
        controls_layout.addWidget(self.folder_label)
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
        self.table.setColumnWidth(2, 180)  # Timestamp
        self.table.setColumnWidth(3, 180)  # Latitude
        self.table.setColumnWidth(4, 200)  # Longitude
        self.table.setColumnWidth(5, 120)  # Altitude
        self.table.setColumnWidth(6, 144)  # Make
        self.table.setColumnWidth(7, 180)  # Model
        self.table.setColumnWidth(8, 220)  # Serial Number
        self.table.setColumnWidth(9, 180)  # Software
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
    
    def select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.current_folder = folder
            self.folder_label.setText(f"Folder: {os.path.basename(folder)}")
            self.scan_folder(folder)
    
    def scan_folder(self, folder_path):
        """Scan folder for images and extract metadata."""
        self.status_bar.showMessage("Scanning folder for images...")
        self.folder_button.setEnabled(False)
        
        image_files = scan_directory(folder_path, recursive=True)

        if not image_files:
            QMessageBox.information(self, "No Images Found",
                                   "No image files found in the selected folder.")
            self.folder_button.setEnabled(True)
            self.status_bar.showMessage("No images found")
            return

        reply = QMessageBox.question(
            self,
            "Generate Thumbnails?",
            f"Found {len(image_files)} image(s).\n\nGenerate thumbnails? (Slower processing, but shows previews in the table and PDF export.)",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.No
        )
        if reply == QMessageBox.Cancel:
            self.folder_button.setEnabled(True)
            self.status_bar.showMessage("Cancelled")
            return

        generate_thumbnails = (reply == QMessageBox.Yes)

        self.status_bar.showMessage(f"Found {len(image_files)} image(s). Extracting metadata...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(image_files))
        self.progress_bar.setValue(0)

        self.worker = ExtractionWorker(image_files, generate_thumbnails=generate_thumbnails)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.extraction_finished)
        self.worker.error.connect(self.extraction_error)
        self.worker.start()
    
    def update_progress(self, current, total):
        """Update progress bar."""
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Processing {current} of {total} images...")
    
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
        self.status_bar.showMessage(f"Extracted metadata from {len(exif_data_list)} image(s)")
    
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
        view_exif_action = QAction("View all EXIF", self)
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
                                   "No GPS coordinates available in the selected images.")
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
                               "Selected image(s) do not have GPS coordinates.")
    
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
                "No images with GPS coordinates to export. Export to KMZ is only available when at least one image has location data.",
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

