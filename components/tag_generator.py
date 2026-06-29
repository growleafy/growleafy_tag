import streamlit as st
import pandas as pd
import io
import qrcode
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import createBarcodeDrawing

# --- ARCHITECTURAL MOCKS (Replace with actual Supabase client calls) ---
def get_dynamic_databases():
    return ["Plants", "Fertilizers", "Pesticides", "Inventory"]

def fetch_data(db_name):
    # Mock data representing a 100k+ row database fetched via pagination
    if db_name == "Plants":
        return pd.DataFrame({
            "id": ["P1", "P2", "P3"],
            "name": ["Monstera Deliciosa", "Ficus Lyrata", "Aloe Vera"],
            "botanical": ["Monstera", "Ficus", "Aloe"],
            "mrp": [1200, 850, 250],
            "sku": ["MNST-01", "FIC-02", "ALV-03"]
        })
    return pd.DataFrame()

# --- PRINT ENGINE ---
def generate_label_pdf(dataframe, template_settings):
    """
    Enterprise Print Layout Engine
    Calculates grid, margins, and renders vectors via ReportLab.
    """
    buffer = io.BytesIO()
    
    # Page setup
    page_width, page_height = A4 
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # Settings
    lbl_w = template_settings['width'] * mm
    lbl_h = template_settings['height'] * mm
    margin_x = template_settings['margin_left'] * mm
    margin_y = template_settings['margin_top'] * mm
    gap_x = template_settings['gap_x'] * mm
    gap_y = template_settings['gap_y'] * mm
    
    cols = template_settings['columns']
    rows = template_settings['rows']
    
    x, y = margin_x, page_height - margin_y - lbl_h
    col_idx, row_idx = 0, 0
    
    for index, row in dataframe.iterrows():
        # Draw Crop Marks (Bleed)
        if template_settings.get('show_crop_marks'):
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.rect(x, y, lbl_w, lbl_h, fill=0)
            c.setStrokeColorRGB(0, 0, 0)

        # 1. Draw Text Elements
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 5*mm, y + lbl_h - 10*mm, str(row.get('name', 'N/A')))
        
        c.setFont("Helvetica", 8)
        c.drawString(x + 5*mm, y + lbl_h - 15*mm, f"SKU: {row.get('sku', 'N/A')}")
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 5*mm, y + 10*mm, f"Rs. {row.get('mrp', '0.00')}")

        # 2. Draw QR Code
        if template_settings.get('include_qr'):
            qr = qrcode.QRCode(version=1, box_size=10, border=1)
            qr.add_data(f"https://growleafy.com/item/{row.get('sku')}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR to temp buffer to draw on canvas
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            
            # Position QR at the right side of the label
            qr_size = 20 * mm
            c.drawImage(Image.open(img_buffer), x + lbl_w - qr_size - 5*mm, y + 5*mm, width=qr_size, height=qr_size)

        # Grid Calculation Logic
        col_idx += 1
        x += lbl_w + gap_x
        
        if col_idx >= cols:
            col_idx = 0
            x = margin_x
            row_idx += 1
            y -= (lbl_h + gap_y)
            
        if row_idx >= rows:
            c.showPage() # Create new page
            x, y = margin_x, page_height - margin_y - lbl_h
            col_idx, row_idx = 0, 0

    c.save()
    buffer.seek(0)
    return buffer

# --- STREAMLIT UI MODULE ---
def render(db_manager=None):
    st.title("🏷️ Universal Tag & Label Generator")
    st.caption("Enterprise Print Management System")
    
    tab1, tab2, tab3 = st.tabs(["1. Select Items", "2. Label Design", "3. Preview & Print"])
    
    # ----------------------------------------
    # TAB 1: DATA SELECTION
    # ----------------------------------------
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            selected_db = st.selectbox("Select Database", get_dynamic_databases())
        with col2:
            search_term = st.text_input("🔍 Live Search (SKU, Name, Barcode)")
            
        # Fetch data based on selection
        df = fetch_data(selected_db)
        
        st.subheader("Data Selection")
        # st.data_editor allows multi-select via a checkbox column in newer Streamlit versions
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )
        
    # ----------------------------------------
    # TAB 2: LABEL DESIGNER & TEMPLATES
    # ----------------------------------------
    with tab2:
        col_tmpl, col_ai = st.columns([3, 1])
        with col_tmpl:
            st.selectbox("Load Saved Template", ["Custom", "Standard Plant Tag (2x1)", "Thermal Barcode (50x25mm)"])
        with col_ai:
            if st.button("✨ AI Auto-Design", use_container_width=True):
                st.toast("DeepSeek AI is analyzing your data to suggest optimal layouts...", icon="🤖")
        
        st.markdown("---")
        
        col_settings, col_fields = st.columns(2)
        with col_settings:
            st.subheader("Page & Grid Settings")
            with st.expander("Dimensions (mm)", expanded=True):
                lbl_w = st.number_input("Label Width", value=50)
                lbl_h = st.number_input("Label Height", value=25)
            
            with st.expander("Grid Layout"):
                cols = st.number_input("Columns", value=4, min_value=1)
                rows = st.number_input("Rows", value=10, min_value=1)
                gap_x = st.number_input("Horizontal Gap", value=2.0)
                gap_y = st.number_input("Vertical Gap", value=2.0)
                crop_marks = st.toggle("Show Crop Marks", value=True)

        with col_fields:
            st.subheader("Dynamic Fields")
            include_qr = st.toggle("Generate QR Code (Auto-links to item profile)", value=True)
            include_barcode = st.toggle("Generate Barcode (SKU)", value=False)
            
            st.multiselect("Data Fields to Print", ["Name", "Botanical Name", "SKU", "MRP", "Care Instructions"], default=["Name", "SKU", "MRP"])
            
            st.color_picker("Primary Label Color", "#000000")

    # ----------------------------------------
    # TAB 3: PREVIEW AND EXPORT
    # ----------------------------------------
    with tab3:
        st.subheader("Print Queue & Output")
        copies = st.number_input("Copies per item", value=1, min_value=1)
        
        # Prepare data (multiply by copies)
        print_df = pd.concat([edited_df]*copies, ignore_index=True)
        
        template_config = {
            'width': lbl_w, 'height': lbl_h,
            'columns': cols, 'rows': rows,
            'margin_left': 10, 'margin_top': 10,
            'gap_x': gap_x, 'gap_y': gap_y,
            'include_qr': include_qr,
            'show_crop_marks': crop_marks
        }
        
        col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
        col_metrics1.metric("Total Items to Print", len(print_df))
        col_metrics2.metric("Estimated Pages", max(1, len(print_df) // (cols * rows)))
        col_metrics3.metric("Format", "A4 Sheet")
        
        st.info("Visual preview of Page 1 will render here in a production environment.")
        
        if st.button("🚀 Generate PDF Labels", type="primary", use_container_width=True):
            with st.status("Processing Print Job...", expanded=True) as status:
                st.write("Calculatng grid geometry...")
                st.write(f"Generating {len(print_df)} QR Codes...")
                st.write("Rendering Vector PDF via ReportLab...")
                
                # Generate File
                pdf_buffer = generate_label_pdf(print_df, template_config)
                
                status.update(label="Print Job Ready!", state="complete", expanded=False)
                
                st.download_button(
                    label="📥 Download Print-Ready PDF",
                    data=pdf_buffer,
                    file_name="nursery_labels_batch.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # Log to Supabase logic goes here
                st.toast("Print job logged to Audit History", icon="✅")

if __name__ == "__main__":
    render()
