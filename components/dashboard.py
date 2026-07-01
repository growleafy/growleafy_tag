"""
Dashboard Component – Unified statistics and recent items across all product tables
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import DatabaseManager

def render(db: DatabaseManager):
    st.title("📊 Dashboard")
    st.markdown("---")

    # 1. Statistics – from the updated get_statistics() (uses agrochemicals)
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
        # Sum all core product tables (approximation – add more if needed)
        total_items = (
            stats['total_plants']
            + stats['total_fertilizers']
            + stats['total_insecticides']
            + stats['total_pesticides']
        )
        st.metric("📦 Total Inventory Items", total_items)

    st.markdown("---")

    # 2. Quick search across all active tables
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
                # Table might not exist yet
                pass

        st.info(f"Found {total_found} result(s) for '{search_term}'")
        for tbl, rows in results.items():
            st.subheader(f"📋 {tbl.replace('_',' ').title()}")
            df = pd.DataFrame(rows)
            st.dataframe(df.head(5), use_container_width=True)

    st.markdown("---")

    # 3. Recently added items – tabs for each product table
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
