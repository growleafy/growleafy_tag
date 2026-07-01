"""
Dashboard Component – Statistics, Recent Items, and a floating AI chat panel
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import DatabaseManager

# ---------------------------------------------------------------------------
# Mini‑chat helpers (plant health logic, same as full AI assistant)
# ---------------------------------------------------------------------------
def _search_inventory(db, keyword: str):
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

def _build_chat_reply(prompt: str, db):
    """Returns a short, inventory‑aware reply for the floating panel."""
    search_results = _search_inventory(db, prompt)
    if not search_results:
        return "No matching products found. Try a different term."
    reply = "Here are some products from your inventory:\n\n"
    for tbl, rows in search_results.items():
        table_label = tbl.replace("_"," ").title()
        reply += f"**{table_label}**\n"
        for row in rows[:2]:  # limit to keep panel tidy
            name = row.get('name', row.get('product_name',''))
            sku = row.get('sku','')
            mrp = row.get('mrp','')
            line = f"- {name}"
            if sku:
                line += f" (SKU: {sku})"
            if mrp:
                line += f" – ₹{mrp:,.2f}"
            reply += line + "\n"
        reply += "\n"
    reply += "Open the full **AI Assistant** page for a detailed diagnosis."
    return reply

# ---------------------------------------------------------------------------
# Main dashboard render
# ---------------------------------------------------------------------------
def render(db: DatabaseManager):
    # Top title remains full width
    st.title("📊 Dashboard")
    st.markdown("---")

    # Use columns to create main area + floating chat panel
    # Left: main content, Right: chat panel (width 350px)
    main_col, chat_col = st.columns([3, 1], gap="large")

    # ---------------- LEFT COLUMN (dashboard content) ------------------
    with main_col:
        # 1. Statistics cards
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

        # 2. Quick search (full width)
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
                except:
                    pass
            st.info(f"Found {total_found} result(s) for '{search_term}'")
            for tbl, rows in results.items():
                st.subheader(f"📋 {tbl.replace('_',' ').title()}")
                df = pd.DataFrame(rows)
                st.dataframe(df.head(5), use_container_width=True)

        st.markdown("---")

        # 3. Recently added items (tabs)
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

        # Footer
        st.markdown("---")
        st.markdown(f"© {datetime.now().year} GrowLeafy | Version 1.0.0")

    # ---------------- RIGHT COLUMN (floating chat panel) ----------------
    with chat_col:
        # Make the panel visually distinct
        with st.container():
            st.markdown("""
            <style>
            /* Force the right column to behave like a sticky panel */
            div[data-testid="column"]:nth-child(2) > div {
                position: sticky;
                top: 20px;
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown("### 💬 Quick AI Help")
            st.caption("Describe a plant problem – I'll search your inventory.")

            # Initialize chat history for the panel
            if "panel_chat" not in st.session_state:
                st.session_state.panel_chat = [
                    {"role": "assistant", "content": "Ask me anything! e.g. *\"black spots on rose\"*"}
                ]

            # Display previous messages (compact)
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.panel_chat[-8:]:  # keep only last 8
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            # Input area – a small form that submits without refreshing
            with st.form(key="panel_form", clear_on_submit=True):
                user_input = st.text_input("Your message", key="panel_input",
                                           placeholder="e.g., organic fungicide")
                send = st.form_submit_button("Send")
                if send and user_input:
                    # Add user message
                    st.session_state.panel_chat.append({"role": "user", "content": user_input})
                    # Build reply
                    reply = _build_chat_reply(user_input, db)
                    st.session_state.panel_chat.append({"role": "assistant", "content": reply})
                    st.rerun()

            # Clear button
            if len(st.session_state.panel_chat) > 1:
                if st.button("Clear chat", key="panel_clear"):
                    st.session_state.panel_chat = [
                        {"role": "assistant", "content": "Ask me anything! e.g. *\"black spots on rose\"*"}
                    ]
                    st.rerun()

            st.caption("🔗 Full **AI Assistant** available in sidebar.")
