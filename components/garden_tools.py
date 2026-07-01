"""
Garden Tools Component – Cascading categories + Bulk Import
"""
import streamlit as st
import pandas as pd
import io

TABLE = "garden_tools"

TOOLS_HIERARCHY = {
    "Digging Tools": ["Spade", "Shovel", "Hoe", "Pickaxe"],
    "Hand Tools": ["Trowel", "Hand Fork", "Hand Cultivator", "Weeder"],
    "Pruning Tools": ["Secateurs", "Pruning Shears", "Loppers", "Hedge Shears", "Pruning Saw"],
    "Soil Tools": [],
    "Lawn Tools": [],
    "Harvesting Tools": [],
    "Measuring Tools": [],
    "Tool Sets": [],
    "Tool Accessories": []
}

def _category_selector(default=None):
    predefined = list(TOOLS_HIERARCHY.keys())
    options = predefined + ["Other"]
    if default and default in predefined:
        idx = options.index(default)
    elif default and default not in predefined:
        idx = options.index("Other")
    else:
        idx = 0
    choice = st.selectbox("Tool Type", options, index=idx)
    if choice == "Other":
        return st.text_input("Enter custom tool type", value=default if (default and default not in predefined) else "")
    return choice

def _subcategory_selector(category, default=None):
    if category in TOOLS_HIERARCHY and TOOLS_HIERARCHY[category]:
        subs = TOOLS_HIERARCHY[category]
        options = subs + ["Other"]
        if default and default in subs:
            idx = options.index(default)
        elif default and default not in subs:
            idx = options.index("Other")
        else:
            idx = 0
        choice = st.selectbox("Tool Subtype", options, index=idx)
        if choice == "Other":
            return st.text_input("Enter custom subtype", value=default if (default and default not in subs) else "")
        return choice
    else:
        return st.text_input("Tool Subtype", value=default if default else "")

def render(db):
    st.title("🛠 Garden Tools")
    st.caption("Manage garden tools with dynamic categories and bulk upload")
    tab1, tab2 = st.tabs(["📋 Inventory", "📤 Bulk Upload"])
    with tab1:
        _render_inventory(db)
    with tab2:
        _render_bulk_upload(db)

def _render_inventory(db):
    mode = st.radio("Action", ["View All", "Add New", "Edit / Delete"], key="tools_mode", horizontal=True)
    if mode == "View All":
        items = db.fetch_all(TABLE)
        if items:
            df = pd.DataFrame(items)
            st.dataframe(df, use_container_width=True)
            st.metric("Total Tools", len(items))
        else:
            st.info("No tools yet.")
    elif mode == "Add New":
        with st.form("add_tool"):
            name = st.text_input("Product Name *")
            category = _category_selector()
            subcategory = _subcategory_selector(category)
            sku = st.text_input("SKU")
            material = st.text_input("Material")
            blade_material = st.text_input("Blade Material")
            handle_material = st.text_input("Handle Material")
            length = st.text_input("Length (cm)")
            weight = st.text_input("Weight (g)")
            brand = st.text_input("Brand")
            warranty = st.text_input("Warranty")
            mrp = st.number_input("MRP (₹)", min_value=0.0, format="%.2f")
            stock = st.number_input("Stock", min_value=0, value=0)
            description = st.text_area("Description")
            if st.form_submit_button("💾 Save"):
                if not name:
                    st.error("Product name required.")
                else:
                    data = {
                        "name": name, "category": category, "subcategory": subcategory,
                        "sku": sku, "material": material, "blade_material": blade_material,
                        "handle_material": handle_material, "length": length, "weight": weight,
                        "brand": brand, "warranty": warranty, "mrp": mrp, "stock": stock,
                        "description": description
                    }
                    if db.insert_one(TABLE, data):
                        st.success("Tool added!")
                        st.rerun()
                    else:
                        st.error("Save failed.")
    elif mode == "Edit / Delete":
        all_items = db.fetch_all(TABLE)
        if not all_items:
            st.info("No items.")
            return
        df = pd.DataFrame(all_items)
        selected_id = st.selectbox("Select tool", df['id'],
                                   format_func=lambda x: f"{df[df['id']==x].iloc[0]['name']} (SKU: {df[df['id']==x].iloc[0].get('sku','')})")
        item = df[df['id'] == selected_id].iloc[0]
        with st.form("edit_tool"):
            name = st.text_input("Product Name", item.get('name',''))
            category = _category_selector(default=item.get('category',''))
            subcategory = _subcategory_selector(category, default=item.get('subcategory',''))
            sku = st.text_input("SKU", item.get('sku',''))
            material = st.text_input("Material", item.get('material',''))
            blade_material = st.text_input("Blade Material", item.get('blade_material',''))
            handle_material = st.text_input("Handle Material", item.get('handle_material',''))
            length = st.text_input("Length", item.get('length',''))
            weight = st.text_input("Weight", item.get('weight',''))
            brand = st.text_input("Brand", item.get('brand',''))
            warranty = st.text_input("Warranty", item.get('warranty',''))
            mrp = st.number_input("MRP", value=float(item.get('mrp',0)), min_value=0.0, format="%.2f")
            stock = st.number_input("Stock", value=int(item.get('stock',0)), min_value=0)
            description = st.text_area("Description", item.get('description',''))
            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Update"):
                    data = {
                        "name": name, "category": category, "subcategory": subcategory,
                        "sku": sku, "material": material, "blade_material": blade_material,
                        "handle_material": handle_material, "length": length, "weight": weight,
                        "brand": brand, "warranty": warranty, "mrp": mrp, "stock": stock,
                        "description": description
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
    st.subheader("📤 Bulk Import – Garden Tools")
    st.markdown("Download template, fill, and upload.")
    template_columns = [
        "name", "category", "subcategory", "sku", "material", "blade_material",
        "handle_material", "length", "weight", "brand", "warranty", "mrp", "stock", "description"
    ]
    template_df = pd.DataFrame(columns=template_columns)
    template_df.loc[0] = [
        "Heavy Duty Spade", "Digging Tools", "Spade", "SP-01", "Steel", "N/A", "Wood",
        "110 cm", "1.5 kg", "FarmPro", "2 years", 850.00, 50, "Durable spade for tough soil"
    ]
    csv_buffer = io.StringIO()
    template_df.to_csv(csv_buffer, index=False)
    st.download_button("📥 Download CSV Template", data=csv_buffer.getvalue(),
                       file_name="garden_tools_template.csv", mime="text/csv")
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
                df['stock'] = pd.to_numeric(df['stock'], errors='coerce').fillna(0).astype(int)
                for col in template_columns:
                    if col not in ['mrp','stock']:
                        df[col] = df[col].fillna('')
                st.success(f"Valid CSV – {len(df)} rows.")
                st.dataframe(df.head(10))
                if st.button("🚀 Upload All", type="primary"):
                    if db.insert_many(TABLE, df.to_dict(orient="records")):
                        st.success(f"✅ Added {len(df)} tools!")
                        st.balloons()
                    else:
                        st.error("Bulk insert failed.")
        except Exception as e:
            st.error(f"Error: {e}")
