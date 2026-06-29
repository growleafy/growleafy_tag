"""
Enterprise Universal Tag & Label Generator Component
"""
import streamlit as st
import pandas as pd
import io
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, A3, LETTER
from reportlab.lib.utils import ImageReader

# --- BILINGUAL DICTIONARY ---
LANG = {
    "English": {
        "title": "🏷️ Universal Tag & Label Generator",
        "tab1": "1. Select Items", "tab2": "2. Label Design", "tab3": "3. Preview & Print",
        "page_size": "Page Size",
        "nursery_name": "Nursery Name (Prints on Label)",
        "contact": "Contact Number",
        "font_size": "Base Font Size (pt)"
    },
    "Bengali": {
        "title": "🏷️ ইউনিভার্সাল ট্যাগ এবং লেবেল জেনারেটর",
        "tab1": "১. আইটেম নির্বাচন", "tab2": "২. লেবেল ডিজাইন", "tab3": "৩. প্রিভিউ এবং প্রিন্ট",
        "page_size": "পৃষ্ঠার আকার (Page Size)",
        "nursery_name": "নার্সারির নাম",
        "contact": "যোগাযোগের নম্বর",
        "font_size": "ফন্টের আকার (Font Size)"
    }
}

# --- PAGE SIZE MAP ---
PAGE_SIZES = {
    "A4 Sheet (210 x 297 mm)": A4,
    "A3 Sheet (297 x 420 mm)": A3,
    "US Letter (216 x 279 mm)": LETTER,
    "Thermal Roll Standard (100 x 150 mm)": (100*mm, 150*mm),
    "Thermal Roll Small (50 x 25 mm)": (50*mm, 25*mm)
}

# --- DATABASE MOCKS ---
def get_dynamic_databases():
    return ["Plants", "Fertilizers", "Pesticides", "Inventory"]

def fetch_data(db_name):
    if db_name == "Plants":
        return pd.DataFrame({
            "id": ["P1", "P2", "P3"],
            "name": ["Monstera Deliciosa", "Ficus Lyrata", "Aloe Vera"],
            "botanical": ["Monstera", "Ficus", "Aloe"],
            "mrp": [1200, 850, 250],
            "sku": ["MNST-01", "FIC-02", "ALV-03"]
        })
    return pd.DataFrame()

# --- LIVE PREVIEW GENERATOR (PIL) ---
def generate_preview_image(settings):
    """Generates a mockup image of a single label for the UI Preview"""
    # Convert mm to pixels (approx 1mm = 3.78px for web display)
    px_w = int(settings['width'] * 3.78)
    px_h = int(settings['height'] * 3.78)
    
    # Create blank white label with a border
    img = Image.new('RGB', (px_w, px_h), color='white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, px_w-1, px_h-1], outline="black", width=2)
    
    # Draw Mock Content
    pad = 10
    current_y = pad
    
    if settings.get('nursery_name'):
        draw.text((pad, current_y), settings['nursery_name'], fill="black")
        current_y += 20
        
    draw.text((pad, current_y), "Plant Name / Product", fill="black")
    draw.text((pad, current_y + 20), "SKU: 12345-ABC", fill="gray")
    draw.text((pad, current_y + 40), "Rs. 999.00", fill="black")
    
    if settings.get('contact'):
        draw.text((pad, px_h - 25), f"Ph: {settings['contact']}", fill="black")
        
    if settings.get('include_qr'):
        # Draw a mock QR code box
        qr_size = int(20 * 3.78)
        draw.rectangle([px_w - qr_size - pad, pad, px_w - pad, pad + qr_size], outline="black", fill="#f0f0f0")
        draw.text((px_w - qr_size - pad + 15, pad + 25), "QR", fill="black")
        
    return img

# --- ENTERPRISE PRINT ENGINE ---
def generate_label_pdf(dataframe, template_settings):
    buffer = io.BytesIO()
    
    # Get selected page size
    page_width, page_height = PAGE_SIZES.get(template_settings['page_format'], A4)
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    lbl_w = template_settings['width'] * mm
    lbl_h = template_settings['height'] * mm
    margin_x = template_settings['margin_left'] * mm
    margin_y = template_settings['margin_top'] * mm
    gap_x = template_settings['gap_x'] * mm
    gap_y = template_settings['gap_y'] * mm
    font_size = template_settings['font_size']
    
    cols = template_settings['columns']
    rows = template_settings['rows']
    
    x, y = margin_x, page_height - margin_y - lbl_h
    col_idx, row_idx = 0, 0
    
    for index, row in dataframe.iterrows():
        if template_settings.get('show_crop_marks'):
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.rect(x, y, lbl_w, lbl_h, fill=0)
            c.setStrokeColorRGB(0, 0, 0)

        # Draw Nursery Name
        if template_settings.get('nursery_name'):
            c.setFont("Helvetica-Bold", font_size - 2)
            c.drawString(x + 2*mm, y + lbl_h - 5*mm, template_settings['nursery_name'])

        # Draw Product Details
        c.setFont("Helvetica-Bold", font_size)
        c.drawString(x + 2*mm, y + lbl_h - 12*mm, str(row.get('name', 'N/A')))
        
        c.setFont("Helvetica", font_size - 2)
        c.drawString(x + 2*mm, y + lbl_h - 17*mm, f"SKU: {row.get('sku', 'N/A')}")
        
        c.setFont("Helvetica-Bold", font_size + 2)
        c.drawString(x + 2*mm, y + 10*mm, f"Rs. {row.get('mrp', '0.00')}")

        # Draw Contact
        if template_settings.get('contact'):
            c.setFont("Helvetica", font_size - 4)
            c.drawString(x + 2*mm, y + 3*mm, f"Ph: {template_settings['contact']}")

        # Draw QR Code
        if template_settings.get('include_qr'):
            qr = qrcode.QRCode(version=1, box_size=10, border=1)
            item_sku = str(row.get('sku', 'UNKNOWN'))
            qr.add_data(f"https://growleafy.com/item/{item_sku}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            
            qr_image = ImageReader(img_buffer)
            qr_size = 20 * mm
            c.drawImage(qr_image, x + lbl_w - qr_size - 2*mm, y + 2*mm, width=qr_size, height=qr_size)

        col_idx += 1
        x += lbl_w + gap_x
        
        if col_idx >= cols:
            col_idx = 0
            x = margin_x
            row_idx += 1
            y -= (lbl_h + gap_y)
            
        if row_idx >= rows:
            c.showPage() 
            x, y = margin_x, page_height - margin_y - lbl_h
            col_idx, row_idx = 0, 0

    c.save()
    buffer.seek(0)
    return buffer

# --- STREAMLIT UI MODULE ---
def render(db_manager=None):
    # Language Toggle
    if "lang" not in st.session_state:
        st.session_state.lang = "English"
        
    col_title, col_lang = st.columns([4, 1])
    with col_lang:
        st.session_state.lang = st.selectbox("Language / ভাষা", ["English", "Bengali"], key="tag_lang")
        
    t = LANG[st.session_state.lang]
    
    with col_title:
        st.title(t["title"])
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs([t["tab1"], t["tab2"], t["tab3"]])
    
    # ----------------------------------------
    # TAB 1: DATA SELECTION
    # ----------------------------------------
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            selected_db = st.selectbox("Select Database", get_dynamic_databases())
        with col2:
            search_term = st.text_input("🔍 Live Search (SKU, Name, Barcode)")
            
        df = fetch_data(selected_db)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
        
    # ----------------------------------------
    # TAB 2: LABEL DESIGNER & TEMPLATES
    # ----------------------------------------
    with tab2:
        # Define settings dictionary to store states
        template_config = {}
        
        col_settings, col_fields, col_preview = st.columns([1.5, 1.5, 1])
        
        with col_settings:
            st.subheader("Layout Settings")
            template_config['page_format'] = st.selectbox(t["page_size"], list(PAGE_SIZES.keys()))
            
            with st.expander("Dimensions (mm)", expanded=True):
                template_config['width'] = st.number_input("Label Width", value=60)
                template_config['height'] = st.number_input("Label Height", value=35)
            
            with st.expander("Grid Layout"):
                template_config['columns'] = st.number_input("Columns", value=3, min_value=1)
                template_config['rows'] = st.number_input("Rows", value=8, min_value=1)
                template_config['gap_x'] = st.number_input("Horizontal Gap", value=2.0)
                template_config['gap_y'] = st.number_input("Vertical Gap", value=2.0)
                template_config['show_crop_marks'] = st.toggle("Show Crop Marks", value=True)

        with col_fields:
            st.subheader("Content Settings")
            template_config['nursery_name'] = st.text_input(t["nursery_name"], placeholder="e.g. GrowLeafy Nursery")
            template_config['contact'] = st.text_input(t["contact"], placeholder="e.g. +91 9876543210")
            template_config['font_size'] = st.slider(t["font_size"], min_value=6, max_value=24, value=10)
            
            template_config['include_qr'] = st.toggle("Generate QR Code", value=True)
            st.multiselect("Data Fields to Print", ["Name", "Botanical Name", "SKU", "MRP"], default=["Name", "SKU", "MRP"])
            
        with col_preview:
            st.subheader("Live Preview")
            st.caption("Approximate visual layout:")
            # Generate and show live PIL preview
            preview_img = generate_preview_image(template_config)
            st.image(preview_img, use_container_width=True)
            
            # Save hardcoded margins for the PDF generation later
            template_config['margin_left'] = 10
            template_config['margin_top'] = 10

    # ----------------------------------------
    # TAB 3: PREVIEW AND EXPORT
    # ----------------------------------------
    with tab3:
        st.subheader("Print Queue & Output")
        copies = st.number_input("Copies per item", value=1, min_value=1)
        
        print_df = pd.concat([edited_df]*copies, ignore_index=True)
        
        col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
        col_metrics1.metric("Total Items to Print", len(print_df))
        col_metrics2.metric("Estimated Pages", max(1, (len(print_df) + (template_config['columns'] * template_config['rows']) - 1) // (template_config['columns'] * template_config['rows'])))
        col_metrics3.metric("Format selected", template_config['page_format'])
        
        if st.button("🚀 Generate PDF Labels", type="primary", use_container_width=True):
            if len(print_df) == 0:
                st.error("No items selected for printing.")
            else:
                with st.status("Processing Print Job...", expanded=True) as status:
                    pdf_buffer = generate_label_pdf(print_df, template_config)
                    status.update(label="Print Job Ready!", state="complete", expanded=False)
                    
                    st.download_button(
                        label="📥 Download Print-Ready PDF",
                        data=pdf_buffer,
                        file_name="nursery_labels_batch.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
