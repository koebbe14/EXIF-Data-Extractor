# EXIF Data Extractor

An application that extracts and displays EXIF metadata from image files. It focuses on **when and where** photos were taken and **device identifiers**, and ignores exposure settings and technical image metadata.

This application will identify image files within folders and automatically extract relevant exif/metadata info for use in determinng location, time/date, and device information.

## Features

- **Folder scanning** — Recursively scan a folder for image files (JPEG, PNG, TIFF, HEIC, RAW, and more)
- **Metadata extraction** — Only date/time, GPS, and device info:
  - **Timestamp** (EXIF encoded date: DateTimeOriginal, DateTimeDigitized, or DateTime)
  - **GPS** — Latitude, longitude, altitude
  - **Device** — Make, model, serial number, software
- **Optional thumbnails** — Generate previews during import; show in table and in PDF/KMZ exports
- **View on map** — Open GPS locations in your browser (Google Maps or OpenStreetMap)
- **Export to KMZ** — Export locations to a KMZ file for Google Earth (placemarks with thumbnails and metadata)
- **Export to CSV, JSON, PDF** — PDF is landscape with all columns and optional thumbnails; GPS in PDF is clickable (opens map in browser)
- **View all EXIF** — Right‑click a row → “View all EXIF” to see every metadata tag in a popup
- **Adjustable columns** — Resize column widths in the table
- **Progress feedback** — Status bar and progress bar during scan and PDF export




## Installation

1. Download the .exe from the "releases" page

## Usage


1. Click **Select Folder** and choose a folder of images.
2. When prompted, choose whether to **generate thumbnails** (slower, but enables previews in the table and in PDF/KMZ).
3. Wait for the scan; results appear in the table.

### Main actions

| Action | How |
|--------|-----|
| **View on map** | Ensure at least one image has GPS; click **View on Map** (uses selected row or first with GPS). |
| **View all EXIF** | Right‑click any cell in a row → **View all EXIF** to see full metadata in a popup. |
| **Export CSV/JSON** | Click **Export to CSV** or **Export to JSON**; choose save path. |
| **Export PDF** | Click **Export to PDF**; choose path. Progress bar runs in background. PDF is landscape; GPS values are clickable links. |
| **Export KMZ** | Click **Export to KMZ** (enabled when any image has GPS). Open the `.kmz` in Google Earth to see placemarks with thumbnails and metadata. |
| **Resize columns** | Drag column borders in the table header. |

## Supported image formats

- JPEG, PNG, TIFF, HEIC/HEIF, BMP, GIF, WebP  
- RAW: CR2, NEF, ARW, DNG, ORF, RAF, RW2, PEF, SRW, X3F  

## Data extracted (and excluded)

**Included:** File name, timestamp (EXIF encoded date only), latitude, longitude, altitude, make, model, serial number, software.

**Excluded:** Exposure (ISO, aperture, shutter, focal length, etc.), orientation, dimensions, compression, resolution, and other technical metadata.


## Troubleshooting

- **No images found** — Check that the folder contains supported image extensions and the path is correct.
- **No metadata** — Many images have no or stripped EXIF; timestamp and device fields may be empty.
- **View on Map / Export KMZ disabled** — At least one loaded image must have GPS coordinates.
- **PDF/export fails** — Ensure reportlab is installed for PDF; check write permissions and disk space.

## License

Permission is hereby granted to law-enforcement agencies, digital-forensic analysts, and authorized investigative personnel ("Authorized Users") to use and copy this software for the purpose of criminal investigations, evidence review, training, or internal operational use.

The following conditions apply:

Redistribution: This software may not be sold, published, or redistributed to the general public. Redistribution outside an authorized agency requires written permission from the developer.

No Warranty: This software is provided "AS IS," without warranty of any kind, express or implied, including but not limited to the warranties of accuracy, completeness, performance, non-infringement, or fitness for a particular purpose. The developer shall not be liable for any claim, damages, or other liability arising from the use of this software, including the handling of digital evidence.

Evidence Integrity: Users are responsible for maintaining forensic integrity and chain of custody when handling evidence. This software does not alter source evidence files and is intended only for analysis and review.

Modifications: Agencies and investigators may modify the software for internal purposes. Modified versions may not be publicly distributed without permission from the developer.

Privacy: Users are responsible for controlling files and output generated during use of the software to prevent unauthorized disclosure of sensitive or personally identifiable information.

Compliance: Users agree to comply with all applicable laws, departmental policies, and legal requirements when using the software.

By using this software, the user acknowledges that they have read, understood, and agreed to the above terms.
