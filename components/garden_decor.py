"""
Garden Decor Component – Cascading categories + Bulk Import
"""
import streamlit as st
import pandas as pd
import io

TABLE = "garden_decor"

DECOR_HIERARCHY = {
    "Garden Statues": [],
    "Decorative Planters": [],
    "Plant Stands": [],
    "Hanging Baskets": [],
    "Garden Lights": [],
    "Solar Lights": [],
    "Bird Feeders": [],
    "Bird Baths": [],
    "Garden Fountains": [],
    "Wind Chimes": [],
    "Pebbles & Stones": [],
    "Garden Edging": [],
    "Trellises": [],
    "Arches": [],
    "Garden Benches": [],
    "Name Plates": [],
    "Decorative Fencing": [],
    "Wall Decor": [],
    "Artificial Grass": [],
    "Outdoor Decorative Items": []
}

def _category_selector(default=None):
    predefined = list(DECOR_HIERARCHY.keys())
    options = predefined + ["Other"]
    if default and default in predefined:
        idx = options.index(default)
    elif default and default not in predefined:
        idx = options.index("Other")
    else:
        idx = 0
    choice = st.selectbox("Decor Type", options, index=idx)
    if choice == "Other":
        return st.text_input("Enter custom type", value=default if (default and default not in predefined) else "")
    return choice

def _subcategory_selector(category, default=None):
    if category in DECOR_HIERARCHY and DECOR_HIERARCHY[category]:
        subs = DECOR_HIERARCHY[category]
        options = subs + ["Other"]
        if default and default in subs:
            idx = options.index(default)
        elif default and default not in subs:
            idx = options.index("Other")
        else:
            idx = 0
        choice = st.selectbox("Subtype", options, index=idx)
        if choice == "Other":
            return st.text_input("Enter custom subtype", value=default if (default and default not in subs) else "")
        return choice
    else:
        return st.text_input("Subtype", value=default if default else "")

def render(db):
    st.title("🏡 Garden Decor")
    st.caption("Manage decorative items with dynamic categories and bulk import")
    tab1, tab2 = st.tabs(["📋 Inventory", "📤 Bulk Upload"])
    with tab1:
        _render_inventory(db)
    with tab2:
        _render_bulk_upload(db)

def _render_inventory(db):
    mode = st.radio("Action", ["View All", "Add New", "Edit / Delete"], key="decor_mode", horizontal=True)
    if mode == "View All":
        items = db.fetch_all(TABLE)
        if items:
            df = pd.DataFrame(items)
            st.dataframe(df, use_container_width=True)
            st.metric("Total Decor Items", len(items))
        else:
            st.info("No items yet.")
    elif mode == "Add New":
        with st.form("add_decor"):
            name = st.text_input("Product Name *")
            category = _category_selector()
            subcategory = _subcategory_selector(category)
            sku = st.text_input("SKU")
            material = st.text_input("Material")
            color = st.text_input("Color")
            theme = st.text_input("Theme")
            location = st.selectbox("Indoor/Outdoor", ["Indoor", "Outdoor", "Both"])
            dimensions = st.text_input("Dimensions (cm)")
            weight = st.text_input("Weight (kg)")
            brand = st.text_input("Brand")
            mrp = st.number_input("MRP (₹)", min_value=0.0, format="%.2f")
            description = st.text_area("Description")
            if st.form_submit_button("💾 Save"):
                if not name:
                    st.error("Product name required.")
                else:
                    data = {
                        "name": name, "category": category, "subcategory": subcategory,
                        "sku": sku, "material": material, "color": color, "theme": theme,
                        "location": location, "dimensions": dimensions, "weight": weight,
                        "brand": brand, "mrp": mrp, "description": description
                    }
                    if db.insert_one(TABLE, data):
                        st.success("Added!")
                        st.rerun()
                    else:
                        st.error("Save failed.")
    elif mode == "Edit / Delete":
        all_items = db.fetch_all(TABLE)
        if not all_items:
            st.info("No items.")
            return
        df = pd.DataFrame(all_items)
        selected_id = st.selectbox("Select item", df['id'],
                                   format_func=lambda x: f"{df[df['id']==x].iloc[0]['name']} (SKU: {df[df['id']==x].iloc[0].get('sku','')})")
        item = df[df['id'] == selected_id].iloc[0]
        with st.form("edit_decor"):
            name = st.text_input("Product Name", item.get('name',''))
            category = _category_selector(default=item.get('category',''))
            subcategory = _subcategory_selector(category, default=item.get('subcategory',''))
            sku = st.text_input("SKU", item.get('sku',''))
            material = st.text_input("Material", item.get('material',''))
            color = st.text_input("Color", item.get('color',''))
            theme = st.text_input("Theme", item.get('theme',''))
            location = st.selectbox("Indoor/Outdoor", ["Indoor", "Outdoor", "Both"],
                                    index=["Indoor","Outdoor","Both"].index(item.get('location','Indoor')))
            dimensions = st.text_input("Dimensions", item.get('dimensions',''))
            weight = st.text_input("Weight", item.get('weight',''))
            brand = st.text_input("Brand", item.get('brand',''))
            mrp = st.number_input("MRP", value=float(item.get('mrp',0)), min_value=0.0, format="%.2f")
            description = st.text_area("Description", item.get('description',''))
            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Update"):
                    data = {
                        "name": name, "category": category, "subcategory": subcategory,
                        "sku": sku, "material": material, "color": color, "theme": theme,
                        "location": location, "dimensions": dimensions, "weight": weight,
                        "brand": brand, "mrp": mrp, "description": description
                    }
                    if db.update_one(TABLE, selected_id, data):
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
                        st.error("Failed to delete.")

def _render_bulk_upload(db):
    st.subheader("📤 Bulk Import – Garden Decor")
    template_columns = [
        "name", "category", "subcategory", "sku", "material", "color", "theme",
        "location", "dimensions", "weight", "brand", "mrp", "description"
    ]
    template_df = pd.DataFrame(columns=template_columns)
    template_df.loc[0] = [
        "Solar Lantern", "Garden Lights", "Solar Lights", "SL-01", "Metal", "Bronze",
        "Vintage", "Outdoor", "20x20x30 cm", "1.2 kg", "GreenGlow", 750.00,
        "Solar-powered hanging lantern"
    ]
    csv_buffer = io.StringIO()
    template_df.to_csv(csv_buffer, index=False)
    st.download_button("📥 Download CSV Template", data=csv_buffer.getvalue(),
                       file_name="garden_decor_template.csv", mime="text/csv")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, dtype=str)
            df.columns = df.columns.str.strip()
            missing = set(template_columns) - set(df.columns)
            if missing:
                st.error(f"Missing columns: {', '.join(missing)}")
            else:
                df['mrp'] = pd.to_numeric(df['mrp'], errors='coerce').fillna(0.0)
                for col in template_columns:
                    if col != 'mrp':
                        df[col] = df[col].fillna('')
                st.success(f"Valid CSV – {len(df)} rows.")
                st.dataframe(df.head(10))
                if st.button("🚀 Upload All", type="primary"):
                    if db.insert_many(TABLE, df.to_dict(orient="records")):
                        st.success(f"✅ Added {len(df)} items!")
                        st.balloons()
                    else:
                        st.error("Bulk insert failed.")
        except Exception as e:
            st.error(f"Error: {e}")
