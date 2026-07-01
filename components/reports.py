"""
Reports & Analytics Component – Inventory health, financials, data export,
and Advanced Plant Diagnosis with Indian language support.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import io, os, glob
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import requests, json, base64
from PIL import Image

# ---------------------------------------------------------------------------
# Table mapping
# ---------------------------------------------------------------------------
ALL_PRODUCT_TABLES = {
    "Plants": "plants",
    "Agrochemicals": "agrochemicals",
    "Pots & Planters": "pots_planters",
    "Seeds": "seeds",
    "Garden Tools": "garden_tools",
    "Watering Tools": "watering_tools",
    "Garden Decor": "garden_decor"
}

# Indian languages supported (as per user preference)
INDIAN_LANGUAGES = {
    "English": "en",
    "हिन्दी (Hindi)": "hi",
    "বাংলা (Bengali)": "bn",
    "తెలుగు (Telugu)": "te",
    "मराठी (Marathi)": "mr",
    "தமிழ் (Tamil)": "ta",
    "اردو (Urdu)": "ur",
    "ગુજરાતી (Gujarati)": "gu",
    "ಕನ್ನಡ (Kannada)": "kn",
    "ଓଡ଼ିଆ (Odia)": "or",
    "മലയാളം (Malayalam)": "ml",
    "ਪੰਜਾਬੀ (Punjabi)": "pa",
    "অসমীয়া (Assamese)": "as",
    "मैथिली (Maithili)": "mai"
}

# ---------------------------------------------------------------------------
# Inventory helpers
# ---------------------------------------------------------------------------
def get_inventory_summary(db):
    summary = {}
    for label, tbl in ALL_PRODUCT_TABLES.items():
        try:
            data = db.fetch_all(tbl)
            if data:
                df = pd.DataFrame(data)
                if "mrp" in df.columns:
                    if "stock" in df.columns:
                        df["stock"] = pd.to_numeric(df["stock"], errors='coerce').fillna(1)
                        value = (df["mrp"] * df["stock"]).sum()
                    else:
                        value = df["mrp"].sum()
                else:
                    value = 0
                summary[label] = (df, value)
            else:
                summary[label] = (pd.DataFrame(), 0)
        except:
            summary[label] = (pd.DataFrame(), 0)
    return summary

def search_inventory(db, keyword: str):
    results = {}
    kw = keyword.lower()
    for label, tbl in ALL_PRODUCT_TABLES.items():
        try:
            rows = db.fetch_all(tbl)
            matches = []
            for row in rows:
                for val in row.values():
                    if isinstance(val, str) and kw in val.lower():
                        matches.append(row)
                        break
            if matches:
                results[label] = matches
        except:
            pass
    return results

# ---------------------------------------------------------------------------
# AI / diagnosis helpers (language-aware)
# ---------------------------------------------------------------------------
def analyze_image_openai(image_bytes, user_text, api_key):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((2048, 2048))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": "You are a plant pathologist. Describe disease symptoms, pest damage, or deficiencies visible in the image. Provide a differential diagnosis with confidence levels."}]
        if user_text:
            messages.append({"role": "user", "content": f"User description: {user_text}"})
        messages.append({"role": "user", "content": [
            {"type": "text", "text": "Analyze the plant image:"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]})
        payload = {"model": "gpt-4o", "messages": messages, "max_tokens": 600, "temperature": 0.5}
        resp = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"OpenAI API error: {resp.status_code}"
    except Exception as e:
        return f"Image analysis failed: {e}"

def diagnose_text_deepseek(prompt, api_key, lang_code):
    """Generate diagnosis in the specified language."""
    lang_name = {v: k for k, v in INDIAN_LANGUAGES.items()}.get(lang_code, "English")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    system_msg = f"You are a plant health expert. Provide a differential diagnosis with confidence levels, then recommend treatments. Respond in {lang_name} language."
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 800
    }
    try:
        resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=20)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"DeepSeek API error: {resp.status_code}"
    except Exception as e:
        return f"API error: {e}"

def fallback_diagnosis(text, inventory_str, lang_code):
    """Basic rule‑based diagnosis (only English, with a note)."""
    if lang_code != "en":
        return f"⚠️ Offline diagnosis is only available in English. Please install an API key for {INDIAN_LANGUAGES.get(lang_code, 'other languages')}."
    text = text.lower()
    diagnoses = []
    if "black spot" in text:
        diagnoses.append("🦠 **Black spot** – Confidence 90% (Diplocarpon rosae)")
    if "powder" in text or "white" in text:
        diagnoses.append("🌫️ **Powdery mildew** – Confidence 85%")
    if "curl" in text:
        diagnoses.append("🍃 **Leaf curl** – Confidence 70% (viral/fungal/insect)")
    if "yellow" in text:
        diagnoses.append("🟡 **Nutrient deficiency** – Confidence 65%")
    if "aphid" in text:
        diagnoses.append("🐞 **Aphids** – Confidence 95%")
    if "mealybug" in text:
        diagnoses.append("🐛 **Mealybugs** – Confidence 95%")
    if not diagnoses:
        diagnoses.append("❓ **Unclear** – Please provide more details.")
    reply = "**🌿 Diagnosis:**\n" + "\n".join(diagnoses) + "\n\n"
    if inventory_str:
        reply += "**📦 Matching Inventory:**\n" + inventory_str
    return reply

def generate_diagnosis_report(db, user_text, uploaded_image, openai_key, deepseek_key, lang_code):
    # 1. Image analysis (always in English, we can translate later if needed)
    image_diag = ""
    if uploaded_image and openai_key:
        image_diag = analyze_image_openai(uploaded_image.read(), user_text, openai_key)
    # 2. Combine text
    combined = (user_text + " " + image_diag).strip()
    # 3. Search inventory (keyword matching, keep English for now)
    inv = search_inventory(db, combined)
    inv_lines = []
    for cat, rows in inv.items():
        for row in rows[:3]:
            name = row.get('name', row.get('product_name',''))
            sku = row.get('sku','')
            price = row.get('mrp','')
            line = f"- {name} (SKU: {sku}) – ₹{price}" if sku and price else f"- {name}"
            inv_lines.append(line)
    inv_str = "\n".join(inv_lines) if inv_lines else "No matching products found."
    # 4. Text diagnosis with language
    if deepseek_key and combined:
        # Include inventory context in prompt so AI can recommend products
        prompt = f"Question: {combined}\nInventory available (only recommend from this list):\n{inv_str}\nProvide diagnosis and treatment recommendations."
        diag_text = diagnose_text_deepseek(prompt, deepseek_key, lang_code)
    else:
        diag_text = fallback_diagnosis(combined, inv_str, lang_code)
    # 5. Build final report (language-aware heading)
    if lang_code != "en":
        # Translate fixed headings (basic mapping, AI handles the rest)
        heading_diag = "🔬 पादप स्वास्थ्य निदान रिपोर्ट" if lang_code == "hi" else "🔬 Plant Health Diagnosis Report"
        heading_date = "दिनांक:" if lang_code == "hi" else "Date:"
        heading_symptoms = "लक्षण:" if lang_code == "hi" else "Symptoms:"
        heading_products = "उत्पाद सिफ़ारिशें:" if lang_code == "hi" else "Product Recommendations:"
    else:
        heading_diag = "🔬 Plant Health Diagnosis Report"
        heading_date = "Date:"
        heading_symptoms = "Symptoms:"
        heading_products = "Product Recommendations:"

    report = f"## {heading_diag}\n\n"
    report += f"**{heading_date}** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    if user_text:
        report += f"**{heading_symptoms}** {user_text}\n\n"
    if image_diag:
        report += f"**Image analysis:** {image_diag}\n\n"
    report += diag_text + "\n\n"
    report += f"**🛒 {heading_products} (from your inventory):**\n{inv_str}\n\n"
    report += "---\n*This report was generated by GrowLeafy. Please verify dosages on product labels.*"
    return {"report": report, "diagnosis": diag_text, "inventory": inv_str, "image_diag": image_diag}

# ---------------------------------------------------------------------------
# PDF generation with Unicode font support for Indian languages
# ---------------------------------------------------------------------------
def _find_noto_font():
    """Try to locate a Noto Sans font on the system (covers many Indian scripts)."""
    search_paths = [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans*.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans*.ttf",
        "/usr/share/fonts/noto/*.ttf"
    ]
    for pattern in search_paths:
        matches = glob.glob(pattern)
        for match in matches:
            if "Regular" in match or "regular" in match.lower():
                return match
    return None

def create_pdf_report(report_md, lang_code):
    """Convert report to PDF, using a Unicode font if language != English."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    if lang_code != "en":
        font_path = _find_noto_font()
        if font_path:
            try:
                pdfmetrics.registerFont(TTFont("NotoSans", font_path))
                font_name = "NotoSans"
            except:
                font_name = "Helvetica"
        else:
            font_name = "Helvetica"
    else:
        font_name = "Helvetica"

    p.setFont(font_name, 10)
    y = h - 30*mm
    for line in report_md.split('\n'):
        clean = line.replace('#', '').replace('*', '')
        if clean.strip():
            # Wrap text manually (simple)
            while len(clean) > 120:
                p.drawString(20*mm, y, clean[:120])
                clean = clean[120:]
                y -= 5*mm
                if y < 20*mm:
                    p.showPage()
                    y = h - 30*mm
                    p.setFont(font_name, 10)
            p.drawString(20*mm, y, clean)
            y -= 5*mm
            if y < 20*mm:
                p.showPage()
                y = h - 30*mm
                p.setFont(font_name, 10)
    p.save()
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
def render(db):
    st.title("📈 Reports & Analytics")
    st.markdown("---")

    deepseek_key = st.secrets.get("DEEPSEEK_API_KEY", None)
    openai_key = st.secrets.get("OPENAI_API_KEY", None)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Inventory Health",
        "💰 Financial Overview",
        "📥 Export Data",
        "🔬 Advanced Plant Diagnosis"
    ])

    with tab1:
        st.subheader("Inventory Distribution")
        summary = get_inventory_summary(db)
        cat_names, cat_counts = [], []
        for label, (df, _) in summary.items():
            cat_names.append(label)
            cat_counts.append(len(df) if not df.empty else 0)
        if sum(cat_counts) > 0:
            fig = px.pie(pd.DataFrame({"Category": cat_names, "Count": cat_counts}),
                         values='Count', names='Category', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No inventory data.")

        st.subheader("⚠️ Low Stock Items")
        low_stock = []
        for label, tbl in ALL_PRODUCT_TABLES.items():
            try:
                data = db.fetch_all(tbl)
                for item in data:
                    if "stock" in item and isinstance(item["stock"], (int,float)) and item["stock"] <= 5:
                        name = item.get("name", item.get("product_name",""))
                        low_stock.append(f"{label}: {name} (Stock: {item['stock']})")
            except: pass
        if low_stock:
            for it in low_stock:
                st.warning(it)
        else:
            st.success("All items have adequate stock (or stock tracking not enabled).")

    with tab2:
        st.subheader("Estimated Inventory Value (MRP)")
        summary = get_inventory_summary(db)
        total_value = sum(v for _, (_, v) in summary.items())
        cols = st.columns(len(summary))
        for col, (label, (_, val)) in zip(cols, summary.items()):
            col.metric(label, f"₹{val:,.2f}")
        st.markdown("---")
        st.metric("**Total Inventory Retail Value**", f"₹{total_value:,.2f}")

    with tab3:
        st.subheader("Download Database Backups (CSV)")
        cols = st.columns(4)
        i = 0
        for label, tbl in ALL_PRODUCT_TABLES.items():
            try:
                df = pd.DataFrame(db.fetch_all(tbl))
                csv = df.to_csv(index=False)
                with cols[i % 4]:
                    st.download_button(f"📥 {label}", csv, f"{tbl}_export.csv", "text/csv", use_container_width=True)
                i += 1
            except:
                with cols[i % 4]:
                    st.button(f"{label} (no data)", disabled=True)
                i += 1

    with tab4:
        st.subheader("🔬 Plant Health Diagnosis & Report")
        st.markdown("Describe symptoms and/or upload an image, then choose your preferred language.")

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            user_text = st.text_area("Describe symptoms", placeholder="e.g., Rose leaves have black spots, curling")
        with col2:
            uploaded_image = st.file_uploader("Upload image (optional)", type=["jpg","jpeg","png"])
        with col3:
            selected_lang_label = st.selectbox("Report Language", list(INDIAN_LANGUAGES.keys()))
            lang_code = INDIAN_LANGUAGES[selected_lang_label]

        if st.button("🔍 Run Diagnosis", type="primary"):
            if not user_text and not uploaded_image:
                st.warning("Please provide text or image.")
            else:
                with st.spinner("Analyzing..."):
                    result = generate_diagnosis_report(
                        db, user_text, uploaded_image, openai_key, deepseek_key, lang_code
                    )
                    st.session_state["diag_report"] = result
                st.success("Diagnosis complete!")
                st.markdown(result["report"])
                # PDF download (language-aware)
                pdf_data = create_pdf_report(result["report"], lang_code)
                st.download_button(
                    "📄 Download PDF Report",
                    data=pdf_data,
                    file_name=f"plant_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )
