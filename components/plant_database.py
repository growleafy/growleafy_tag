"""
Plant Database Component
"""
import streamlit as st
import pandas as pd

def render(db):
    st.title("🌱 Plant Database")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 View Inventory", "➕ Add New Plant"])
    
    with tab1:
        st.subheader("Current Plant Inventory")
        # Placeholder for your database fetch method
        # Example: plants = db.get_all_plants()
        st.info("Your plant inventory will appear here. Connect this to your DatabaseManager fetch method.")
        
    with tab2:
        st.subheader("Add New Plant")
        with st.form("add_plant_form"):
            col1, col2 = st.columns(2)
            with col1:
                plant_name = st.text_input("Common Name*")
                botanical_name = st.text_input("Botanical Name")
                category = st.selectbox("Category", ["Indoor", "Outdoor", "Succulent", "Herb", "Tree", "Other"])
            with col2:
                mrp = st.number_input("MRP (₹)*", min_value=0.0, step=10.0)
                stock = st.number_input("Initial Stock", min_value=0, step=1)
                location = st.text_input("Nursery Location/Batch")
                
            submitted = st.form_submit_button("Save Plant", use_container_width=True)
            if submitted:
                if plant_name and mrp:
                    # Example: db.add_plant(plant_name, botanical_name, category, mrp, stock)
                    st.success(f"Successfully added {plant_name} to the database!")
                else:
                    st.error("Please fill in all required fields (*).")
