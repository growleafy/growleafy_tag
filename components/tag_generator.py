"""
Universal Enterprise Tag & Label Generator – Most Advanced Edition
Supports: A4 sheets, continuous rolls, ZPL, SVG preview, AI auto-design, barcode types, 
dynamic data sources, template library, and more.
"""
import streamlit as st
import pandas as pd
import io
import json
import os
from datetime import datetime
from PIL import Image
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.graphics import renderPM
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

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

# -----------------------------------------------------------------------------
# 1. UNIVERSAL DATA PROVIDER (Pluggable backends)
# -----------------------------------------------------------------------------
class DataProvider:
    """Base class for fetching item data."""
    def fetch(self, params: dict) -> pd.DataFrame:
        raise NotImplementedError

class MockProvider(DataProvider):
    def fetch(self, params):
        db = params.get("database", "Plants")
        if db == "Plants":
            return pd.DataFrame({
                "id": ["P1", "P2", "P3", "P4"],
                "name": ["Monstera Deliciosa", "Ficus Lyrata", "Aloe Vera", "Snake Plant"],
                "botanical": ["Monstera", "Ficus", "Aloe", "Sansevieria"],
                "mrp": [1200, 850, 250, 450],
                "sku": ["MNST-01", "FIC-02", "ALV-03", "SNK-04"],
                "description": ["Tropical beauty", "Statement tree", "Medicinal", "Air purifier"]
            })
        return pd.DataFrame()

class CSVProvider(DataProvider):
    def fetch(self, params):
        uploaded_file = params.get("file")
        if uploaded_file:
            return pd.read_csv(uploaded_file)
        return pd.DataFrame()

# Manager to select provider
def get_data_provider(source_type, credentials=None):
    if source_type == "Mock":
        return MockProvider()
    elif source_type == "CSV":
        return CSVProvider()
    # else Supabase, Google Sheets, etc. – add later
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
        self.width = width          # mm
        self.height = height
        self.cols = cols
        self.rows = rows
        self.margin_left = margin_left
        self.margin_top = margin_top
        self.gap_x = gap_x
        self.gap_y = gap_y
        self.fields = fields or [
            {"field": "name", "x": 5, "y": -10, "font_size": 10, "bold": True},
            {"field": "sku", "x": 5, "y": -15, "font_size": 8, "bold": False},
            {"field": "mrp", "x": 5, "y": 10, "font_size": 12, "bold": True, "prefix": "Rs. "}
        ]
        self.include_qr = include_qr
        self.qr_size = qr_size
        self.qr_x_offset = qr_x_offset  # from right edge
        self.qr_y_offset = qr_y_offset  # from bottom edge
        self.include_barcode = include_barcode
        self.barcode_type = barcode_type
        self.show_crop_marks = show_crop_marks
        self.font_name = font_name
        self.font_size = font_size
        self.color = color
        self.output_format = output_format  # "A4_sheet", "continuous_roll", "ZPL"
        self.roll_width = roll_width        # mm (for continuous roll)
        self.roll_gap = roll_gap

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

    def _draw_label_content(self, c, x, y, lbl_w, lbl_h, row):
        """Common drawing for PDF backends."""
        c.setFillColor(self.template.color)
        # Draw all text fields
        for fld in self.template.fields:
            field_name = fld["field"]
            if field_name not in row:
                continue
            text = str(row[field_name])
            if "prefix" in fld:
                text = fld["prefix"] + text
            c.setFont(self.template.font_name + ("-Bold" if fld.get("bold") else ""), fld.get("font_size", self.template.font_size))
            pos_x = x + fld["x"] * mm
            pos_y = y + lbl_h + fld["y"] * mm  # y offset from top‑left of label
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

    def render_pdf_a4_sheet(self, dataframe: pd.DataFrame) -> io.BytesIO:
        """Tiled A4 pages."""
        buffer = io.BytesIO()
        page_w, page_h = A4
        c = canvas.Canvas(buffer, pagesize=A4)
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

            self._draw_label_content(c, x, y, lbl_w, lbl_h, row)

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

        c.save()
        buffer.seek(0)
        return buffer

    def render_pdf_continuous_roll(self, dataframe: pd.DataFrame) -> io.BytesIO:
        """Single long page representing a continuous roll."""
        buffer = io.BytesIO()
        roll_w_mm = self.template.roll_width
        roll_h_mm = 5000  # artificially long
        page_w = roll_w_mm * mm
        page_h = roll_h_mm * mm
        c = canvas.Canvas(buffer, pagesize=(page_w, page_h))
        lbl_w = self.template.width * mm
        lbl_h = self.template.height * mm
        gap = self.template.roll_gap * mm
        x = self.template.margin_left * mm
        y = page_h - self.template.margin_top * mm - lbl_h

        for _, row in dataframe.iterrows():
            self._draw_label_content(c, x, y, lbl_w, lbl_h, row)
            y -= (lbl_h + gap)
            if y < 0:
                c.showPage()
                y = page_h - self.template.margin_top * mm - lbl_h

        c.save()
        buffer.seek(0)
        return buffer

    def render_zpl(self, dataframe: pd.DataFrame) -> str:
        """Generate ZPL II code for Zebra printers."""
        zpl = "^XA\n"
        lbl_w_dots = int(self.template.width * 8)  # 8 dpmm
        lbl_h_dots = int(self.template.height * 8)
        for _, row in dataframe.iterrows():
            zpl += f"^FO10,10^A0N,20,20^FD{row.get('name','')}^FS\n"
            zpl += f"^FO10,30^A0N,18,18^FDSKU:{row.get('sku','')}^FS\n"
            if self.template.include_qr:
                qr_data = f"https://growleafy.com/item/{row.get('sku','UNKNOWN')}"
                zpl += f"^FO{lbl_w_dots-200},10^BQN,2,5^FDQA,{qr_data}^FS\n"
            zpl += "^XZ\n"
        return zpl

    def render_svg_preview(self, dataframe: pd.DataFrame, max_items=4) -> str:
        """Return SVG string for browser preview."""
        if not HAS_SVGWRITE:
            return "<svg></svg>"
        dwg = svgwrite.Drawing(size=("800px", "400px"))
        # Simple grid preview: render first few labels
        x, y = 10, 10
        lbl_w_px = self.template.width * 3
        lbl_h_px = self.template.height * 3
        for i, (_, row) in enumerate(dataframe.head(max_items).iterrows()):
            dwg.add(dwg.rect(insert=(x, y), size=(lbl_w_px, lbl_h_px), fill="white", stroke="gray"))
            dwg.add(dwg.text(row.get("name",""), insert=(x+5, y+20), font_size="12"))
            dwg.add(dwg.text(f"SKU:{row.get('sku','')}", insert=(x+5, y+40), font_size="10"))
            x += lbl_w_px + 5
            if x > 750:
                x = 10
                y += lbl_h_px + 5
        return dwg.tostring()

# -----------------------------------------------------------------------------
# 4. AI AUTO‑DESIGNER (DeepSeek stub – replace with API)
# -----------------------------------------------------------------------------
class AIDesigner:
    @staticmethod
    def suggest_layout(dataframe: pd.DataFrame, user_prompt: str = "") -> LabelTemplate:
        """Calls DeepSeek API to analyze data and return optimal layout.
           For now, returns a smart heuristic template."""
        # Mock AI logic: if names are long, increase width; if many columns, use landscape.
        avg_name_len = dataframe["name"].str.len().mean() if "name" in dataframe else 10
        suggested_width = max(40, min(100, 20 + int(avg_name_len * 1.2)))
        suggested_cols = 3 if suggested_width < 65 else 2
        fields = [
            {"field": "name", "x": 5, "y": -10, "font_size": 10, "bold": True},
            {"field": "botanical", "x": 5, "y": -18, "font_size": 7, "bold": False},
            {"field": "mrp", "x": 5, "y": 10, "font_size": 12, "bold": True, "prefix": "Rs. "}
        ]
        return LabelTemplate(
            name="AI Suggested",
            width=suggested_width, height=35, cols=suggested_cols, rows=8,
            fields=fields, include_qr=True
        )

# -----------------------------------------------------------------------------
# 5. THERMAL PRINTER MANAGER – settings helper
# -----------------------------------------------------------------------------
class ThermalPrinterManager:
    def __init__(self):
        self.supported_modes = ["continuous_roll", "gap", "black_mark"]

    def validate_template(self, template: LabelTemplate) -> bool:
        if template.output_format == "continuous_roll":
            return template.roll_width > 0
        return True

# -----------------------------------------------------------------------------
# 6. STREAMLIT UI – Modular tabs
# -----------------------------------------------------------------------------
def render(db_manager=None):
    st.set_page_config(layout="wide")
    st.title("🏷️ Universal Advanced Tag & Label Generator")
    st.caption("Enterprise‑grade: AI design, multi‑format output, pluggable data")

    # Initialize session state for template and data
    if "current_template" not in st.session_state:
        st.session_state.current_template = LabelTemplate()
    if "dataframe" not in st.session_state:
        st.session_state.dataframe = pd.DataFrame()

    template = st.session_state.current_template

    # ---------- TAB 1: DATA SOURCE ----------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Data Source", "🎨 Label Designer", "🤖 AI Auto‑Design",
        "⚙️ Output & Format", "🖨️ Preview & Export"
    ])

    with tab1:
        st.subheader("Select & Prepare Data")
        source_type = st.radio("Data Source", ["Mock", "CSV Upload", "Supabase (coming soon)"], horizontal=True)
        provider = None
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

    # ---------- TAB 2: LABEL DESIGNER ----------
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
            with st.expander("✨ Fields & Positioning"):
                st.write("Define text fields (x,y in mm from top‑left label corner)")
                fields_json = st.text_area("Fields (JSON)", value=json.dumps(template.fields, indent=2), height=200)
                try:
                    template.fields = json.loads(fields_json)
                except:
                    st.error("Invalid JSON")
                template.font_name = st.selectbox("Font", ["Helvetica", "Courier", "Times-Roman"])
                template.font_size = st.slider("Default Font Size", 5, 20, template.font_size)
                template.color = st.color_picker("Text Color", template.color)
        with col_right:
            st.subheader("Codes & Marks")
            template.include_qr = st.toggle("QR Code", value=template.include_qr)
            if template.include_qr:
                template.qr_size = st.slider("QR Size (mm)", 10, 40, template.qr_size)
                template.qr_x_offset = st.slider("QR Offset from Right (mm)", 0, 30, template.qr_x_offset)
                template.qr_y_offset = st.slider("QR Offset from Bottom (mm)", 0, 30, template.qr_y_offset)
            template.include_barcode = st.toggle("Barcode", value=template.include_barcode)
            if template.include_barcode:
                template.barcode_type = st.selectbox("Barcode Type", ["code128", "ean13", "upca"] if HAS_BARCODE else ["code128"])
            template.show_crop_marks = st.toggle("Show Crop Marks", value=template.show_crop_marks)
        st.session_state.current_template = template

    # ---------- TAB 3: AI AUTO‑DESIGN ----------
    with tab3:
        st.subheader("🤖 AI‑Powered Layout Suggestion")
        user_prompt = st.text_area("Describe your needs (optional)", placeholder="e.g., Long plant names need bigger font, use landscape")
        if st.button("✨ Generate AI Design", use_container_width=True):
            if not st.session_state.dataframe.empty:
                with st.spinner("Consulting DeepSeek AI..."):
                    suggested = AIDesigner.suggest_layout(st.session_state.dataframe, user_prompt)
                    st.session_state.current_template = suggested
                    st.success("AI design applied! Go to Label Designer to tweak.")
                    st.json(suggested.to_dict())
            else:
                st.warning("Load data first")
        st.info("🔌 DeepSeek API placeholder – integrate your key to get real AI layouts.")

    # ---------- TAB 4: OUTPUT & FORMAT ----------
    with tab4:
        st.subheader("Output Settings")
        template.output_format = st.selectbox("Print Format", ["A4_sheet", "continuous_roll", "ZPL"])
        if template.output_format == "continuous_roll":
            template.roll_width = st.number_input("Roll Width (mm)", value=template.roll_width)
            template.roll_gap = st.number_input("Gap Between Labels (mm)", value=template.roll_gap)
            st.info("Continuous roll PDF – no page breaks, just a long strip.")
        if template.output_format == "ZPL":
            st.info("ZPL code will be generated. Use with Zebra printers.")
        copies = st.number_input("Copies per item", value=1, min_value=1)
        st.session_state.copies = copies
        st.session_state.current_template = template

    # ---------- TAB 5: PREVIEW & EXPORT ----------
    with tab5:
        st.subheader("Preview & Generate")
        if st.session_state.dataframe.empty:
            st.warning("No data to print. Select data source first.")
            return

        # Duplicate rows for copies
        full_df = pd.concat([st.session_state.dataframe] * st.session_state.copies, ignore_index=True)
        engine = RenderEngine(template)

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Items", len(full_df))
        if template.output_format == "A4_sheet":
            pages = max(1, (len(full_df) + template.cols * template.rows - 1) // (template.cols * template.rows))
            col_b.metric("Pages (A4)", pages)
        else:
            col_b.metric("Format", template.output_format)

        # Live SVG preview
        if HAS_SVGWRITE:
            svg_str = engine.render_svg_preview(full_df, max_items=8)
            st.image(f"data:image/svg+xml;base64,{base64.b64encode(svg_str.encode()).decode()}", caption="SVG Preview", use_column_width=True)
        else:
            st.info("Install `svgwrite` for live preview.")

        # Generate buttons
        if st.button("🚀 Generate & Download", type="primary", use_container_width=True):
            with st.status("Rendering...", expanded=True) as status:
                if template.output_format == "A4_sheet":
                    buf = engine.render_pdf_a4_sheet(full_df)
                    mime = "application/pdf"
                    fname = "labels_a4.pdf"
                elif template.output_format == "continuous_roll":
                    buf = engine.render_pdf_continuous_roll(full_df)
                    mime = "application/pdf"
                    fname = "labels_roll.pdf"
                elif template.output_format == "ZPL":
                    zpl_code = engine.render_zpl(full_df)
                    buf = io.BytesIO(zpl_code.encode())
                    mime = "text/plain"
                    fname = "labels.zpl"
                else:
                    st.error("Unknown format")
                    return
                status.update(label="Ready!", state="complete")
                st.download_button("📥 Download", data=buf, file_name=fname, mime=mime, use_container_width=True)

# -----------------------------------------------------------------------------
# If you want to test standalone:
if __name__ == "__main__":
    render()
