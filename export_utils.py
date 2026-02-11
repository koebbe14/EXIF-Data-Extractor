"""
Export utilities for saving EXIF data to CSV, JSON, PDF, and KMZ formats.
"""

import csv
import html
import io
import json
import zipfile
from typing import List
from data_model import ExifData
from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    import io
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def export_to_csv(exif_data_list: List[ExifData], output_path: str) -> bool:
    """
    Export EXIF data to CSV file.
    
    Args:
        exif_data_list: List of ExifData objects
        output_path: Path to save the CSV file
    
    Returns:
        True if successful, False otherwise
    """
    if not exif_data_list:
        return False
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'file_name', 'file_path', 'date_taken', 'latitude', 'longitude',
                'altitude', 'make', 'model', 'serial_number', 'software'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for exif_data in exif_data_list:
                row = exif_data.to_dict()
                writer.writerow(row)
        
        return True
    except Exception:
        return False


def export_to_json(exif_data_list: List[ExifData], output_path: str) -> bool:
    """
    Export EXIF data to JSON file.
    
    Args:
        exif_data_list: List of ExifData objects
        output_path: Path to save the JSON file
    
    Returns:
        True if successful, False otherwise
    """
    if not exif_data_list:
        return False
    
    try:
        data = [exif_data.to_dict() for exif_data in exif_data_list]
        
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        
        return True
    except Exception:
        return False


def export_to_pdf(exif_data_list: List[ExifData], output_path: str) -> bool:
    """
    Export EXIF data to PDF file.
    
    Args:
        exif_data_list: List of ExifData objects
        output_path: Path to save the PDF file
    
    Returns:
        True if successful, False otherwise
    """
    if not exif_data_list:
        return False
    
    if not REPORTLAB_AVAILABLE:
        return False
    
    try:
        # Explicit landscape: 11" wide x 8.5" tall (width, height in points)
        landscape_letter = (11 * inch, 8.5 * inch)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape_letter,
            leftMargin=0.4 * inch,
            rightMargin=0.4 * inch,
            topMargin=0.4 * inch,
            bottomMargin=0.4 * inch,
        )
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=1,
        )
        # Style for table cells so long text wraps instead of being cut off
        cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontSize=7,
            leading=8,
            wordWrap='CJK',  # enables word wrap
        )
        header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
        )

        title = Paragraph("EXIF Data Extract", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2 * inch))

        gen_date = Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal'],
        )
        elements.append(gen_date)
        elements.append(Spacer(1, 0.25 * inch))

        has_thumbnails = any(exif_data.thumbnail for exif_data in exif_data_list)
        table_data = []

        def cell_text(s):
            return Paragraph(html.escape(str(s) if s else ''), cell_style)

        def gps_link(lat, lon, label):
            """Return a clickable Paragraph linking to Google Maps, or plain text if no GPS."""
            if lat is not None and lon is not None:
                map_url = f"https://www.google.com/maps?q={lat},{lon}"
                url_escaped = html.escape(map_url)
                text_escaped = html.escape(str(label))
                return Paragraph(f'<a href="{url_escaped}" color="blue">{text_escaped}</a>', cell_style)
            return cell_text('')

        if has_thumbnails:
            headers = [
                Paragraph('Thumbnail', header_style),
                Paragraph('File Name', header_style),
                Paragraph('Timestamp (EXIF encoded date)', header_style),
                Paragraph('Latitude', header_style),
                Paragraph('Longitude', header_style),
                Paragraph('Altitude', header_style),
                Paragraph('Make', header_style),
                Paragraph('Model', header_style),
                Paragraph('Serial Number', header_style),
                Paragraph('Software', header_style),
            ]
        else:
            headers = [
                Paragraph('File Name', header_style),
                Paragraph('Timestamp (EXIF encoded date)', header_style),
                Paragraph('Latitude', header_style),
                Paragraph('Longitude', header_style),
                Paragraph('Altitude', header_style),
                Paragraph('Make', header_style),
                Paragraph('Model', header_style),
                Paragraph('Serial Number', header_style),
                Paragraph('Software', header_style),
            ]
        table_data.append(headers)

        for exif_data in exif_data_list:
            row = []

            if has_thumbnails:
                if exif_data.thumbnail:
                    try:
                        img_bytes = io.BytesIO()
                        exif_data.thumbnail.save(img_bytes, format='PNG')
                        img_bytes.seek(0)
                        # Slightly smaller than column width so image doesn't overlap next column (cell has padding)
                        rl_image = RLImage(img_bytes, width=0.82 * inch, height=0.82 * inch)
                        row.append(rl_image)
                    except Exception:
                        row.append(cell_text('No preview'))
                else:
                    row.append(cell_text('No thumbnail'))

            date_str = exif_data.date_taken.strftime('%Y-%m-%d %H:%M:%S') if exif_data.date_taken else ''
            lat_str = f"{exif_data.latitude:.6f}" if exif_data.latitude is not None else ''
            lon_str = f"{exif_data.longitude:.6f}" if exif_data.longitude is not None else ''
            has_gps = exif_data.latitude is not None and exif_data.longitude is not None
            row.extend([
                cell_text(exif_data.file_name or ''),
                cell_text(date_str),
                gps_link(exif_data.latitude, exif_data.longitude, lat_str) if has_gps else cell_text(lat_str),
                gps_link(exif_data.latitude, exif_data.longitude, lon_str) if has_gps else cell_text(lon_str),
                cell_text(f"{exif_data.altitude:.2f}" if exif_data.altitude is not None else ''),
                cell_text(exif_data.make or ''),
                cell_text(exif_data.model or ''),
                cell_text(exif_data.serial_number or ''),
                cell_text(exif_data.software or ''),
            ])
            table_data.append(row)

        # Column widths to fit landscape ~10.2" usable; all headers and content visible
        if has_thumbnails:
            col_widths = [
                1.0 * inch,   # Thumbnail
                1.35 * inch,  # File Name
                1.0 * inch,   # Timestamp
                0.7 * inch,   # Latitude
                0.7 * inch,   # Longitude
                0.5 * inch,   # Altitude
                0.65 * inch,  # Make
                1.0 * inch,   # Model
                1.0 * inch,   # Serial Number
                1.15 * inch,  # Software
            ]
        else:
            col_widths = [
                1.5 * inch, 1.1 * inch, 0.8 * inch, 0.8 * inch, 0.6 * inch,
                0.8 * inch, 1.0 * inch, 1.0 * inch, 1.1 * inch,
            ]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Style the table
        table_style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Data row styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ])
        
        table.setStyle(table_style)
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        return True

    except Exception:
        return False


def export_to_kmz(exif_data_list: List[ExifData], output_path: str) -> bool:
    """
    Export location data to a KMZ file for use in Google Earth.
    Only includes entries with GPS coordinates. Each placemark includes file name,
    description (timestamp, make, model, serial, software), and optional thumbnail.
    Full file path and Google Earth's "Directions" links are omitted.
    """
    gps_items = [e for e in exif_data_list if e.has_gps()]
    if not gps_items:
        return False

    try:
        # Build KML document. Style with BalloonStyle/text prevents Google Earth from adding "Directions: To here / From here".
        kml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<kml xmlns="http://www.opengis.net/kml/2.2">',
            '  <Document>',
            '    <name>EXIF Location Export</name>',
            '    <Style id="noDirections">',
            '      <BalloonStyle>',
            '        <text>$[description]</text>',
            '      </BalloonStyle>',
            '    </Style>',
        ]
        for i, exif in enumerate(gps_items):
            name = html.escape(exif.file_name)
            lon = exif.longitude
            lat = exif.latitude
            alt = exif.altitude if exif.altitude is not None else 0
            desc_parts = [
                f"<p><b>File name:</b> {html.escape(exif.file_name)}</p>",
            ]
            if exif.date_taken:
                desc_parts.append(f"<p><b>Timestamp:</b> {html.escape(exif.date_taken.strftime('%Y-%m-%d %H:%M:%S'))}</p>")
            if exif.make or exif.model:
                desc_parts.append(f"<p><b>Make:</b> {html.escape(exif.make or '')} &nbsp; <b>Model:</b> {html.escape(exif.model or '')}</p>")
            if exif.serial_number:
                desc_parts.append(f"<p><b>Serial number:</b> {html.escape(exif.serial_number)}</p>")
            if exif.software:
                desc_parts.append(f"<p><b>Software:</b> {html.escape(exif.software)}</p>")
            if exif.thumbnail:
                thumb_ref = f"files/thumb_{i}.png"
                desc_parts.insert(0, f'<p><img src="{thumb_ref}" width="150" alt="Thumbnail"/></p>')
            description = "".join(desc_parts).replace(']]>', ']]]]><![CDATA[>')
            kml_lines.append('    <Placemark>')
            kml_lines.append('      <styleUrl>#noDirections</styleUrl>')
            kml_lines.append(f'      <name>{name}</name>')
            kml_lines.append('      <description><![CDATA[<html><body>' + description + '</body></html>]]></description>')
            kml_lines.append('      <Point>')
            kml_lines.append(f'        <coordinates>{lon},{lat},{alt}</coordinates>')
            kml_lines.append('      </Point>')
            kml_lines.append('    </Placemark>')
        kml_lines.append('  </Document>')
        kml_lines.append('</kml>')
        kml_content = "\n".join(kml_lines)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("doc.kml", kml_content.encode('utf-8'))
            for i, exif in enumerate(gps_items):
                if exif.thumbnail:
                    buf = io.BytesIO()
                    try:
                        exif.thumbnail.save(buf, format='PNG')
                        buf.seek(0)
                        zf.writestr(f"files/thumb_{i}.png", buf.read())
                    except Exception:
                        pass

        return True
    except Exception:
        return False

