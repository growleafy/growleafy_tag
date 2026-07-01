"""
AI Plant Health & Inventory Assistant – now with image diagnosis (OpenAI Vision)
"""
import streamlit as st
import pandas as pd
import requests
import json
import base64
from io import BytesIO
from PIL import Image

# ---------------------------------------------------------------------------
# Helper: Search inventory
# ---------------------------------------------------------------------------
def search_inventory(db, keyword: str):
    tables = [
        "plants", "agrochemicals", "pots_planters", "seeds",
        "garden_tools", "watering_tools", "garden_decor"
    ]
    results = {}
    kw = keyword.lower()
    for tbl in tables:
        try:
            rows = db.fetch_all(tbl)
            matches = []
            for row in rows:
                for val in row.values():
                    if isinstance(val, str) and kw in val.lower():
                        matches.append(row)
                        break
            if matches:
                results[tbl] = matches
        except:
            pass
    return results

def build_inventory_context(search_results: dict) -> str:
    context = []
    for tbl, rows in search_results.items():
        table_label = tbl.replace("_"," ").title()
        for row in rows:
            name = row.get('name', row.get('product_name',''))
            sku = row.get('sku','')
            mrp = row.get('mrp','')
            cat = row.get('category','')
            sub = row.get('subcategory','')
            desc = row.get('description','')[:100] if row.get('description') else ''
            line = f"[{table_label}] {name}"
            if sku: line += f" (SKU: {sku})"
            if cat: line += f" | Category: {cat}/{sub}" if sub else f" | Category: {cat}"
            if mrp: line += f" | Price: ₹{mrp}"
            if desc: line += f" | Description: {desc}"
            context.append(line)
    return "\n".join(context) if context else "No products found in inventory."

# ---------------------------------------------------------------------------
# DeepSeek text generation
# ---------------------------------------------------------------------------
def ask_deepseek(prompt: str, api_key: str):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a plant health expert. Diagnose plant problems, suggest possible causes with confidence levels, recommend ONLY products from the provided inventory list. Include dosage, safety precautions, and preventive measures. Format with clear sections."},
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
            return f"DeepSeek API error: {resp.status_code} – {resp.text}"
    except Exception as e:
        return f"Failed to reach DeepSeek API: {e}"

# ---------------------------------------------------------------------------
# OpenAI Vision call (for image analysis)
# ---------------------------------------------------------------------------
def analyze_image_with_openai(image_bytes: bytes, user_text: str, api_key: str) -> str:
    """Send image + optional text to GPT-4o, return diagnosis text."""
    # Resize image to reduce size (max 2048 px on longest side)
    img = Image.open(BytesIO(image_bytes))
    img.thumbnail((2048, 2048))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role": "system", "content": "You are a plant pathologist. Look at the image and describe any visible disease symptoms, pest damage, or nutrient deficiency. Provide a differential diagnosis with confidence levels. Then suggest possible treatments and preventive measures. If the image is not a plant or unclear, say so."}
    ]
    # If user also provided text, add it
    if user_text.strip():
        messages.append({"role": "user", "content": f"User description: {user_text}"})

    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze the plant image:"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]
    })

    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.5
    }
    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"OpenAI API error: {resp.status_code} – {resp.text}"
    except Exception as e:
        return f"Failed to reach OpenAI API: {e}"

# ---------------------------------------------------------------------------
# Fallback text-only analysis (no AI keys)
# ---------------------------------------------------------------------------
def fallback_analysis(user_query: str, inventory_context: str):
    query = user_query.lower()
    diagnosis = []
    products = []
    if "black spot" in query or "black spots" in query:
        diagnosis.append("🦠 **Black spot disease (Diplocarpon rosae)** – Confidence 90%")
        products.append("Fungicide containing chlorothalonil or neem oil")
    if "powder" in query or "white powder" in query:
        diagnosis.append("🌫️ **Powdery mildew** – Confidence 85%")
        products.append("Neem oil, potassium bicarbonate, or sulphur-based fungicide")
    if "curl" in query or "curling" in query:
        diagnosis.append("🍃 **Leaf curl (viral/fungal/insect damage)** – Confidence 70%")
        products.append("Copper oxychloride, neem oil, or appropriate insecticide")
    if "yellow" in query and "leaf" in query:
        diagnosis.append("🟡 **Nutrient deficiency (iron/magnesium/nitrogen)** – Confidence 65%")
        products.append("Balanced NPK fertilizer, micronutrient spray")
    if "aphid" in query or "aphids" in query:
        diagnosis.append("🐞 **Aphids** – Confidence 95%")
        products.append("Neem oil, insecticidal soap, or pyrethrin-based insecticide")
    if "mealybug" in query or "mealybugs" in query:
        diagnosis.append("🐛 **Mealybugs** – Confidence 95%")
        products.append("Neem oil, alcohol spray, or systemic insecticide")
    if not diagnosis:
        diagnosis.append("❓ **Unclear diagnosis** – I couldn't determine the exact issue. Please provide more details or consult a specialist.")
    reply = "**🔍 Plant Health Assessment**\n\n"
    reply += "\n".join(diagnosis) + "\n\n"
    if products:
        reply += "**🛒 Recommended Products (check inventory):**\n"
        reply += "\n".join(f"- {p}" for p in products) + "\n\n"
    reply += "**📦 Inventory Relevance:**\n"
    if inventory_context != "No products found in inventory.":
        reply += "The following items in your inventory may be useful:\n\n" + inventory_context + "\n"
    else:
        reply += "No matching products found in your inventory.\n"
    reply += "\n⚠️ *Please verify dosage on product labels. This is computer‑generated advice.*"
    return reply

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
def render(db):
    st.title("🌿 AI Plant Health & Inventory Assistant")
    st.caption("Describe symptoms or upload a photo. I'll diagnose and recommend products from your inventory.")

    # Check API keys
    deepseek_key = None
    openai_key = None
    try:
        deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
    except:
        pass
    try:
        openai_key = st.secrets["OPENAI_API_KEY"]
    except:
        pass

    # Show availability
    if not deepseek_key and not openai_key:
        st.info("💡 For detailed AI diagnoses, add `DEEPSEEK_API_KEY` or `OPENAI_API_KEY` in secrets.")
    if openai_key:
        st.success("📸 Image diagnosis is active (OpenAI Vision).")
    elif not openai_key:
        st.warning("📸 Image diagnosis is disabled. Add `OPENAI_API_KEY` to secrets to enable it.")

    # Chat history
    if "plant_chat" not in st.session_state:
        st.session_state.plant_chat = [
            {"role": "assistant", "content": "Hello! Describe your plant problem or upload an image. I'll search your inventory for solutions."}
        ]

    for msg in st.session_state.plant_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input area – we'll use a form to allow both text and image
    with st.form(key="chat_form", clear_on_submit=True):
        col_text, col_img = st.columns([3, 1])
        with col_text:
            user_text = st.text_input("Your message", placeholder="e.g., Rose leaves have black spots")
        with col_img:
            uploaded_image = st.file_uploader("📷 Upload image", type=["jpg","jpeg","png"], label_visibility="collapsed")
        submitted = st.form_submit_button("Send")

    if submitted:
        if not user_text and not uploaded_image:
            st.warning("Please enter a message or upload an image.")
        else:
            # Build user content for chat display
            display_msg = user_text if user_text else "Image uploaded"
            if uploaded_image:
                # Show image thumbnail in chat
                with st.chat_message("user"):
                    st.image(uploaded_image, caption="Uploaded image", width=200)
                    if user_text:
                        st.markdown(user_text)
                st.session_state.plant_chat.append({"role": "user", "content": display_msg})
            else:
                st.session_state.plant_chat.append({"role": "user", "content": user_text})
                with st.chat_message("user"):
                    st.markdown(user_text)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("Analyzing..."):
                    # --- Image analysis if available ---
                    if uploaded_image and openai_key:
                        # Use OpenAI Vision to get a diagnosis
                        diagnosis_text = analyze_image_with_openai(uploaded_image.read(), user_text, openai_key)
                        # Build query from diagnosis (combine user text + AI description)
                        combined_query = diagnosis_text + " " + user_text
                    else:
                        combined_query = user_text
                        if uploaded_image:
                            # No vision key – warn
                            st.warning("Image analysis requires an OpenAI API key. Only text will be used.")
                            combined_query = user_text  # fallback to text only

                    # --- Search inventory ---
                    search_results = search_inventory(db, combined_query)
                    # Expand search to product categories based on keywords in diagnosis
                    extra_terms = []
                    if "fungus" in combined_query.lower() or "mildew" in combined_query.lower() or "black spot" in combined_query.lower():
                        extra_terms.append("fungicide")
                    if "insect" in combined_query.lower() or "aphid" in combined_query.lower() or "mealy" in combined_query.lower():
                        extra_terms.append("insecticide")
                    if "deficiency" in combined_query.lower() or "yellow" in combined_query.lower():
                        extra_terms.append("fertilizer")
                        extra_terms.append("nutrient")
                    for term in extra_terms:
                        more = search_inventory(db, term)
                        for k,v in more.items():
                            if k in search_results:
                                search_results[k].extend(v)
                            else:
                                search_results[k] = v
                    # Deduplicate
                    for k in search_results:
                        seen = set()
                        unique = []
                        for row in search_results[k]:
                            uid = row.get('id', str(row))
                            if uid not in seen:
                                seen.add(uid)
                                unique.append(row)
                        search_results[k] = unique

                    inv_context = build_inventory_context(search_results)

                    # --- Generate final response ---
                    if deepseek_key:
                        full_prompt = f"""User question: "{combined_query}"
Inventory available (only recommend from this list):
{inv_context}

Please diagnose the plant issue, provide confidence levels, recommend specific products from the inventory (with dosage if applicable), safety precautions, and preventive measures."""
                        response = ask_deepseek(full_prompt, deepseek_key)
                    else:
                        response = fallback_analysis(combined_query, inv_context)

                    message_placeholder.markdown(response)
                    st.session_state.plant_chat.append({"role": "assistant", "content": response})

    # Clear chat
    if len(st.session_state.plant_chat) > 1:
        if st.button("🗑️ Clear Chat"):
            st.session_state.plant_chat = [
                {"role": "assistant", "content": "Chat cleared. How can I help?"}
            ]
            st.rerun()

    st.markdown("---")
    st.caption("🔑 Add `OPENAI_API_KEY` in secrets for image diagnosis, and `DEEPSEEK_API_KEY` for advanced text generation.")
