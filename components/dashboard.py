"""
AI Plant Health & Inventory Assistant
Diagnoses plant issues, searches inventory, recommends treatments.
"""
import streamlit as st
import pandas as pd
import requests
import json

# ---------------------------------------------------------------------------
# Helper: Search all product tables for keywords (returns dict by table)
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

# ---------------------------------------------------------------------------
# Build a compact inventory summary string for the AI prompt
# ---------------------------------------------------------------------------
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
            # Build a line item
            line = f"[{table_label}] {name}"
            if sku: line += f" (SKU: {sku})"
            if cat: line += f" | Category: {cat}/{sub}" if sub else f" | Category: {cat}"
            if mrp: line += f" | Price: ₹{mrp}"
            if desc: line += f" | Description: {desc}"
            context.append(line)
    return "\n".join(context) if context else "No products found in inventory."

# ---------------------------------------------------------------------------
# DeepSeek API call (if key present)
# ---------------------------------------------------------------------------
def ask_deepseek(prompt: str, api_key: str):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a plant health expert. You help nursery staff by diagnosing plant problems, suggesting possible causes with confidence levels, and recommending products ONLY from the provided inventory list. Always include dosage information if known. Never recommend items not in the list. Format your answer clearly with sections: Diagnosis (with confidence %), Product Recommendations, Dosage, Safety Precautions, Preventive Measures."},
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
# Fallback expert system (rule‑based with inventory lookup)
# ---------------------------------------------------------------------------
def fallback_analysis(user_query: str, inventory_context: str):
    """Simple keyword matching when AI is not available."""
    query = user_query.lower()
    diagnosis = []
    products = []
    # Basic rules
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
    # Cross‑reference with inventory
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
# Main Streamlit UI
# ---------------------------------------------------------------------------
def render(db):
    st.title("🌿 AI Plant Health & Inventory Assistant")
    st.caption("Describe your plant problem – I’ll diagnose and recommend products from your inventory.")

    # API key check
    deepseek_key = None
    try:
        deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
    except:
        pass

    # Chat history
    if "plant_chat" not in st.session_state:
        st.session_state.plant_chat = [
            {"role": "assistant", "content": "Hello! I can help diagnose plant issues and suggest products from your inventory. Try: *\"Rose leaves have black spots\"* or *\"What organic fungicide do you have?\"*"}
        ]

    # Display chat
    for msg in st.session_state.plant_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Describe the problem..."):
        st.session_state.plant_chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Analyzing symptoms and searching inventory..."):
                # 1. Search inventory for keywords
                search_results = search_inventory(db, prompt)
                # Also search for broader terms (extract likely product types)
                extra_terms = []
                if "fungus" in prompt.lower() or "black spot" in prompt.lower():
                    extra_terms.append("fungicide")
                if "insect" in prompt.lower() or "aphid" in prompt.lower() or "mealy" in prompt.lower():
                    extra_terms.append("insecticide")
                if "deficiency" in prompt.lower() or "yellow" in prompt.lower():
                    extra_terms.append("fertilizer")
                    extra_terms.append("nutrient")
                for term in extra_terms:
                    more = search_inventory(db, term)
                    for k,v in more.items():
                        if k in search_results:
                            search_results[k].extend(v)
                        else:
                            search_results[k] = v
                # Remove duplicates
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

                # 2. Build prompt for AI (or fallback)
                if deepseek_key:
                    # Prepare expert prompt
                    full_prompt = f"""User question: "{prompt}"
Inventory available (only recommend from this list):
{inv_context}

Please diagnose the likely plant problem, provide confidence levels, recommend specific products from the inventory (with dosage if applicable), safety precautions, and preventive measures. Keep it concise."""
                    response = ask_deepseek(full_prompt, deepseek_key)
                else:
                    response = fallback_analysis(prompt, inv_context)

                message_placeholder.markdown(response)
                st.session_state.plant_chat.append({"role": "assistant", "content": response})

    # Clear chat button
    if len(st.session_state.plant_chat) > 1:
        if st.button("🗑️ Clear Chat"):
            st.session_state.plant_chat = [
                {"role": "assistant", "content": "Chat cleared. How can I help?"}
            ]
            st.rerun()

    st.markdown("---")
    st.caption("💡 **Tip:** For best results, add your DeepSeek API key in secrets (`DEEPSEEK_API_KEY`).")
