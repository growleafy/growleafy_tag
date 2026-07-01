"""
Dashboard Component – Unified statistics, recent items, and mini AI assistant
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import DatabaseManager

# ----------------------------------------------------------------------
# Mini chat helpers (same logic as the full AI assistant)
# ----------------------------------------------------------------------
def _search_all_tables(db, keyword: str):
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

def _build_fallback_reply(prompt: str, search_results: dict):
    if not search_results:
        return "I couldn't find any matching products in your inventory. Please try different keywords."
    reply_parts = ["Here are relevant items from your nursery:\n"]
    for tbl, rows in search_results.items():
        table_name = tbl.replace("_"," ").title()
        reply_parts.append(f"**{table_name}**:")
        for row in rows[:3]:
            name = row.get('name', row.get('product_name', 'Unknown'))
            sku = row.get('sku','')
            mrp = row.get('mrp','')
            line = f"- {name}"
            if sku:
                line += f" (SKU: {sku})"
            if mrp:
                line += f" – ₹{mrp:,.2f}"
            reply_parts.append(line)
        reply_parts.append("")
    reply_parts.append("You can explore these items in the respective database pages.")
    return "\n".join(reply_parts)

# ----------------------------------------------------------------------
# Main dashboard render
# ----------------------------------------------------------------------
def render(db: DatabaseManager):
    st.title("📊 Dashboard")
    st.markdown("---")

    # 1. Statistics
    stats = db.get_statistics()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🌱 Total Plants", stats['total_plants'])
    with col2:
        st.metric("🌾 Fertilizers", stats['total_fertilizers'])
    with col3:
        st.metric("🛡️ Plant Protection", stats['total_insecticides'])
    with col4:
        st.metric("🧪 Growth Regulators", stats['total_pesticides'])

    st.markdown("---")
    col5, col6 = st.columns(2)
    with col5:
        st.metric("🏷️ Printed Tags", stats['total_printed_tags'])
    with col6:
        total_items = (
            stats['total_plants']
            + stats['total_fertilizers']
            + stats['total_insecticides']
            + stats['total_pesticides']
        )
        st.metric("📦 Total Inventory Items", total_items)

    st.markdown("---")

    # 2. Quick search
    st.subheader("🔍 Quick Search")
    search_term = st.text_input("Search across all databases", placeholder="Enter name, SKU, brand...")
    if search_term:
        tables = [
            "plants", "agrochemicals", "pots_planters", "seeds",
            "garden_tools", "watering_tools", "garden_decor"
        ]
        results = {}
        total_found = 0
        for tbl in tables:
            try:
                rows = db.fetch_all(tbl)
                filtered = []
                for row in rows:
                    for val in row.values():
                        if isinstance(val, str) and search_term.lower() in val.lower():
                            filtered.append(row)
                            break
                if filtered:
                    results[tbl] = filtered
                    total_found += len(filtered)
            except Exception:
                pass
        st.info(f"Found {total_found} result(s) for '{search_term}'")
        for tbl, rows in results.items():
            st.subheader(f"📋 {tbl.replace('_',' ').title()}")
            df = pd.DataFrame(rows)
            st.dataframe(df.head(5), use_container_width=True)

    st.markdown("---")

    # 3. Recently added items
    st.subheader("🕒 Recently Added Items")
    tab_labels = [
        "Plants", "Agrochemicals", "Pots & Planters", "Seeds",
        "Garden Tools", "Watering Tools", "Garden Decor"
    ]
    table_map = {
        "Plants": "plants",
        "Agrochemicals": "agrochemicals",
        "Pots & Planters": "pots_planters",
        "Seeds": "seeds",
        "Garden Tools": "garden_tools",
        "Watering Tools": "watering_tools",
        "Garden Decor": "garden_decor"
    }
    tabs = st.tabs(tab_labels)
    for tab, label in zip(tabs, tab_labels):
        with tab:
            tbl = table_map[label]
            try:
                recent = db.get_recent_items(tbl, limit=5)
                if recent:
                    df = pd.DataFrame(recent)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info(f"No {label.lower()} added yet.")
            except Exception as e:
                st.warning(f"Could not load {label.lower()}: {e}")

    st.markdown("---")

    # 4. Mini AI Assistant (embedded)
    st.subheader("💬 Mini Assistant")
    st.caption("Ask a quick question about your inventory – I'll search your products.")

    # Initialize mini chat history
    if "dash_chat" not in st.session_state:
        st.session_state.dash_chat = [
            {"role": "assistant", "content": "Hi! Ask me something like 'organic fungicide' or 'rose care'."}
        ]

    # Display last N messages (keep it compact)
    with st.container(height=200):
        for msg in st.session_state.dash_chat[-6:]:  # show at most 6 messages
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Input area
    with st.form(key="dash_chat_form", clear_on_submit=True):
        user_input = st.text_input("Your message", key="dash_input", placeholder="e.g., best fertilizer for roses")
        send = st.form_submit_button("Send")
        if send and user_input:
            # Add user message
            st.session_state.dash_chat.append({"role": "user", "content": user_input})

            # Search and build reply
            results = _search_all_tables(db, user_input)
            reply = _build_fallback_reply(user_input, results)

            # Add assistant reply
            st.session_state.dash_chat.append({"role": "assistant", "content": reply})
            st.rerun()

    # Clear button
    if len(st.session_state.dash_chat) > 1:
        if st.button("Clear mini chat"):
            st.session_state.dash_chat = [
                {"role": "assistant", "content": "Hi! Ask me something like 'organic fungicide' or 'rose care'."}
            ]
            st.rerun()

    # Footer
    st.markdown("---")
    st.markdown(f"© {datetime.now().year} GrowLeafy | Version 1.0.0")
