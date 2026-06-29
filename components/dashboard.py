"""
Dashboard Component
"""

import streamlit as st
from utils.database import DatabaseManager
import pandas as pd
from datetime import datetime

def render(db: DatabaseManager):
    """Render dashboard page"""
    
    st.title("📊 Dashboard")
    st.markdown("---")
    
    # Get statistics
    stats = db.get_statistics()
    
    # Display summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🌱 Total Plants",
            value=stats['total_plants'],
            delta=None
        )
    
    with col2:
        st.metric(
            label="🧪 Total Fertilizers",
            value=stats['total_fertilizers'],
            delta=None
        )
    
    with col3:
        st.metric(
            label="🐛 Total Insecticides",
            value=stats['total_insecticides'],
            delta=None
        )
    
    with col4:
        st.metric(
            label="🛡️ Total Pesticides",
            value=stats['total_pesticides'],
            delta=None
        )
    
    st.markdown("---")
    
    col5, col6 = st.columns(2)
    
    with col5:
        st.metric(
            label="🏷️ Total Printed Tags",
            value=stats['total_printed_tags'],
            delta=None
        )
    
    with col6:
        total_items = stats['total_plants'] + stats['total_fertilizers'] + \
                     stats['total_insecticides'] + stats['total_pesticides']
        st.metric(
            label="📦 Total Inventory Items",
            value=total_items,
            delta=None
        )
    
    st.markdown("---")
    
    # Global search bar
    st.subheader("🔍 Quick Search")
    search_term = st.text_input(
        "Search across all databases",
        placeholder="Enter plant name, product name, brand, category...",
        key="dashboard_search"
    )
    
    if search_term:
        results = db.universal_search(search_term)
        
        # Display results
        total_found = sum(len(v) for v in results.values())
        st.info(f"Found {total_found} results for '{search_term}'")
        
        if results['plants']:
            st.subheader("🌱 Plants")
            plants_df = pd.DataFrame(results['plants'])
            if not plants_df.empty:
                st.dataframe(
                    plants_df[['plant_name', 'botanical_name', 'category', 'mrp']].head(5),
                    use_container_width=True
                )
        
        if results['fertilizers']:
            st.subheader("🧪 Fertilizers")
            fert_df = pd.DataFrame(results['fertilizers'])
            if not fert_df.empty:
                st.dataframe(
                    fert_df[['product_name', 'brand', 'category', 'mrp']].head(5),
                    use_container_width=True
                )
        
        if results['insecticides']:
            st.subheader("🐛 Insecticides")
            insect_df = pd.DataFrame(results['insecticides'])
            if not insect_df.empty:
                st.dataframe(
                    insect_df[['product_name', 'brand', 'target_pest', 'mrp']].head(5),
                    use_container_width=True
                )
        
        if results['pesticides']:
            st.subheader("🛡️ Pesticides")
            pest_df = pd.DataFrame(results['pesticides'])
            if not pest_df.empty:
                st.dataframe(
                    pest_df[['product_name', 'brand', 'target_disease', 'mrp']].head(5),
                    use_container_width=True
                )
    
    st.markdown("---")
    
    # Recent items
    st.subheader("🕒 Recently Added Items")
    recent = db.get_recent_items(limit=5)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Plants", "Fertilizers", "Insecticides", "Pesticides"])
    
    with tab1:
        if recent['plants']:
            df = pd.DataFrame(recent['plants'])
            st.dataframe(
                df[['plant_name', 'category', 'created_at']],
                use_container_width=True
            )
        else:
            st.info("No plants added yet")
    
    with tab2:
        if recent['fertilizers']:
            df = pd.DataFrame(recent['fertilizers'])
            st.dataframe(
                df[['product_name', 'brand', 'created_at']],
                use_container_width=True
            )
        else:
            st.info("No fertilizers added yet")
    
    with tab3:
        if recent['insecticides']:
            df = pd.DataFrame(recent['insecticides'])
            st.dataframe(
                df[['product_name', 'brand', 'created_at']],
                use_container_width=True
            )
        else:
            st.info("No insecticides added yet")
    
    with tab4:
        if recent['pesticides']:
            df = pd.DataFrame(recent['pesticides'])
            st.dataframe(
                df[['product_name', 'brand', 'created_at']],
                use_container_width=True
            )
        else:
            st.info("No pesticides added yet")
    
    # Footer
    st.markdown("---")
    st.markdown(f"© {datetime.now().year} GrowLeafy | Version 1.0.0")
