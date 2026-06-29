"""
A4 Tag Generator Module
Handles label calculations and PDF generation for A4 sheets
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from io import BytesIO
from typing import List, Dict, Any, Tuple
import math
from config import Config
import logging

logger = logging.getLogger(__name__)

class TagLayoutCalculator:
    """Calculate tag layout for A4 sheets"""
    
    def __init__(self, settings: Dict[str, float]):
        """
        Initialize calculator with user settings
        
        Args:
            settings: Dictionary containing label dimensions and margins
        """
        self.settings = settings
        self.a4_width = Config.A4_WIDTH  # 21.0 cm
        self.a4_height = Config.A4_HEIGHT  # 29.7 cm
        
    def calculate_layout(self) -> Dict[str, Any]:
        """
        Calculate label positions and counts
        
        Returns:
            Dictionary with layout calculations
        """
        # Extract settings
        label_width = self.settings.get('label_width', 8.5)
        label_height = self.settings.get('label_height', 5.5)
        top_margin = self.settings.get('top_margin', 1.5)
        bottom_margin = self.settings.get('bottom_margin', 1.5)
        left_margin = self.settings.get('left_margin', 1.0)
        right_margin = self.settings.get('right_margin', 1.0)
        horizontal_gap = self.settings.get('horizontal_gap', 0.3)
        vertical_gap = self.settings.get('vertical_gap', 0.3)
        
        # Calculate available space
        available_width = self.a4_width - left_margin - right_margin
        available_height = self.a4_height - top_margin - bottom_margin
        
        # Calculate labels per row
        labels_per_row = int((available_width + horizontal_gap) / (label_width + horizontal_gap))
        
        # Calculate rows per page
        rows_per_page = int((available_height + vertical_gap) / (label_height + vertical_gap))
        
        # Calculate total labels per sheet
        total_labels = labels_per_row * rows_per_page
        
        # Calculate actual spacing for centering
        total_row_width = (labels_per_row * label_width) + ((labels_per_row - 1) * horizontal_gap)
        actual_left_margin = left_margin + (available_width - total_row_width) / 2
        
        total_column_height = (rows_per_page * label_height) + ((rows_per_page - 1) * vertical_gap)
        actual_top_margin = top_margin + (available_height - total_column_height) / 2
        
        return {
            'labels_per_row': labels_per_row,
            'rows_per_page': rows_per_page,
            'total_labels': total_labels,
            'actual_left_margin': actual_left_margin,
            'actual_top_margin': actual_top_margin,
            'total_row_width': total_row_width,
            'total_column_height': total_column_height
        }
    
    def get_label_position(self, index: int, layout: Dict[str, Any]) -> Tuple[float, float]:
        """
        Get position for a specific label
        
        Args:
            index: Label index (0-based)
            layout: Layout calculations from calculate_layout()
            
        Returns:
            Tuple of (x, y) position in cm from bottom-left
        """
        row = index // layout['labels_per_row']
        col = index % layout['labels_per_row']
        
        x = layout['actual_left_margin'] + col * (self.settings['label_width'] + self.settings['horizontal_gap'])
        y = self.a4_height - layout['actual_top_margin'] - (row + 1) * self.settings['label_height'] - row * self.settings['vertical_gap']
        
        return x, y


class TagGenerator:
    """Generate plant tags as PDF"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize tag generator
        
        Args:
            settings: Dictionary with label settings and nursery info
        """
        self.settings = settings
        self.calculator = TagLayoutCalculator(settings)
        self.layout = self.calculator.calculate_layout()
        
    def create_single_tag(self, plant_data: Dict[str, Any], x: float, y: float, canvas_obj) -> None:
        """
        Create a single tag on the canvas
        
        Args:
            plant_data: Plant information dictionary
            x, y: Position in cm
            canvas_obj: ReportLab canvas object
        """
        c = canvas_obj
        label_w = self.settings['label_width'] * cm
        label_h = self.settings['label_height'] * cm
        
        # Convert position to points (ReportLab uses points)
        x_pt = x * cm
        y_pt = y * cm
        
        # Draw label border
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.5)
        c.rect(x_pt, y_pt, label_w, label_h)
        
        # Add nursery name
        nursery_name = self.settings.get('nursery_name', 'GrowLeafy Nursery')
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.Color(0.2, 0.6, 0.2))  # Dark green
        c.drawCentredString(x_pt + label_w/2, y_pt + label_h - 0.8*cm, nursery_name)
        
        # Add plant name (large bold)
        plant_name = plant_data.get('plant_name', 'Unknown Plant')
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.black)
        
        # Handle long names
        if len(plant_name) > 20:
            c.setFont("Helvetica-Bold", 11)
        
        c.drawCentredString(x_pt + label_w/2, y_pt + label_h - 1.8*cm, plant_name)
        
        # Add botanical name (optional)
        if self.settings.get('include_botanical_name', True) and plant_data.get('botanical_name'):
            botanical = plant_data['botanical_name']
            c.setFont("Helvetica-Oblique", 7)
            c.setFillColor(colors.Color(0.4, 0.4, 0.4))
            c.drawCentredString(x_pt + label_w/2, y_pt + label_h - 2.4*cm, botanical)
        
        # Add MRP
        mrp = plant_data.get('mrp', 0)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.Color(0.8, 0.2, 0.2))  # Red
        mrp_text = f"₹{mrp:,.2f}"
        c.drawCentredString(x_pt + label_w/2, y_pt + 1.5*cm, mrp_text)
        
        # Add barcode (optional)
        if self.settings.get('include_barcode', True) and plant_data.get('barcode'):
            barcode = plant_data['barcode']
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.black)
            c.drawCentredString(x_pt + label_w/2, y_pt + 0.5*cm, barcode)
        
        # Add QR code (optional)
        if self.settings.get('include_qr', True) and plant_data.get('qr_code'):
            # Add QR code placeholder
            c.setFillColor(colors.Color(0.9, 0.9, 0.9))
            qr_size = 1.5 * cm
            c.rect(x_pt + label_w - qr_size - 0.3*cm, y_pt + 0.3*cm, qr_size, qr_size, fill=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 5)
            c.drawCentredString(x_pt + label_w - qr_size/2 - 0.3*cm, y_pt + qr_size/2 + 0.3*cm, "QR")
        
        # Add image (optional)
        if self.settings.get('include_image', False) and plant_data.get('plant_image_url'):
            try:
                from reportlab.platypus import Image
                img = Image(plant_data['plant_image_url'], width=1.5*cm, height=1.5*cm)
                img.drawOn(c, x_pt + 0.3*cm, y_pt + 0.3*cm)
            except:
                pass
        
        # Draw cutting line (dotted)
        c.setDash(2, 2)
        c.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
        c.rect(x_pt + 0.1*cm, y_pt + 0.1*cm, label_w - 0.2*cm, label_h - 0.2*cm)
        c.setDash()
    
    def generate_tags_pdf(self, plants: List[Dict[str, Any]]) -> BytesIO:
        """
        Generate PDF with plant tags
        
        Args:
            plants: List of plant dictionaries
            
        Returns:
            BytesIO buffer containing PDF
        """
        buffer = BytesIO()
        
        # Create PDF with A4 size
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Calculate layout
        layout = self.layout
        
        # Generate tags
        for page_num in range(math.ceil(len(plants) / layout['total_labels'])):
            start_idx = page_num * layout['total_labels']
            end_idx = min(start_idx + layout['total_labels'], len(plants))
            
            for i in range(start_idx, end_idx):
                label_idx = i - start_idx
                x, y = self.calculator.get_label_position(label_idx, layout)
                self.create_single_tag(plants[i], x, y, c)
            
            # Add page number
            c.setFont("Helvetica", 6)
            c.setFillColor(colors.grey)
            c.drawCentredString(A4[0]/2, 0.5*cm, f"Page {page_num + 1} - GrowLeafy Tag Generator")
            
            if end_idx < len(plants):
                c.showPage()
        
        c.save()
        buffer.seek(0)
        return buffer
    
    def preview_layout(self) -> Dict[str, Any]:
        """
        Get layout preview information
        
        Returns:
            Dictionary with layout details for display
        """
        layout = self.layout
        return {
            'sheet_dimensions': f"{self.calculator.a4_width} x {self.calculator.a4_height} cm",
            'label_dimensions': f"{self.settings['label_width']} x {self.settings['label_height']} cm",
            'labels_per_row': layout['labels_per_row'],
            'rows_per_page': layout['rows_per_page'],
            'total_labels_per_sheet': layout['total_labels'],
            'margins': {
                'top': self.settings['top_margin'],
                'bottom': self.settings['bottom_margin'],
                'left': self.settings['left_margin'],
                'right': self.settings['right_margin']
            },
            'gaps': {
                'horizontal': self.settings['horizontal_gap'],
                'vertical': self.settings['vertical_gap']
            }
        }
