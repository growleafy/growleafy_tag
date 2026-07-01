"""
Advanced Search Component – works with all current product tables
"""
import streamlit as st
import pandas as pd

# List all active product tables (add/remove as your inventory grows)
ALL_TABLES = {
    "Plants": "plants",
    "Agrochemicals": "agrochemicals",
    "Pots & Planters": "pots_planters",
    "Seeds": "seeds",
    "Garden Tools": "garden_tools",
    "Watering Tools": "watering_tools",
    "Garden Decor": "garden_decor"
}

def render(db):
    st.title("🔍 Advanced Search")
    st.markdown("---")

    # Search filters
    with st.expander("⚙️ Search Filters", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            search_query = st.text_input("Search Keyword", placeholder="e.g., Neem, Rose, NPK...")

        with col2:
            # Let user choose which tables to search
            selected_tables = st.multiselect(
                "Search In:",
                list(ALL_TABLES.keys()),
                default=["Plants", "Agrochemicals", "Pots & Planters"]
            )

        with col3:
            sort_by = st.selectbox(
                "Sort Results By:",
                ["Relevance", "Price: Low to High", "Price: High to Low", "Recently Added"]
            )

    st.markdown("---")

    if not search_query:
        st.info("👆 Enter a keyword above to start searching your nursery inventory.")
        return

    # Perform search
    with st.spinner("Searching database..."):
        total_found = 0
        results = {}

        for label in selected_tables:
            table_name = ALL_TABLES[label]
            try:
                rows = db.fetch_all(table_name)  # get all rows (safe – returns [])
                filtered = []
                for row in rows:
                    # Check all string values for the keyword
                    for val in row.values():
                        if isinstance(val, str) and search_query.lower() in val.lower():
                            filtered.append(row)
                            break
                if filtered:
                    results[label] = filtered
                    total_found += len(filtered)
            except Exception as e:
                # Table may not exist or some other error – skip gracefully
                pass

        if total_found == 0:
            st.warning(f"No results found for '{search_query}' in the selected categories.")
            return

        st.success(f"Found {total_found} matching item(s).")

        # Display results per category
        for label, rows in results.items():
            st.subheader(f"{label} ({len(rows)})")
            df = pd.DataFrame(rows)

            # Apply sorting
            if sort_by == "Price: Low to High" and "mrp" in df.columns:
                df = df.sort_values("mrp", ascending=True)
            elif sort_by == "Price: High to Low" and "mrp" in df.columns:
                df = df.sort_values("mrp", ascending=False)
            elif sort_by == "Recently Added" and "created_at" in df.columns:
                df = df.sort_values("created_at", ascending=False)

            st.dataframe(df, use_container_width=True, hide_index=True)
