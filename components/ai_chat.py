"""
AI Botanical Assistant Component – database‑aware with optional DeepSeek LLM
"""
import streamlit as st
import time
import json
import os
import requests

# ----------------------------------------------------------------------
# Helper: Search all product tables for a keyword
# ----------------------------------------------------------------------
def search_all_tables(db, keyword: str):
    """Return a dict {table_name: [list_of_rows]} for rows matching keyword."""
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
        except Exception:
            pass
    return results

# ----------------------------------------------------------------------
# Fallback reply builder (no LLM)
# ----------------------------------------------------------------------
def build_fallback_reply(prompt: str, search_results: dict):
    """Construct a helpful reply from database search results."""
    if not search_results:
        return ("I couldn't find any matching products in your inventory. "
                "Please try different keywords or check the spelling.")

    reply_parts = ["I found these relevant items in your nursery database:\n"]
    for tbl, rows in search_results.items():
        table_name = tbl.replace("_"," ").title()
        reply_parts.append(f"**{table_name}**:")
        for row in rows[:3]:  # show max 3 per table
            name = row.get('name', row.get('product_name', 'Unknown'))
            sku = row.get('sku','')
            mrp = row.get('mrp','')
            line = f"- {name}"
            if sku:
                line += f" (SKU: {sku})"
            if mrp:
                line += f" – ₹{mrp:,.2f}"
            reply_parts.append(line)
        reply_parts.append("")  # blank line
    reply_parts.append("You can find them in the respective database pages.")
    return "\n".join(reply_parts)

# ----------------------------------------------------------------------
# Optional DeepSeek call
# ----------------------------------------------------------------------
def call_deepseek(prompt: str, search_results: dict, api_key: str) -> str:
    """Send context + prompt to DeepSeek and return the response."""
    # Build a context summary from search results
    context = "Inventory items:\n"
    for tbl, rows in search_results.items():
        for row in rows:
            name = row.get('name', row.get('product_name',''))
            cat = row.get('category','')
            sub = row.get('subcategory','')
            mrp = row.get('mrp','')
            context += f"- {name} (Category: {cat}/{sub}, MRP: ₹{mrp})\n"

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a botanical expert assistant. You help nursery staff answer customer questions. Use the provided inventory data when applicable. Keep answers concise and friendly."},
            {"role": "user", "content": f"Context from our inventory:\n{context}\n\nUser question: {prompt}\n\nProvide a helpful answer, mentioning specific products if relevant."}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post("https://api.deepseek.com/v1/chat/completions",
                             json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"DeepSeek API error: {resp.status_code}"
    except Exception as e:
        return f"Failed to reach DeepSeek API: {e}"

# ----------------------------------------------------------------------
# Main render
# ----------------------------------------------------------------------
def render(db):
    st.title("🤖 GrowLeafy AI Assistant")
    st.caption("Ask about plant care, pest control, or product recommendations — I’ll search your inventory.")

    # Try to get DeepSeek API key from secrets
    deepseek_key = None
    try:
        deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
    except KeyError:
        pass

    if not deepseek_key:
        st.info("💡 For advanced plant care advice, add your DeepSeek API key in Secrets (`DEEPSEEK_API_KEY`).")

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm your GrowLeafy botanical assistant. Ask me anything about plants, pests, or products in your inventory."}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("E.g., What organic fungicides do I have?"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate reply
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Searching inventory..."):
                # Step 1: search database
                results = search_all_tables(db, prompt)
                time.sleep(0.3)  # tiny pause for UX

                # Step 2: decide reply
                if deepseek_key:
                    try:
                        full_response = call_deepseek(prompt, results, deepseek_key)
                    except Exception:
                        full_response = build_fallback_reply(prompt, results)
                else:
                    full_response = build_fallback_reply(prompt, results)

                # Simulate streaming
                simulated = ""
                for word in full_response.split():
                    simulated += word + " "
                    time.sleep(0.03)
                    message_placeholder.markdown(simulated + "▌")
                message_placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Clear chat
    if len(st.session_state.messages) > 1:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Chat history cleared. How can I help you?"}
            ]
            st.rerun()
