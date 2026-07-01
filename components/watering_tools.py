"""
Watering Tools Component – Cascading categories + Bulk Import
"""
import streamlit as st
import pandas as pd
import io

TABLE = "watering_tools"

WATERING_HIERARCHY = {
    "Watering Cans": [],
    "Garden Hoses": [],
    "Hose Reels": [],
    "Spray Guns": [],
    "Spray Nozzles": [],
    "Hand Sprayers": [],
    "Pressure Sprayers": [],
    "Battery Sprayers": [],
    "Knapsack Sprayers": [],
    "Drip Irrigation Kits": [],
    "Drippers": [],
    "Sprinklers": [],
    "Mist Systems": [],
    "Hose Connectors": [],
    "Timers": [],
    "Water Pumps": [],
    "Irrigation Accessories": []
}

def _category_selector(default=None):
    predefined = list(WATERING_HIERARCHY.keys())
    options = predefined + ["Other"]
    if default and default in predefined:
        idx = options.index(default)
    elif default and default not in predefined:
        idx = options.index("Other")
    else:
        idx = 0
    choice = st.selectbox("Tool Type", options, index=idx)
    if choice == "Other":
        return st.text_input("Enter custom type", value=default if (default and default not in predefined) else "")
    return choice

def _subcategory_selector(category, default=None):
    # Watering tools typically have no deep subcategories, but we can still allow custom
    if category in WATERING_HIERARCHY and WATERING_HIERARCHY[category]:
        subs = WATERING_HIERARCHY[category]
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
    st.title("💧 Watering Tools")
    st.caption("Manage watering & irrigation equipment")
    tab1, tab2 = st.tabs(["📋 Inventory", "📤 Bulk Upload"])
    with tab1:
        _render_inventory(db)
    with tab2:
        _render_bulk_upload(db)

def _render_inventory(db):
    mode = st.radio("Action", ["View All", "Add New", "Edit / Delete"], key="water_mode", horizontal=True)
    if mode == "View All":
        items = db.fetch_all(TABLE)
        if items:
            df = pd.DataFrame(items)
            st.dataframe(df, use_container_width=True)
            st.metric("Total Items", len(items))
        else:
            st.info("No items yet.")
    elif mode == "Add New":
        with st.form("add_watering"):
            name = st.text_input("Product Name *")
            category = _category_selector()
            subcategory = _subcategory_selector(category)
            sku = st.text_input("SKU")
            capacity = st.text_input("Capacity (L)")
            pressure_rating = st.text_input("Pressure Rating")
            material = st.text_input("Material")
            hose_length = st.text_input("Hose Length (m)")
            spray_pattern = st.text_input("Spray Pattern")
            power_source = st.selectbox("Power Source", ["Manual", "Battery", "Electric", "Other"])
            flow_rate = st.text_input("Flow Rate")
            mrp = st.number_input("MRP (₹)", min_value=0.0, format="%.2f")
            description = st.text_area("Description")
            if st.form_submit_button("💾 Save"):
                if not name:
                    st.error("Product name required.")
                else:
                    data = {
                        "name": name, "category": category, "subcategory": subcategory,
                        "sku": sku, "capacity": capacity, "pressure_rating": pressure_rating,
                        "material": material, "hose_length": hose_length,
                        "spray_pattern": spray_pattern, "power_source": power_source,
                        "flow_rate": flow_rate, "mrp": mrp, "description": description
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
        with st.form("edit_watering"):
            name = st.text_input("Product Name", item.get('name',''))
            category = _category_selector(default=item.get('category',''))
            subcategory = _subcategory_selector(category, default=item.get('subcategory',''))
            sku = st.text_input("SKU", item.get('sku',''))
            capacity = st.text_input("Capacity", item.get('capacity',''))
            pressure_rating = st.text_input("Pressure Rating", item.get('pressure_rating',''))
            material = st.text_input("Material", item.get('material',''))
            hose_length = st.text_input("Hose Length", item.get('hose_length',''))
            spray_pattern = st.text_input("Spray Pattern", item.get('spray_pattern',''))
            power_source = st.selectbox("Power Source", ["Manual", "Battery", "Electric", "Other"],
                                        index=["Manual","Battery","Electric","Other"].index(item.get('power_source','Manual')))
            flow_rate = st.text_input("Flow Rate", item.get('flow_rate',''))
            mrp = st.number_input("MRP", value=float(item.get('mrp',0)), min_value=0.0, format="%.2f")
            description = st.text_area("Description", item.get('description',''))
            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Update"):
                    data = {
                        "name": name, "category": category, "subcategory": subcategory,
                        "sku": sku, "capacity": capacity, "pressure_rating": pressure_rating,
                        "material": material, "hose_length": hose_length,
                        "spray_pattern": spray_pattern, "power_source": power_source,
                        "flow_rate": flow_rate, "mrp": mrp, "description": description
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
    st.subheader("📤 Bulk Import – Watering Tools")
    template_columns = [
        "name", "category", "subcategory", "sku", "capacity", "pressure_rating",
        "material", "hose_length", "spray_pattern", "power_source", "flow_rate", "mrp", "description"
    ]
    template_df = pd.DataFrame(columns=template_columns)
    template_df.loc[0] = [
        "5L Pressure Sprayer", "Pressure Sprayers", "", "PS-05", "5L", "3 bar",
        "Plastic", "", "Adjustable", "Manual", "1L/min", 450.00, "Handheld pressure sprayer"
    ]
    csv_buffer = io.StringIO()
    template_df.to_csv(csv_buffer, index=False)
    st.download_button("📥 Download CSV Template", data=csv_buffer.getvalue(),
                       file_name="watering_tools_template.csv", mime="text/csv")
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
