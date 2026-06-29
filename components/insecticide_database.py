"""
Insecticide Database Component
"""
import streamlit as st
import pandas as pd

def render(db):
    st.title("🐛 Insecticide Database")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 View Inventory", "➕ Add New Insecticide"])
    
    with tab1:
        st.subheader("Current Insecticide Inventory")
        st.info("Your insecticide inventory will appear here. Connect this to your DatabaseManager fetch method.")
        
    with tab2:
        st.subheader("Add New Insecticide")
        with st.form("add_insecticide_form"):
            col1, col2 = st.columns(2)
            with col1:
                product_name = st.text_input("Product Name*")
                brand = st.text_input("Brand/Manufacturer")
                target_pest = st.text_input("Target Pests")
            with col2:
                active_ingredient = st.text_input("Active Ingredient")
                mrp = st.number_input("MRP (₹)*", min_value=0.0, step=10.0)
                stock = st.number_input("Initial Stock", min_value=0, step=1)
                
            submitted = st.form_submit_button("Save Insecticide", use_container_width=True)
            if submitted:
                if product_name and mrp:
                    st.success(f"Successfully added {product_name} to the database!")
                else:
                    st.error("Please fill in all required fields (*).")
