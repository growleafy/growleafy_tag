"""
Dashboard Component – Safe, dynamic, and works with current DatabaseManager.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import DatabaseManager

def render(db: DatabaseManager):
    st.title("📊 Dashboard")
    st.markdown("---")

    # 1. Statistics cards (safe - already working)
    stats = db.get_statistics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🌱 Total Plants", stats['total_plants'])
    with col2:
        st.metric("🧪 Total Fertilizers", stats['total_fertilizers'])
    with col3:
        st.metric("🐛 Total Insecticides", stats['total_insecticides'])
    with col4:
        st.metric("🛡️ Total Pesticides", stats['total_pesticides'])

    st.markdown("---")

    col5, col6 = st.columns(2)
    with col5:
        st.metric("🏷️ Total Printed Tags", stats['total_printed_tags'])
    with col6:
        total_items = (
            stats['total_plants']
            + stats['total_fertilizers']
            + stats['total_insecticides']
            + stats['total_pesticides']
        )
        st.metric("📦 Total Inventory Items", total_items)

    st.markdown("---")

    # 2. Quick search (manual across tables)
    st.subheader("🔍 Quick Search")
    search_term = st.text_input(
        "Search across all databases",
        placeholder="Enter plant name, product name, brand...",
        key="dashboard_search"
    )

    if search_term:
        # We'll search all tables that exist
        tables = ["plants", "fertilizers", "insecticides", "pesticides"]
        results = {}
        total_found = 0

        for tbl in tables:
            rows = db.fetch_all(tbl)  # returns list of dicts
            # Filter rows where any string field contains the search term
            filtered = []
            for row in rows:
                for val in row.values():
                    if isinstance(val, str) and search_term.lower() in val.lower():
                        filtered.append(row)
                        break
            results[tbl] = filtered
            total_found += len(filtered)

        st.info(f"Found {total_found} result(s) for '{search_term}'")

        for tbl, rows in results.items():
            if rows:
                st.subheader(f"📋 {tbl.capitalize()}")
                df = pd.DataFrame(rows)
                # Show first 5 results to keep dashboard clean
                st.dataframe(df.head(5), use_container_width=True)

    st.markdown("---")

    # 3. Recently added items
    st.subheader("🕒 Recently Added Items")

    tab_labels = ["Plants", "Fertilizers", "Insecticides", "Pesticides"]
    table_map = {
        "Plants": "plants",
        "Fertilizers": "fertilizers",
        "Insecticides": "insecticides",
        "Pesticides": "pesticides",
    }
    tabs = st.tabs(tab_labels)

    for tab, label in zip(tabs, tab_labels):
        with tab:
            tbl = table_map[label]
            try:
                recent = db.get_recent_items(tbl, limit=5)
                if recent:
                    df = pd.DataFrame(recent)
                    # Show all columns except maybe long blobs
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info(f"No {label.lower()} added yet.")
            except Exception as e:
                st.warning(f"Could not load {label.lower()}: {e}")

    # Footer
    st.markdown("---")
    st.markdown(f"© {datetime.now().year} GrowLeafy | Version 1.0.0")
