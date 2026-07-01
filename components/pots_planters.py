"""
Pots & Planters Database Component
"""
import streamlit as st
import pandas as pd
from datetime import datetime

def render(db):
    st.title("🪴 Pots & Planters")
    st.caption("Manage your planter inventory with dynamic subcategories")

    TABLE = "pots_planters"
    fields_config = {
        'name': 'Product Name',
        'material': 'Material',
        'size': 'Size',
        'sku': 'SKU',
        'mrp': 'MRP (₹)',
        'description': 'Description',
        'subcategory': 'Subcategory'
    }

    # ---------- Helper: dynamic subcategory input ----------
    def subcategory_selector(db, existing_value=""):
        """Returns a subcategory value chosen by the user (existing or new)."""
        existing_subs = db.get_distinct_subcategories(TABLE)
        options = ["Select or type new..."] + existing_subs
        # If current value is in existing, preselect it; else show placeholder
        if existing_value in existing_subs:
            idx = options.index(existing_value)
        else:
            idx = 0
        selected = st.selectbox("Subcategory", options, index=idx,
                                help="Choose an existing subcategory or type a new one below.")
        if selected == "Select or type new...":
            new_sub = st.text_input("New subcategory", value="")
            return new_sub.strip() if new_sub.strip() else None
        return selected

    # ---------- Action: Add / Edit ----------
    mode = st.radio("Action", ["View All", "Add New", "Edit / Delete"], horizontal=True)

    if mode == "Add New":
        with st.form("add_pot"):
            name = st.text_input("Product Name *")
            material = st.text_input("Material")
            size = st.text_input("Size")
            sku = st.text_input("SKU")
            mrp = st.number_input("MRP (₹)", min_value=0.0, format="%.2f")
            description = st.text_area("Description")
            subcategory = subcategory_selector(db)
            submitted = st.form_submit_button("💾 Save")
            if submitted:
                if not name:
                    st.error("Product name is required.")
                else:
                    data = {
                        "name": name,
                        "material": material,
                        "size": size,
                        "sku": sku,
                        "mrp": mrp,
                        "description": description,
                        "subcategory": subcategory
                    }
                    res = db.insert_one(TABLE, data)
                    if res:
                        st.success("Pot / Planter added!")
                        st.rerun()
                    else:
                        st.error("Failed to save.")

    elif mode == "Edit / Delete":
        all_items = db.fetch_all(TABLE)
        if not all_items:
            st.info("No items found.")
        else:
            df = pd.DataFrame(all_items)
            selected_id = st.selectbox("Select item to edit/delete", df['id'],
                                       format_func=lambda x: f"{df[df['id']==x].iloc[0]['name']} (SKU: {df[df['id']==x].iloc[0].get('sku','')})")
            item = df[df['id'] == selected_id].iloc[0]
            with st.form("edit_pot"):
                name = st.text_input("Product Name", item.get('name',''))
                material = st.text_input("Material", item.get('material',''))
                size = st.text_input("Size", item.get('size',''))
                sku = st.text_input("SKU", item.get('sku',''))
                mrp = st.number_input("MRP", value=float(item.get('mrp',0)), min_value=0.0, format="%.2f")
                description = st.text_area("Description", item.get('description',''))
                # Subcategory
                current_sub = item.get('subcategory','')
                subcategory = subcategory_selector(db, current_sub)
                col_save, col_del = st.columns(2)
                with col_save:
                    if st.form_submit_button("💾 Update"):
                        data = {
                            "name": name,
                            "material": material,
                            "size": size,
                            "sku": sku,
                            "mrp": mrp,
                            "description": description,
                            "subcategory": subcategory
                        }
                        res = db.update_one(TABLE, selected_id, data)
                        if res:
                            st.success("Updated!")
                            st.rerun()
                        else:
                            st.error("Update failed.")
                with col_del:
                    if st.form_submit_button("🗑 Delete"):
                        if db.delete_one(TABLE, selected_id):
                            st.success("Deleted!")
                            st.rerun()
                        else:
                            st.error("Deletion failed.")

    else:  # View All
        items = db.fetch_all(TABLE)
        if items:
            df = pd.DataFrame(items)
            st.dataframe(df, use_container_width=True)
            st.metric("Total Pots & Planters", len(items))
        else:
            st.info("No items yet. Use 'Add New' to create one.")
