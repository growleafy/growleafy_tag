"""
Dashboard Component – Product stats, Nursery Operations overview, and floating AI chat
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils.database import DatabaseManager

# ---------------------------------------------------------------------------
# Mini chat helpers (same as before)
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
    search_results = _search_inventory(db, prompt)
    if not search_results:
        return "No matching products found. Try a different term."
    reply = "Here are some products from your inventory:\n\n"
    for tbl, rows in search_results.items():
        table_label = tbl.replace("_"," ").title()
        reply += f"**{table_label}**\n"
        for row in rows[:2]:
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
# Main dashboard
# ---------------------------------------------------------------------------
def render(db: DatabaseManager):
    st.title("📊 Dashboard")
    st.markdown("---")

    # Use columns for main content + chat panel
    main_col, chat_col = st.columns([3, 1], gap="large")

    with main_col:
        # =================== PRODUCT STATISTICS ===================
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

        # =================== NURSERY OPERATIONS OVERVIEW ===================
        st.subheader("🌿 Nursery Operations Snapshot")

        # Fetch operations data (safe fallbacks)
        try:
            batches = db.fetch_all("plant_batches")
            total_batches = len(batches) if batches else 0
        except:
            total_batches = 0

        try:
            employees = db.fetch_all("employees")
            total_employees = len(employees) if employees else 0
        except:
            total_employees = 0

        try:
            tasks = db.fetch_all("scheduled_tasks")
            if tasks:
                df_tasks = pd.DataFrame(tasks)
                today_str = date.today().isoformat()
                tasks_today = len(df_tasks[df_tasks['scheduled_date'] == today_str])
                tasks_overdue = len(df_tasks[(df_tasks['status'] == 'pending') &
                                             (pd.to_datetime(df_tasks['scheduled_date']).dt.date < date.today())])
                tasks_completed = len(df_tasks[df_tasks['status'].isin(['completed','verified'])])
            else:
                tasks_today = tasks_overdue = tasks_completed = 0
        except:
            tasks_today = tasks_overdue = tasks_completed = 0

        try:
            attendance_records = db.fetch_all("attendance")
            if attendance_records:
                today_iso = date.today().isoformat()
                checked_in_today = sum(1 for r in attendance_records if r.get("check_in","")[:10] == today_iso)
            else:
                checked_in_today = 0
        except:
            checked_in_today = 0

        col7, col8, col9, col10 = st.columns(4)
        with col7:
            st.metric("🪴 Active Batches", total_batches)
        with col8:
            st.metric("📅 Tasks Today", tasks_today, delta=f"{tasks_overdue} overdue" if tasks_overdue else None)
        with col9:
            st.metric("👷 Employees", total_employees)
        with col10:
            st.metric("✅ Completed Tasks", tasks_completed)

        st.markdown("---")

        # =================== QUICK SEARCH ===================
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

        # =================== RECENTLY ADDED ITEMS ===================
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
        st.markdown(f"© {datetime.now().year} GrowLeafy | Version 1.0.0")

    # =================== FLOATING AI CHAT (right column) ===================
    with chat_col:
        with st.container():
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-child(2) > div {
                position: sticky;
                top: 20px;
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown("### 💬 Quick AI Help")
            st.caption("Describe a plant problem – I'll search your inventory.")

            if "panel_chat" not in st.session_state:
                st.session_state.panel_chat = [
                    {"role": "assistant", "content": "Ask me anything! e.g. *\"black spots on rose\"*"}
                ]

            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.panel_chat[-8:]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            with st.form(key="panel_form", clear_on_submit=True):
                user_input = st.text_input("Your message", key="panel_input",
                                           placeholder="e.g., organic fungicide")
                send = st.form_submit_button("Send")
                if send and user_input:
                    st.session_state.panel_chat.append({"role": "user", "content": user_input})
                    reply = _build_chat_reply(user_input, db)
                    st.session_state.panel_chat.append({"role": "assistant", "content": reply})
                    st.rerun()

            if len(st.session_state.panel_chat) > 1:
                if st.button("Clear chat", key="panel_clear"):
                    st.session_state.panel_chat = [
                        {"role": "assistant", "content": "Ask me anything! e.g. *\"black spots on rose\"*"}
                    ]
                    st.rerun()

            st.caption("🔗 Full **AI Assistant** available in sidebar.")
