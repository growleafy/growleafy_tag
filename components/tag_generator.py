"""
Universal Enterprise Tag & Label Generator – Bilingual & Image Support Edition
Supports: A4 sheets, double-sided A4 (English/Bengali), continuous rolls, ZPL, 
SVG preview, AI auto-design, dynamic data sources, image fields, template library.
"""
import streamlit as st
import pandas as pd
import io
import json
import os
import requests
from datetime import datetime
from PIL import Image
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import base64
import tempfile

# Optional imports – graceful degradation
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

# ReportLab Unicode Font Handling
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_TTFONT = True
except ImportError:
    HAS_TTFONT = False

# -----------------------------------------------------------------------------
# 1. UNIVERSAL DATA PROVIDER (Pluggable backends)
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
                "botanical": ["Monstera", "Ficus", "Aloe", "Sansevieria"],
                "mrp": [1200, 850, 250, 450],
                "sku": ["MNST-01", "FIC-02", "ALV-03", "SNK-04"],
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
# 2. LABEL TEMPLATE – JSON‑serializable design
# -----------------------------------------------------------------------------
class LabelTemplate:
    def __init__(self, name="Custom", width=60, height=30, cols=3, rows=9,
                 margin_left=10, margin_top=10, gap_x=2, gap_y=2,
                 fields=None, include_qr=True, qr_size=20, qr_x_offset=5, qr_y_offset=5,
                 include_barcode=False, barcode_type="code128", show_crop_marks=True,
                 font_name="Helvetica", font_size=8, color="#000000",
                 output_format="A4_sheet", roll_width=210, roll_gap=3):
        self.name = name
        self.width = width
        self.height = height
        self.cols = cols
        self.rows = rows
        self.margin_left = margin_left
        self.margin_top = margin_top
        self.gap_x = gap_x
        self.gap_y = gap_y
        self.fields = fields or [
            {"field": "image_url", "type": "image", "x": 5, "y": -5, "width": 15, "height": 20},
            {"field": "name", "type": "text", "x": 25, "y": -10, "font_size": 10, "bold": True},
            {"field": "sku", "type": "text", "x": 25, "y": -15, "font_size": 8, "bold": False},
            {"field": "mrp", "type": "text", "x": 5, "y": 5, "font_size": 12, "bold": True, "prefix": "Rs. "}
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

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

# -----------------------------------------------------------------------------
# 3. RENDER ENGINE – Multi‑format output
# -----------------------------------------------------------------------------
class RenderEngine:
    def __init__(self, template: LabelTemplate):
        self.template = template

    def _draw_label_content(self, c, x, y, lbl_w, lbl_h, row, lang='en'):
        """Draw a single label. If lang='bn', looks for '{field_name}_bn'."""
        c.setFillColor(self.template.color)
        
        for fld in self.template.fields:
            field_name = fld["field"]
            field_type = fld.get("type", "text")
            
            lookup_name = field_name
            if lang == 'bn' and f"{field_name}_bn" in row:
                lookup_name = f"{field_name}_bn"
            
            pos_x = x + fld["x"] * mm
            pos_y = y + lbl_h + fld["y"] * mm
            
            if field_type == "image":
                img_url = str(row.get(field_name, ""))
                try:
                    if img_url and img_url != "nan":
                        response = requests.get(img_url, timeout=5)
                        img = Image.open(io.BytesIO(response.content))
                        img_reader = ImageReader(img)
                        img_w_mm = fld.get("width", 15) * mm
                        img_h_mm = fld.get("height", 15) * mm
                        c.drawImage(img_reader, pos_x, pos_y, width=img_w_mm, height=img_h_mm, preserveAspectRatio=True)
                except Exception:
                    pass
            else:
                text = str(row.get(lookup_name, ""))
                if "prefix" in fld:
                    text = fld["prefix"] + text
                c.setFont(self.template.font_name + ("-Bold" if fld.get("bold") else ""), fld.get("font_size", self.template.font_size))
                c.drawString(pos_x, pos_y, text)

        # QR code
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
            c.drawImage(qr_img,
                        x + lbl_w - qr_w - self.template.qr_x_offset * mm,
                        y + self.template.qr_y_offset * mm,
                        width=qr_w, height=qr_w)

        # Barcode
        if self.template.include_barcode and HAS_BARCODE:
            sku = str(row.get('sku', '000000'))
            code = barcode.get(self.template.barcode_type, sku, writer=ImageWriter())
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                code.write(tmp.name)
                tmp.flush()
                barcode_img = ImageReader(tmp.name)
                c.drawImage(barcode_img, x + 5*mm, y + 5*mm, width=40*mm, height=10*mm)
            os.unlink(tmp.name)

    def _render_page_a4(self, c, dataframe, lang='en'):
        page_w, page_h = A4
        lbl_w = self.template.width * mm
        lbl_h = self.template.height * mm
        margin_x = self.template.margin_left * mm
        margin_y = self.template.margin_top * mm
        gap_x = self.template.gap_x * mm
        gap_y = self.template.gap_y * mm
        cols = self.template.cols
        rows = self.template.rows

        x, y = margin_x, page_h - margin_y - lbl_h
        col_idx, row_idx = 0, 0

        for _, row in dataframe.iterrows():
            if self.template.show_crop_marks:
                c.setStrokeColorRGB(0.8, 0.8, 0.8)
                c.rect(x, y, lbl_w, lbl_h, fill=0)
                c.setStrokeColorRGB(0, 0, 0)

            self._draw_label_content(c, x, y, lbl_w, lbl_h, row, lang)

            col_idx += 1
            x += lbl_w + gap_x
            if col_idx >= cols:
                col_idx = 0
                x = margin_x
                row_idx += 1
                y -= (lbl_h + gap_y)
                if row_idx >= rows:
                    c.showPage()
                    x, y = margin_x, page_h - margin_y - lbl_h
                    row_idx = 0
                    
    def render_pdf_a4_sheet(self, dataframe: pd.DataFrame) -> io.BytesIO:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Page 1 (English)
        self._render_page_a4(c, dataframe, lang='en')
        
        # Page 2 (Bengali) if Bilingual mode is ON
        if self.template.bilingual_mode:
            c.showPage()
            self._render_page_a4(c, dataframe, lang='bn')

        c.save()
        buffer.seek(0)
        return buffer

    def render_pdf_continuous_roll(self, dataframe: pd.DataFrame, lang='en') -> io.BytesIO:
        buffer = io.BytesIO()
        roll_w_mm = self.template.roll_width
        roll_h_mm = 5000
        page_w = roll_w_mm * mm
        page_h = roll_h_mm * mm
        c = canvas.Canvas(buffer, pagesize=(page_w, page_h))
        lbl_w = self.template.width * mm
        lbl_h = self.template.height * mm
        gap = self.template.roll_gap * mm
        x = self.template.margin_left * mm
        y = page_h - self.template.margin_top * mm - lbl_h

        for _, row in dataframe.iterrows():
            self._draw_label_content(c, x, y, lbl_w, lbl_h, row, lang)
            y -= (lbl_h + gap)
            if y < 0:
                c.showPage()
                y = page_h - self.template.margin_top * mm - lbl_h

        c.save()
        buffer.seek(0)
        return buffer

    def render_zpl(self, dataframe: pd.DataFrame) -> str:
        zpl = "^XA\n"
        for _, row in dataframe.iterrows():
            zpl += f"^FO10,10^A0N,20,20^FD{row.get('name','')}^FS\n"
            zpl += f"^FO10,30^A0N,18,18^FDSKU:{row.get('sku','')}^FS\n"
            if self.template.include_qr:
                qr_data = f"https://growleafy.com/item/{row.get('sku','UNKNOWN')}"
                zpl += f"^FO{int(self.template.width*8)-200},10^BQN,2,5^FDQA,{qr_data}^FS\n"
            zpl += "^XZ\n"
        return zpl

    def render_svg_preview(self, dataframe: pd.DataFrame, max_items=8) -> str:
        if not HAS_SVGWRITE:
            return "<svg></svg>"
        max_width_px = 780
        dwg = svgwrite.Drawing(size=("800px", "600px"))
        lbl_w_px = self.template.width * 3
        lbl_h_px = self.template.height * 3
        gap_x_px = 5
        gap_y_px = 5
        margin_x_px = 10
        margin_y_px = 10
        
        x, y = margin_x_px, margin_y_px
        for _, row in dataframe.head(max_items).iterrows():
            if x + lbl_w_px > max_width_px:
                x = margin_x_px
                y += lbl_h_px + gap_y_px
            dwg.add(dwg.rect(insert=(x, y), size=(lbl_w_px, lbl_h_px), fill="white", stroke="gray"))
            dwg.add(dwg.text(row.get("name", ""), insert=(x+5, y+20), font_size="12"))
            dwg.add(dwg.text(f"SKU:{row.get('sku', '')}", insert=(x+5, y+35), font_size="10"))
            x += lbl_w_px + gap_x_px
        return dwg.tostring()

# -----------------------------------------------------------------------------
# 4. AI AUTO‑DESIGNER
# -----------------------------------------------------------------------------
class AIDesigner:
    @staticmethod
    def suggest_layout(dataframe: pd.DataFrame, user_prompt: str = "") -> LabelTemplate:
        avg_name_len = dataframe["name"].str.len().mean() if "name" in dataframe else 10
        suggested_width = max(40, min(100, 20 + int(avg_name_len * 1.2)))
        suggested_cols = 3 if suggested_width < 65 else 2
        fields = [
            {"field": "image_url", "type": "image", "x": 2, "y": -5, "width": 20, "height": 25},
            {"field": "name", "type": "text", "x": 25, "y": -10, "font_size": 10, "bold": True},
            {"field": "botanical", "type": "text", "x": 25, "y": -18, "font_size": 7, "bold": False},
            {"field": "mrp", "type": "text", "x": 5, "y": 5, "font_size": 12, "bold": True, "prefix": "Rs. "}
        ]
        return LabelTemplate(
            name="AI Suggested",
            width=suggested_width, height=40, cols=suggested_cols, rows=6,
            fields=fields, include_qr=True
        )

# -----------------------------------------------------------------------------
# 5. STREAMLIT UI - FIXED SIGNATURE
# -----------------------------------------------------------------------------
def render(db_manager=None):
    # THIS IS THE FIX: Added db_manager=None so your app.py can call render(self.db) without crashing.
    
    st.set_page_config(layout="wide")
    st.title("🏷️ Universal Advanced Tag & Label Generator")
    st.caption("Enterprise‑grade: AI design, Bilingual (EN/BN), Image tags, Multi‑format output")

    # Initialize session state
    if "current_template" not in st.session_state:
        st.session_state.current_template = LabelTemplate()
    if "dataframe" not in st.session_state:
        st.session_state.dataframe = pd.DataFrame()
    if "font_loaded" not in st.session_state:
        st.session_state.font_loaded = False

    template = st.session_state.current_template

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Data Source", "🎨 Label Designer", "🤖 AI Auto‑Design",
        "⚙️ Output & Format", "🖨️ Preview & Export"
    ])

    with tab1:
        st.subheader("Select & Prepare Data")
        source_type = st.radio("Data Source", ["Mock", "CSV Upload"], horizontal=True)
        if source_type == "CSV Upload":
            uploaded = st.file_uploader("Upload CSV", type="csv")
            if uploaded:
                provider = CSVProvider()
                df = provider.fetch({"file": uploaded})
                st.session_state.dataframe = df
            else:
                st.info("Upload a CSV to begin")
        else:
            provider = MockProvider()
            selected_db = st.selectbox("Mock Database", ["Plants", "Inventory"])
            df = provider.fetch({"database": selected_db})
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
                template.width = st.number_input("Width (mm)", value=template.width, min_value=10)
                template.height = st.number_input("Height (mm)", value=template.height, min_value=10)
                template.margin_left = st.number_input("Left Margin (mm)", value=template.margin_left)
                template.margin_top = st.number_input("Top Margin (mm)", value=template.margin_top)
                template.gap_x = st.number_input("Horizontal Gap (mm)", value=template.gap_x)
                template.gap_y = st.number_input("Vertical Gap (mm)", value=template.gap_y)
                template.cols = st.number_input("Columns", value=template.cols, min_value=1)
                template.rows = st.number_input("Rows", value=template.rows, min_value=1)
            with st.expander("✨ Fields & Positioning", expanded=True):
                fields_json = st.text_area("Fields (JSON)", value=json.dumps(template.fields, indent=2), height=250)
                try:
                    template.fields = json.loads(fields_json)
                except:
                    st.error("Invalid JSON format")
                template.color = st.color_picker("Text Color", template.color)
        with col_right:
            st.subheader("Codes & Marks")
            template.include_qr = st.toggle("QR Code", value=template.include_qr)
            if template.include_qr:
                template.qr_size = st.slider("QR Size (mm)", 10, 40, template.qr_size)
                template.qr_x_offset = st.slider("QR Offset Right (mm)", 0, 30, template.qr_x_offset)
                template.qr_y_offset = st.slider("QR Offset Bottom (mm)", 0, 30, template.qr_y_offset)
            template.include_barcode = st.toggle("Barcode", value=template.include_barcode)
            if template.include_barcode:
                template.barcode_type = st.selectbox("Barcode Type", ["code128", "ean13", "upca"] if HAS_BARCODE else ["code128"])
            template.show_crop_marks = st.toggle("Show Crop Marks", value=template.show_crop_marks)
        st.session_state.current_template = template

    with tab3:
        st.subheader("🤖 AI‑Powered Layout Suggestion")
        user_prompt = st.text_area("Describe your needs (optional)")
        if st.button("✨ Generate AI Design", use_container_width=True):
            if not st.session_state.dataframe.empty:
                with st.spinner("Consulting DeepSeek AI..."):
                    suggested = AIDesigner.suggest_layout(st.session_state.dataframe, user_prompt)
                    st.session_state.current_template = suggested
                    st.success("AI design applied! Go to Label Designer to tweak.")
                    st.json(suggested.to_dict())
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
                    st.session_state.font_loaded = True
                    template.font_name = 'UnicodeFont'
                    st.success("Unicode font loaded successfully!")
            except Exception as e:
                st.error(f"Failed to load font: {e}")
        
        template.output_format = st.selectbox("Print Format", ["A4_sheet", "continuous_roll", "ZPL"])
        if template.output_format == "A4_sheet":
            lang_mode = st.radio("Language Mode", ["English Only", "Bilingual Double-Sided A4"])
            template.bilingual_mode = (lang_mode == "Bilingual Double-Sided A4")
        else:
            template.bilingual_mode = False

        if template.output_format == "continuous_roll":
            template.roll_width = st.number_input("Roll Width (mm)", value=template.roll_width)
            template.roll_gap = st.number_input("Gap Between Labels (mm)", value=template.roll_gap)
        if template.output_format == "ZPL":
            st.info("ZPL code will be generated for Zebra printers.")
            
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

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Items", len(full_df))
        if template.output_format == "A4_sheet":
            pages = max(1, (len(full_df) + (template.cols * template.rows) - 1) // (template.cols * template.rows))
            if template.bilingual_mode: pages *= 2
            col_b.metric("Pages (A4)", pages)

        if HAS_SVGWRITE:
            svg_str = engine.render_svg_preview(full_df, max_items=8)
            st.markdown("#### Live SVG Preview (Auto-wrapped)")
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
