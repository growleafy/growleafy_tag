"""
Reports & Analytics Component – Inventory health, financials, data export,
and Advanced Plant Health Diagnosis with PDF report generation.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import io, os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import requests, json, base64
from PIL import Image

# ---------------------------------------------------------------------------
# Helpers for inventory fetching (used across tabs)
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

def get_inventory_summary(db):
    """Fetch all products and return a dict {label: (df, total_value)}."""
    summary = {}
    for label, tbl in ALL_PRODUCT_TABLES.items():
        try:
            data = db.fetch_all(tbl)
            if data:
                df = pd.DataFrame(data)
                # calculate total value (MRP * stock if stock exists, else MRP)
                if "mrp" in df.columns:
                    if "stock" in df.columns:
                        # stock might be integer
                        df["stock"] = pd.to_numeric(df["stock"], errors='coerce').fillna(1)
                        value = (df["mrp"] * df["stock"]).sum()
                    else:
                        value = df["mrp"].sum()
                    summary[label] = (df, value)
                else:
                    summary[label] = (df, 0)
            else:
                summary[label] = (pd.DataFrame(), 0)
        except Exception as e:
            summary[label] = (pd.DataFrame(), 0)
    return summary

def search_inventory(db, keyword: str):
    """Search all product tables for a keyword."""
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
# Diagnosis helper (image + text)
# ---------------------------------------------------------------------------
def analyze_image_openai(image_bytes, user_text, api_key):
    """Use GPT-4o to analyze plant image."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((2048, 2048))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": "You are a plant pathologist. Describe disease symptoms, pest damage, or deficiencies visible in the image. Provide a differential diagnosis with confidence levels. Suggest treatments."}]
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

def diagnose_text_deepseek(prompt, api_key):
    """Use DeepSeek for diagnosis."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [
        {"role": "system", "content": "You are a plant health expert. Provide a differential diagnosis with confidence levels, then recommend treatments."},
        {"role": "user", "content": prompt}
    ], "temperature": 0.5, "max_tokens": 500}
    try:
        resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"DeepSeek API error: {resp.status_code}"
    except Exception as e:
        return f"API error: {e}"

def fallback_diagnosis(text, inventory_str):
    """Simple rule‑based diagnosis when no API keys are set."""
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

def generate_diagnosis_report(db, user_text, uploaded_image, openai_key, deepseek_key):
    """Runs the diagnosis and returns a dict with results and inventory matches."""
    # 1. Image analysis if available
    image_diag = ""
    if uploaded_image and openai_key:
        image_diag = analyze_image_openai(uploaded_image.read(), user_text, openai_key)
    # 2. Build combined query
    combined = (user_text + " " + image_diag).strip()
    # 3. Search inventory based on combined query
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
    # 4. Text diagnosis
    if deepseek_key and combined:
        diag_text = diagnose_text_deepseek(combined, deepseek_key)
    else:
        diag_text = fallback_diagnosis(combined, inv_str)
    # 5. Build full report
    report = f"## 🧪 Plant Health Diagnosis Report\n\n"
    report += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    if user_text:
        report += f"**Symptoms described:** {user_text}\n\n"
    if image_diag:
        report += f"**Image analysis:** {image_diag}\n\n"
    report += diag_text
    report += f"\n\n**🛒 Product Recommendations (from your inventory):**\n{inv_str}\n\n"
    report += "---\n*This report was generated by GrowLeafy. Please verify dosages on product labels.*"
    return {"report": report, "diagnosis": diag_text, "inventory": inv_str, "image_diag": image_diag}

def create_pdf_report(report_md):
    """Convert report markdown to a simple PDF."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    # Very basic: split lines and wrap
    p.setFont("Helvetica", 10)
    y = h - 30*mm
    for line in report_md.split('\n'):
        # Simple handling: skip markdown formatting for now
        clean = line.replace('#', '').replace('*', '')
        if clean.strip():
            p.drawString(20*mm, y, clean[:120])  # crude truncation
            y -= 5*mm
            if y < 20*mm:
                p.showPage()
                y = h - 30*mm
                p.setFont("Helvetica", 10)
    p.save()
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
def render(db):
    st.title("📈 Reports & Analytics")
    st.markdown("---")

    # Check API keys
    deepseek_key = st.secrets.get("DEEPSEEK_API_KEY", None)
    openai_key = st.secrets.get("OPENAI_API_KEY", None)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Inventory Health",
        "💰 Financial Overview",
        "📥 Export Data",
        "🔬 Advanced Plant Diagnosis"
    ])

    # ---------------- TAB 1: Inventory Health -----------------
    with tab1:
        st.subheader("Inventory Distribution")
        summary = get_inventory_summary(db)
        # Prepare pie chart
        cat_names = []
        cat_counts = []
        for label, (df, _) in summary.items():
            cat_names.append(label)
            cat_counts.append(len(df) if not df.empty else 0)
        if sum(cat_counts) > 0:
            pie_df = pd.DataFrame({"Category": cat_names, "Count": cat_counts})
            fig = px.pie(pie_df, values='Count', names='Category', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No inventory data to display.")

        # Low stock alert (if stock column exists in any table)
        st.subheader("⚠️ Low Stock Items")
        low_stock_items = []
        for label, tbl in ALL_PRODUCT_TABLES.items():
            try:
                data = db.fetch_all(tbl)
                for item in data:
                    if "stock" in item and item["stock"] is not None and item["stock"] <= 5:
                        name = item.get("name", item.get("product_name",""))
                        low_stock_items.append(f"{label}: {name} (Stock: {item['stock']})")
            except:
                pass
        if low_stock_items:
            for it in low_stock_items:
                st.warning(it)
        else:
            st.success("All items have adequate stock (or stock tracking not enabled).")

    # ---------------- TAB 2: Financial Overview -----------------
    with tab2:
        st.subheader("Estimated Inventory Value (MRP)")
        summary = get_inventory_summary(db)
        total_value = 0
        cols = st.columns(len(summary))
        for col, (label, (df, val)) in zip(cols, summary.items()):
            with col:
                st.metric(label, f"₹{val:,.2f}")
                total_value += val
        st.markdown("---")
        st.metric("**Total Inventory Retail Value**", f"₹{total_value:,.2f}")

    # ---------------- TAB 3: Export Data -----------------
    with tab3:
        st.subheader("Download Database Backups (CSV)")
        cols = st.columns(4)
        i = 0
        for label, tbl in ALL_PRODUCT_TABLES.items():
            try:
                data = db.fetch_all(tbl)
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False)
                with cols[i % 4]:
                    st.download_button(
                        f"📥 {label}",
                        data=csv,
                        file_name=f"{tbl}_export.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                i += 1
            except:
                with cols[i % 4]:
                    st.button(f"{label} (no data)", disabled=True)
                i += 1

    # ---------------- TAB 4: Advanced Plant Diagnosis -----------------
    with tab4:
        st.subheader("🔬 Plant Health Diagnosis & Report")
        st.markdown("Describe symptoms and/or upload an image. We'll diagnose the issue and search your inventory for solutions.")

        col1, col2 = st.columns([2, 1])
        with col1:
            user_text = st.text_area("Describe symptoms", placeholder="e.g., Rose leaves have black spots, curling")
        with col2:
            uploaded_image = st.file_uploader("Upload image (optional)", type=["jpg","jpeg","png"])
            if not openai_key:
                st.caption("⚠️ Image analysis requires OpenAI API key.")

        if st.button("🔍 Run Diagnosis", type="primary"):
            if not user_text and not uploaded_image:
                st.warning("Please provide text or image.")
            else:
                with st.spinner("Analyzing..."):
                    result = generate_diagnosis_report(db, user_text, uploaded_image, openai_key, deepseek_key)
                    st.session_state["diagnosis_report"] = result  # store for download

                st.success("Diagnosis complete!")
                st.markdown(result["report"])
                if st.download_button("📄 Download PDF Report",
                                      data=create_pdf_report(result["report"]),
                                      file_name=f"plant_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                      mime="application/pdf"):
                    st.success("Report downloaded!")
