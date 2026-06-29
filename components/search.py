"""
Advanced Search Component
"""
import streamlit as st
import pandas as pd

def render(db):
    st.title("🔍 Advanced Search")
    st.markdown("---")
    
    # Search Configuration
    with st.expander("⚙️ Search Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_query = st.text_input("Search Keyword", placeholder="e.g., Neem, Rose, NPK...")
        
        with col2:
            db_filter = st.multiselect(
                "Search In:",
                ["Plants", "Fertilizers", "Insecticides", "Pesticides"],
                default=["Plants", "Fertilizers", "Insecticides", "Pesticides"]
            )
            
        with col3:
            sort_by = st.selectbox("Sort Results By:", ["Relevance", "Price: Low to High", "Price: High to Low", "Recently Added"])

    st.markdown("---")
    
    # Execute Search
    if search_query:
        with st.spinner("Searching database..."):
            # Fetch results from DatabaseManager (assuming a universal_search method exists)
            results = db.universal_search(search_query)
            
            total_results = sum(len(results.get(key.lower(), [])) for key in db_filter)
            
            if total_results == 0:
                st.warning(f"No results found for '{search_query}' in the selected categories.")
            else:
                st.success(f"Found {total_results} matching items.")
                
                # Display Results based on filters
                for category in db_filter:
                    cat_key = category.lower()
                    if results.get(cat_key) and len(results[cat_key]) > 0:
                        st.subheader(f"{category} Results ({len(results[cat_key])})")
                        
                        df = pd.DataFrame(results[cat_key])
                        
                        # Apply sorting logic
                        if 'mrp' in df.columns:
                            if sort_by == "Price: Low to High":
                                df = df.sort_values('mrp', ascending=True)
                            elif sort_by == "Price: High to Low":
                                df = df.sort_values('mrp', ascending=False)
                                
                        # Display as an interactive dataframe
                        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("👆 Enter a keyword above to start searching your nursery inventory.")
