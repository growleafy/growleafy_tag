"""
Ultimate Tag Generator – Absolute Coordinate Math Engine & Hard Validation
"""
import streamlit as st
import pandas as pd
import io
import json
import os
import requests
from PIL import Image
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import base64
import tempfile

# Optional imports
try:
    import barcode
    from barcode.writer import ImageWriter
    HAS_BARCODE = True
except ImportError:
    HAS_BARCODE = False

try:
    import svgwrite
    HAS_SVGWRITE = True
except ImportError:
    HAS_SVGWRITE = False

try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_TTFONT = True
except ImportError:
    HAS_TTFONT = False

# -----------------------------------------------------------------------------
# 1. DATA PROVIDER
# -----------------------------------------------------------------------------
class DataProvider:
    def fetch(self, params: dict) -> pd.DataFrame:
        raise NotImplementedError

class MockProvider(DataProvider):
    def fetch(self, params):
        db = params.get("database", "Plants")
        if db == "Plants":
            return pd.DataFrame({
                "id": ["P1", "P2", "P3", "P4"],
                "name": ["Monstera Deliciosa", "Ficus Lyrata", "Aloe Vera", "Snake Plant"],
                "name_bn": ["মনস্টেরা ডেলিসিওসা", "ফিকাস লিরাটা", "অ্যালো ভেরা", "স্নেক প্ল্যান্ট"],
                "sku": ["MNST-01", "FIC-02", "ALV-03", "SNK-04"],
                "mrp": [1200, 850, 250, 450],
                "image_url": [
                    "https://images.unsplash.com/photo-1614594975525-e45190c55d0b?w=200", 
                    "https://images.unsplash.com/photo-1598881604340-9be93332939f?w=200", 
                    "https://images.unsplash.com/photo-1596712222938-bae0c60b71cd?w=200", 
                    "https://images.unsplash.com/photo-1607363581603-59cd2527742f?w=200"
                ]
            })
        return pd.DataFrame()

class CSVProvider(DataProvider):
    def fetch(self, params):
        uploaded_file = params.get("file")
        if uploaded_file:
            return pd.read_csv(uploaded_file)
        return pd.DataFrame()

def get_data_provider(source_type, credentials=None):
    if source_type == "Mock":
        return MockProvider()
    elif source_type == "CSV":
        return CSVProvider()
    return MockProvider()

# -----------------------------------------------------------------------------
# 2. LABEL TEMPLATE
# -----------------------------------------------------------------------------
class LabelTemplate:
    def __init__(self, name="Custom", width=60, height=30, cols=3, rows=9,
                 margin_left=10, margin_top=10, gap_x=2, gap_y=2,
                 fields=None, include_qr=True, qr_size=20, qr_x_offset=5, qr_y_offset=5,
                 include_barcode=False, barcode_type="code128", show_crop_marks=True,
                 font_name="Helvetica", font_size=8, color="#000000",
                 output_format="A4_sheet", roll_width=210, roll_gap=3,
                 enable_header=False, header_text="GrowLeafy Nursery", 
                 enable_footer=False, footer_text="Contact: +91-XXXXX | www.growleafy.com",
                 hide_sku_text_if_barcode=True):
        
        self.name = name
        self.width = width
        self.height = height
        self.cols = cols
        self.rows = rows
        self.margin_left = margin_left
        self.margin_top = margin_top
        self.gap_x = gap_x
        self.gap_y = gap_y
        # Safe default fields
        self.fields = fields or [
            {"field": "image_url", "type": "image", "x": 2, "y": 5, "width": 20, "height": 20},
            {"field": "name", "type": "text", "x": 25, "y": 22, "font_size": 10, "bold": True},
            {"field": "sku", "type": "text", "x": 25, "y": 14, "font_size": 8},
            {"field": "mrp", "type": "text", "x": 25, "y": 8, "font_size": 12, "bold": True, "prefix": "Rs. "}
        ]
        self.include_qr = include_qr
        self.qr_size = qr_size
        self.qr_x_offset = qr_x_offset
        self.qr_y_offset = qr_y_offset
        self.include_barcode = include_barcode
        self.barcode_type = barcode_type
        self.show_crop_marks = show_crop_marks
        self.font_name = font_name
        self.font_size = font_size
        self.color = color
        self.output_format = output_format
        self.roll_width = roll_width
        self.roll_gap = roll_gap
        self.bilingual_mode = False
        self.enable_header = enable_header
        self.header_text = header_text
        self.enable_footer = enable_footer
        self.footer_text = footer_text
        self.hide_sku_text_if_barcode = hide_sku_text_if_barcode

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

# -----------------------------------------------------------------------------
# 3. PRECISION COORDINATE ENGINE
# -----------------------------------------------------------------------------
class RenderEngine:
    def __init__(self, template: LabelTemplate):
        self.template = template

    def calculate_minimum_required_height(self):
        if not self.template.fields:
            return 20
        
        y_values = [f.get("y", 0) for f in self.template.fields]
        max_y = max(y_values)
        min_y = min(y_values)
        
        top_padding = 2.0
        bottom_padding = 2.0
        
        if self.template.enable_header:
            top_padding += 12.0
        if self.template.enable_footer:
            bottom_padding += 10.0
            
        min_height = bottom_padding + (max_y - min_y) + top_padding
        return int(min_height + 5)

    def _draw_label_content(self, c, x, y, lbl_w_mm, lbl_h_mm, row, lang='en'):
        lbl_w = lbl_w_mm * mm
        lbl_h = lbl_h_mm * mm
        
        # ABSOLUTE ANCHORS FOR THE BOX
        box_top_y = y
        box_bottom_y = y + lbl_h
        box_right_x = x + lbl_w

        # 1. Branding Header (Top-Left, 2mm from top)
        if self.template.enable_header:
            c.setFont(self.template.font_name, 10)
            c.setFillColorRGB(0, 0, 0)
            c.drawCentredString(x + lbl_w / 2, box_top_y + 2*mm, self.template.header_text)

        # 2. Branding Footer (Bottom, 2mm from bottom)
        if self.template.enable_footer:
            c.setFont(self.template.font_name, 8)
            c.setFillColorRGB(0.2, 0.2, 0.2)
            c.drawCentredString(x + lbl_w / 2, box_bottom_y - 2*mm, self.template.footer_text)

        # 3. Content Fields
        for fld in self.template.fields:
            field_name = fld["field"]
            field_type = fld.get("type", "text")
            
            if self.template.include_barcode and self.template.hide_sku_text_if_barcode and field_name == "sku":
                continue
            
            lookup_name = field_name
            if lang == 'bn' and f"{field_name}_bn" in row:
                lookup_name = f"{field_name}_bn"
            
            pos_x = x + fld["x"] * mm
            
            if field_type == "image":
                img_url = str(row.get(field_name, ""))
                try:
                    if img_url and img_url != "nan":
                        response = requests.get(img_url, timeout=5)
                        img = Image.open(io.BytesIO(response.content))
                        img_reader = ImageReader(img)
                        img_w_mm = fld.get("width", 15) * mm
                        img_h_mm = fld.get("height", 15) * mm
                        # IMAGE MATH: Offsets from bottom, but ReportLab draws Image Top-Left.
                        pos_y = box_bottom_y - (fld["y"] * mm) - img_h_mm
                        c.drawImage(img_reader, pos_x, pos_y, width=img_w_mm, height=img_h_mm, preserveAspectRatio=True)
                except Exception:
                    pass
            else:
                text = str(row.get(lookup_name, ""))
                if "prefix" in fld:
                    text = fld["prefix"] + text
                c.setFont(self.template.font_name + ("-Bold" if fld.get("bold") else ""), fld.get("font_size", self.template.font_size))
                # TEXT MATH: Baseline is offset from bottom.
                pos_y = box_bottom_y - (fld["y"] * mm)
                c.drawString(pos_x, pos_y, text)

        # 4. QR Code (Anchored precisely to Top-Right)
        if self.template.include_qr:
            qr = qrcode.QRCode(version=1, box_size=10, border=1)
            qr.add_data(f"https://growleafy.com/item/{row.get('sku', 'UNKNOWN')}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qr_img = ImageReader(buf)
            qr_w = self.template.qr_size * mm
            qr_h = self.template.qr_size * mm
            # QR MATH: Anchored from Top-Right
            pos_x = box_right_x - qr_w - self.template.qr_x_offset * mm
            pos_y = box_top_y + self.template.qr_y_offset * mm
            c.drawImage(qr_img, pos_x, pos_y, width=qr_w, height=qr_h)

        # 5. Barcode (Anchored precisely to Bottom-Center, 2mm from bottom)
        if self.template.include_barcode and HAS_BARCODE:
            sku = str(row.get('sku', '000000'))
            code = barcode.get(self.template.barcode_type, sku, writer=ImageWriter())
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                code.write(tmp.name)
                tmp.flush()
                barcode_img = ImageReader(tmp.name)
                
                barcode_w_mm = min(40, lbl_w_mm - 10)
                barcode_h_mm = 10
                barcode_x = x + (lbl_w_mm - barcode_w_mm) / 2 * mm
                # BARCODE MATH: Bottom edge should be 2mm from box bottom. Top-Left of image is at Bottom - Height - 2mm.
                barcode_y = box_bottom_y - (barcode_h_mm * mm) - (2 * mm)
                
                c.drawImage(barcode_img, barcode_x, barcode_y, width=barcode_w_mm*mm, height=barcode_h_mm*mm)
            os.unlink(tmp.name)

    def _render_page_a4(self, c, dataframe, lang='en'):
        page_w_mm, page_h_mm = 210, 297
        lbl_w_mm = self.template.width
        lbl_h_mm = self.template.height
        margin_x_mm = self.template.margin_left
        margin_y_mm = self.template.margin_top
        gap_x_mm = self.template.gap_x
        gap_y_mm = self.template.gap_y
        
        max_allowed_cols = int((page_w_mm - 2 * margin_x_mm) / (lbl_w_mm + gap_x_mm))
        actual_cols = min(self.template.cols, max_allowed_cols if max_allowed_cols > 0 else 1)
        
        x = margin_x_mm * mm
        y = page_h_mm * mm - margin_y_mm * mm - lbl_h_mm * mm
        col_idx, row_idx = 0, 0

        for _, row in dataframe.iterrows():
            if self.template.show_crop_marks:
                c.setStrokeColorRGB(0.8, 0.8, 0.8)
                c.rect(x, y, lbl_w_mm*mm, lbl_h_mm*mm, fill=0)
                c.setStrokeColorRGB(0, 0, 0)

            self._draw_label_content(c, x, y, lbl_w_mm, lbl_h_mm, row, lang)

            col_idx += 1
            x += (lbl_w_mm + gap_x_mm) * mm
            
            if col_idx >= actual_cols:
                col_idx = 0
                x = margin_x_mm * mm
                row_idx += 1
                y -= (lbl_h_mm + gap_y_mm) * mm
                if row_idx >= self.template.rows:
                    c.showPage()
                    x = margin_x_mm * mm
                    y = page_h_mm * mm - margin_y_mm * mm - lbl_h_mm * mm
                    row_idx = 0
                    
    def render_pdf_a4_sheet(self, dataframe: pd.DataFrame) -> io.BytesIO:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        self._render_page_a4(c, dataframe, lang='en')
        if self.template.bilingual_mode:
            c.showPage()
            self._render_page_a4(c, dataframe, lang='bn')
        c.save()
        buffer.seek(0)
        return buffer

    def render_svg_preview(self, dataframe: pd.DataFrame, max_items=8) -> str:
        if not HAS_SVGWRITE:
            return "<svg></svg>"
            
        page_w_px = 800
        scale = 3
        lbl_w_px = self.template.width * scale
        lbl_h_px = self.template.height * scale
        gap_x_px = self.template.gap_x * scale
        gap_y_px = self.template.gap_y * scale
        margin_x_px = self.template.margin_left * scale
        margin_y_px = self.template.margin_top * scale
        
        max_allowed_cols = int((page_w_px - 2 * margin_x_px) / (lbl_w_px + gap_x_px))
        actual_cols = min(self.template.cols, max_allowed_cols if max_allowed_cols > 0 else 1)
        
        dwg = svgwrite.Drawing(size=(f"{page_w_px}px", "800px"))
        x, y = margin_x_px, margin_y_px
        col_idx, row_idx = 0, 0
        
        for _, row in dataframe.head(max_items).iterrows():
            dwg.add(dwg.rect(insert=(x, y), size=(lbl_w_px, lbl_h_px), fill="white", stroke="#000000", stroke_width=2))
            
            for fld in self.template.fields:
                if self.template.include_barcode and self.template.hide_sku_text_if_barcode and fld.get("field") == "sku":
                    continue

                pos_x = x + fld["x"] * scale
                
                if fld.get("type") == "text":
                    text = str(row.get(fld["field"], ""))
                    if "prefix" in fld:
                        text = fld["prefix"] + text
                    font_size = fld.get("font_size", self.template.font_size)
                    # SVG coordinates accurately mimic the strict math
                    pos_y = y + lbl_h_px - (fld["y"] * scale)
                    dwg.add(dwg.text(text, insert=(pos_x, pos_y), font_size=f"{font_size}px", fill="#000000", font_family="sans-serif"))
            
            if self.template.include_barcode:
                barcode_w_px = min(40*scale, lbl_w_px - 20)
                barcode_h_px = 10*scale
                barcode_x = x + (lbl_w_px - barcode_w_px)/2
                barcode_y = y + lbl_h_px - (barcode_h_px) - (2 * scale)
                dwg.add(dwg.rect(insert=(barcode_x, barcode_y), size=(barcode_w_px, barcode_h_px), fill="#000000"))

            col_idx += 1
            x += lbl_w_px + gap_x_px
            
            if col_idx >= actual_cols:
                col_idx = 0
                x = margin_x_px
                row_idx += 1
                y += lbl_h_px + gap_y_px
                
        return dwg.tostring()

# -----------------------------------------------------------------------------
# 4. STREAMLIT UI
# -----------------------------------------------------------------------------
def render(db_manager=None):
    st.set_page_config(layout="wide")
    st.title("🏷️ Universal Advanced Tag & Label Generator")
    st.caption("Absolute Anchor Math Engine: Barcodes and Texts are strictly pinned inside boxes.")

    if "current_template" not in st.session_state:
        st.session_state.current_template = LabelTemplate()
    if "dataframe" not in st.session_state:
        st.session_state.dataframe = pd.DataFrame()

    template = st.session_state.current_template

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Data Source", "🎨 Label Designer", "🤖 AI Auto‑Design", "⚙️ Output & Format", "🖨️ Preview & Export"])

    with tab1:
        st.subheader("Select & Prepare Data")
        source_type = st.radio("Data Source", ["Mock", "CSV Upload"], horizontal=True)
        if source_type == "CSV Upload":
            uploaded = st.file_uploader("Upload CSV", type="csv")
            if uploaded:
                df = CSVProvider().fetch({"file": uploaded})
                st.session_state.dataframe = df
            else:
                st.info("Upload a CSV to begin")
        else:
            selected_db = st.selectbox("Mock Database", ["Plants", "Inventory"])
            df = MockProvider().fetch({"database": selected_db})
            st.session_state.dataframe = df

        if not st.session_state.dataframe.empty:
            st.subheader("Data Preview")
            edited_df = st.data_editor(st.session_state.dataframe, num_rows="dynamic", use_container_width=True, hide_index=True)
            st.session_state.dataframe = edited_df

    with tab2:
        st.subheader("Design Your Label")
        col_left, col_right = st.columns([2, 1])
        with col_left:
            with st.expander("📐 Dimensions & Grid", expanded=True):
                template.width = st.number_input("Width (mm)", value=template.width, min_value=20)
                template.height = st.number_input("Height (mm)", value=template.height, min_value=20)
                template.margin_left = st.number_input("Left Margin (mm)", value=template.margin_left)
                template.margin_top = st.number_input("Top Margin (mm)", value=template.margin_top)
                template.gap_x = st.number_input("Horizontal Gap (mm)", value=template.gap_x)
                template.gap_y = st.number_input("Vertical Gap (mm)", value=template.gap_y)
                template.cols = st.number_input("Columns", value=template.cols, min_value=1)
                template.rows = st.number_input("Rows", value=template.rows, min_value=1)
            
            with st.expander("✨ Fields & Positioning (y = offset from bottom)", expanded=True):
                st.caption("`y` refers to mm away from the BOTTOM edge. If `y` is too close to `Height`, text gets squeezed.")
                fields_json = st.text_area("Fields (JSON)", value=json.dumps(template.fields, indent=2), height=250)
                try:
                    template.fields = json.loads(fields_json)
                except:
                    st.error("Invalid JSON format")
                template.color = st.color_picker("Text Color", template.color)

            with st.expander("📞 Branding (Nursery Name & Contact)", expanded=True):
                template.enable_header = st.toggle("Show Header", value=template.enable_header)
                if template.enable_header:
                    template.header_text = st.text_input("Header Text", value=template.header_text)
                template.enable_footer = st.toggle("Show Footer", value=template.enable_footer)
                if template.enable_footer:
                    template.footer_text = st.text_input("Footer Text", value=template.footer_text)
                
        with col_right:
            st.subheader("Codes & Marks")
            template.include_qr = st.toggle("QR Code", value=template.include_qr)
            if template.include_qr:
                template.qr_size = st.slider("QR Size (mm)", 10, 40, template.qr_size)
                template.qr_x_offset = st.slider("QR Offset Right (mm)", 0, 30, template.qr_x_offset)
                template.qr_y_offset = st.slider("QR Offset Top (mm)", 0, 30, template.qr_y_offset)
                
            template.include_barcode = st.toggle("Barcode", value=template.include_barcode)
            if template.include_barcode:
                template.barcode_type = st.selectbox("Barcode Type", ["code128", "ean13", "upca"] if HAS_BARCODE else ["code128"])
                template.hide_sku_text_if_barcode = st.checkbox("Hide text SKU when Barcode is active", value=template.hide_sku_text_if_barcode)
            
            template.show_crop_marks = st.toggle("Show Crop Marks", value=template.show_crop_marks)

        st.session_state.current_template = template

    with tab3:
        st.subheader("🤖 AI‑Powered Layout Suggestion")
        if st.button("✨ Generate AI Design", use_container_width=True):
            if not st.session_state.dataframe.empty:
                with st.spinner("Generating..."):
                    avg_name_len = st.session_state.dataframe["name"].str.len().mean() if "name" in st.session_state.dataframe else 10
                    suggested_width = max(40, min(100, 20 + int(avg_name_len * 1.2)))
                    suggested_cols = 3 if suggested_width < 65 else 2
                    fields = [
                        {"field": "image_url", "type": "image", "x": 2, "y": 5, "width": 20, "height": 20},
                        {"field": "name", "type": "text", "x": 25, "y": 22, "font_size": 10, "bold": True},
                        {"field": "mrp", "type": "text", "x": 25, "y": 8, "font_size": 12, "bold": True, "prefix": "Rs. "}
                    ]
                    suggested = LabelTemplate(name="AI Suggested", width=suggested_width, height=40, cols=suggested_cols, rows=6, fields=fields, include_qr=True)
                    st.session_state.current_template = suggested
                    st.success("AI design applied!")
            else:
                st.warning("Load data first")

    with tab4:
        st.subheader("Output Settings")
        st.markdown("#### 🔤 Unicode Font Setup (Required for Bengali)")
        uploaded_font = st.file_uploader("Upload a Unicode .ttf font", type=["ttf"])
        if uploaded_font and HAS_TTFONT:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tmp:
                    tmp.write(uploaded_font.getvalue())
                    tmp.flush()
                    pdfmetrics.registerFont(TTFont('UnicodeFont', tmp.name))
                    template.font_name = 'UnicodeFont'
                    st.success("Unicode font loaded successfully!")
            except Exception as e:
                st.error(f"Failed to load font: {e}")

        template.output_format = st.selectbox("Print Format", ["A4_sheet", "continuous_roll", "ZPL"])
        if template.output_format == "A4_sheet":
            lang_mode = st.radio("Language Mode", ["English Only", "Bilingual Double-Sided A4"])
            template.bilingual_mode = (lang_mode == "Bilingual Double-Sided A4")

        if template.output_format == "continuous_roll":
            template.roll_width = st.number_input("Roll Width (mm)", value=template.roll_width)
            template.roll_gap = st.number_input("Gap Between Labels (mm)", value=template.roll_gap)
            
        copies = st.number_input("Copies per item", value=1, min_value=1)
        st.session_state.copies = copies
        st.session_state.current_template = template

    with tab5:
        st.subheader("Preview & Generate")
        if st.session_state.dataframe.empty:
            st.warning("No data to print. Select data source first.")
            return

        full_df = pd.concat([st.session_state.dataframe] * st.session_state.copies, ignore_index=True)
        engine = RenderEngine(template)

        # HARD VALIDATIONS
        page_w_mm = 210
        max_allowed_cols = int((page_w_mm - 2 * template.margin_left) / (template.width + template.gap_x))
        if template.cols > max_allowed_cols:
            st.error(f"⚠️ Column Overflow! Page is {page_w_mm}mm wide. Max columns is {max_allowed_cols}. Please reduce Columns.")
            st.stop()

        min_required_height = engine.calculate_minimum_required_height()
        if template.height < min_required_height:
            st.error(
                f"🚫 **Height Shortage Detected!** \n\n"
                f"Your current Tag Height is **{template.height}mm**, but the layout requires **{min_required_height}mm** to fit all elements securely.\n\n"
                f"👉 **Please increase the Height (mm) slider to at least {min_required_height}mm.**"
            )
            if st.button(f"✏️ Auto-Fix Height to {min_required_height}mm"):
                template.height = min_required_height
                st.session_state.current_template = template
                st.rerun()
            st.stop()

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Items", len(full_df))
        if template.output_format == "A4_sheet":
            items_per_page = min(template.cols, max_allowed_cols) * template.rows
            pages = max(1, (len(full_df) + items_per_page - 1) // items_per_page)
            if template.bilingual_mode: pages *= 2
            col_b.metric("Pages (A4)", pages)

        st.subheader("📌 Live Layout Preview")
        if HAS_SVGWRITE:
            svg_str = engine.render_svg_preview(full_df, max_items=8)
            st.image(f"data:image/svg+xml;base64,{base64.b64encode(svg_str.encode()).decode()}", use_column_width=True)

        if st.button("🚀 Generate & Download", type="primary", use_container_width=True):
            with st.status("Rendering...", expanded=True) as status:
                if template.output_format == "A4_sheet":
                    buf = engine.render_pdf_a4_sheet(full_df)
                    mime, fname = "application/pdf", "labels_a4.pdf"
                elif template.output_format == "continuous_roll":
                    buf = engine.render_pdf_continuous_roll(full_df)
                    mime, fname = "application/pdf", "labels_roll.pdf"
                elif template.output_format == "ZPL":
                    zpl_code = engine.render_zpl(full_df)
                    buf = io.BytesIO(zpl_code.encode())
                    mime, fname = "text/plain", "labels.zpl"
                status.update(label="Ready!", state="complete")
                st.download_button("📥 Download", data=buf, file_name=fname, mime=mime, use_container_width=True)

if __name__ == "__main__":
    render()
