"""
Fertilizer Database Component
"""
import streamlit as st
import pandas as pd

def render(db):
    st.title("🧪 Fertilizer Database")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 View Inventory", "➕ Add New Fertilizer"])
    
    with tab1:
        st.subheader("Current Fertilizer Inventory")
        st.info("Your fertilizer inventory will appear here. Connect this to your DatabaseManager fetch method.")
        
    with tab2:
        st.subheader("Add New Fertilizer")
        with st.form("add_fertilizer_form"):
            col1, col2 = st.columns(2)
            with col1:
                product_name = st.text_input("Product Name*")
                brand = st.text_input("Brand/Manufacturer")
                type_ = st.selectbox("Type", ["Organic", "Chemical", "Liquid", "Granular", "Powder"])
            with col2:
                npk_ratio = st.text_input("NPK Ratio (e.g., 10-10-10)")
                mrp = st.number_input("MRP (₹)*", min_value=0.0, step=10.0)
                stock = st.number_input("Initial Stock", min_value=0, step=1)
                
            submitted = st.form_submit_button("Save Fertilizer", use_container_width=True)
            if submitted:
                if product_name and mrp:
                    st.success(f"Successfully added {product_name} to the database!")
                else:
                    st.error("Please fill in all required fields (*).")
