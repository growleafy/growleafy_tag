"""
Seeds Component – Dynamic categories + Bulk Import
"""
import streamlit as st
import pandas as pd
import io

TABLE = "seeds"

# Pre-defined hierarchy
SEEDS_HIERARCHY = {
    "Vegetable Seeds": [
        "Leafy Vegetables", "Root Vegetables", "Fruiting Vegetables",
        "Legumes", "Exotic Vegetables"
    ],
    "Flower Seeds": [
        "Annual Flowers", "Perennial Flowers", "Wildflowers",
        "Cut Flowers", "Seasonal Flowers"
    ],
    "Herb Seeds": [
        "Culinary Herbs", "Medicinal Herbs", "Aromatic Herbs"
    ],
    "Fruit Seeds": [],
    "Tree Seeds": [],
    "Lawn Grass Seeds": [],
    "Microgreen Seeds": [],
    "Sprouting Seeds": [],
    "Bonsai Seeds": [],
    "Palm Seeds": [],
    "Cactus & Succulent Seeds": [],
    "Seed Kits": []
}

def _category_selector(default=None):
    predefined = list(SEEDS_HIERARCHY.keys())
    options = predefined + ["Other"]
    if default and default in predefined:
        idx = options.index(default)
    elif default and default not in predefined:
        idx = options.index("Other")
    else:
        idx = 0
    choice = st.selectbox("Seed Type", options, index=idx)
    if choice == "Other":
        return st.text_input("Enter custom seed type", value=default if (default and default not in predefined) else "")
    return choice

def _subcategory_selector(category, default=None):
    if category in SEEDS_HIERARCHY and SEEDS_HIERARCHY[category]:
        subs = SEEDS_HIERARCHY[category]
        options = subs + ["Other"]
        if default and default in subs:
            idx = options.index(default)
        elif default and default not in subs:
            idx = options.index("Other")
        else:
            idx = 0
        choice = st.selectbox("Variety / Subtype", options, index=idx)
        if choice == "Other":
            return st.text_input("Enter custom subtype", value=default if (default and default not in subs) else "")
        return choice
    else:
        return st.text_input("Variety / Subtype", value=default if default else "")

def render(db):
    st.title("🌱 Seeds")
    st.caption("Manage seed inventory with dynamic categories and bulk import")

    tab1, tab2 = st.tabs(["📋 Inventory", "📤 Bulk Upload"])

    with tab1:
        _render_inventory(db)
    with tab2:
        _render_bulk_upload(db)

def _render_inventory(db):
    mode = st.radio("Action", ["View All", "Add New", "Edit / Delete"], key="seeds_mode", horizontal=True)

    if mode == "View All":
        items = db.fetch_all(TABLE)
        if items:
            df = pd.DataFrame(items)
            st.dataframe(df, use_container_width=True)
            st.metric("Total Seeds", len(items))
        else:
            st.info("No seeds yet.")

    elif mode == "Add New":
        with st.form("add_seed"):
            name = st.text_input("Variety Name *")
            botanical_name = st.text_input("Botanical Name")
            category = _category_selector()
            subcategory = _subcategory_selector(category)
            sku = st.text_input("SKU")
            germination_rate = st.number_input("Germination Rate (%)", 0, 100, 80)
            germination_days = st.text_input("Germination Days (e.g., 7-14)")
            sowing_season = st.text_input("Sowing Season")
            harvest_days = st.text_input("Harvest Days")
            seed_count = st.text_input("Seed Count (e.g., 100)")
            pack_weight = st.text_input("Pack Weight (g/kg)")
            sunlight = st.selectbox("Sunlight", ["Full Sun", "Partial Shade", "Full Shade"])
            water = st.selectbox("Water Requirement", ["Low", "Medium", "High"])
            mrp = st.number_input("MRP (₹)", min_value=0.0, format="%.2f")
            description = st.text_area("Description")
            if st.form_submit_button("💾 Save"):
                if not name:
                    st.error("Variety name required.")
                else:
                    data = {
                        "name": name,
                        "botanical_name": botanical_name,
                        "category": category,
                        "subcategory": subcategory,
                        "sku": sku,
                        "germination_rate": germination_rate,
                        "germination_days": germination_days,
                        "sowing_season": sowing_season,
                        "harvest_days": harvest_days,
                        "seed_count": seed_count,
                        "pack_weight": pack_weight,
                        "sunlight": sunlight,
                        "water_requirement": water,
                        "mrp": mrp,
                        "description": description
                    }
                    if db.insert_one(TABLE, data):
                        st.success("Seed added!")
                        st.rerun()
                    else:
                        st.error("Failed to save.")

    elif mode == "Edit / Delete":
        all_items = db.fetch_all(TABLE)
        if not all_items:
            st.info("No items.")
            return
        df = pd.DataFrame(all_items)
        selected_id = st.selectbox("Select seed", df['id'],
                                   format_func=lambda x: f"{df[df['id']==x].iloc[0]['name']} (SKU: {df[df['id']==x].iloc[0].get('sku','')})")
        item = df[df['id'] == selected_id].iloc[0]
        with st.form("edit_seed"):
            name = st.text_input("Variety Name", item.get('name',''))
            botanical_name = st.text_input("Botanical Name", item.get('botanical_name',''))
            category = _category_selector(default=item.get('category',''))
            subcategory = _subcategory_selector(category, default=item.get('subcategory',''))
            sku = st.text_input("SKU", item.get('sku',''))
            germination_rate = st.number_input("Germination Rate (%)", 0, 100, int(item.get('germination_rate',80)))
            germination_days = st.text_input("Germination Days", item.get('germination_days',''))
            sowing_season = st.text_input("Sowing Season", item.get('sowing_season',''))
            harvest_days = st.text_input("Harvest Days", item.get('harvest_days',''))
            seed_count = st.text_input("Seed Count", item.get('seed_count',''))
            pack_weight = st.text_input("Pack Weight", item.get('pack_weight',''))
            sunlight = st.selectbox("Sunlight", ["Full Sun", "Partial Shade", "Full Shade"],
                                    index=["Full Sun", "Partial Shade", "Full Shade"].index(item.get('sunlight','Full Sun')))
            water = st.selectbox("Water Requirement", ["Low", "Medium", "High"],
                                 index=["Low","Medium","High"].index(item.get('water_requirement','Medium')))
            mrp = st.number_input("MRP", value=float(item.get('mrp',0)), min_value=0.0, format="%.2f")
            description = st.text_area("Description", item.get('description',''))
            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Update"):
                    data = {
                        "name": name, "botanical_name": botanical_name,
                        "category": category, "subcategory": subcategory,
                        "sku": sku, "germination_rate": germination_rate,
                        "germination_days": germination_days,
                        "sowing_season": sowing_season, "harvest_days": harvest_days,
                        "seed_count": seed_count, "pack_weight": pack_weight,
                        "sunlight": sunlight, "water_requirement": water,
                        "mrp": mrp, "description": description
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
    st.subheader("📤 Bulk Import – Seeds")
    st.markdown("Download the CSV template, fill, and upload. Existing data is preserved.")

    template_columns = [
        "name", "botanical_name", "category", "subcategory", "sku",
        "germination_rate", "germination_days", "sowing_season", "harvest_days",
        "seed_count", "pack_weight", "sunlight", "water_requirement", "mrp", "description"
    ]
    template_df = pd.DataFrame(columns=template_columns)
    template_df.loc[0] = [
        "Tomato Cherry", "Solanum lycopersicum", "Vegetable Seeds", "Fruiting Vegetables",
        "TOM-CH-01", 90, "5-10", "Spring-Summer", "60-70", "100", "5g",
        "Full Sun", "Medium", 120.00, "Sweet cherry tomato, high yield"
    ]
    csv_buffer = io.StringIO()
    template_df.to_csv(csv_buffer, index=False)
    st.download_button("📥 Download CSV Template", data=csv_buffer.getvalue(),
                       file_name="seeds_template.csv", mime="text/csv")

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload your filled CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, dtype=str)
            df.columns = df.columns.str.strip()
            missing = set(template_columns) - set(df.columns)
            if missing:
                st.error(f"Missing columns: {', '.join(missing)}")
            else:
                df['mrp'] = pd.to_numeric(df['mrp'], errors='coerce').fillna(0.0)
                df['germination_rate'] = pd.to_numeric(df['germination_rate'], errors='coerce').fillna(80)
                for col in template_columns:
                    if col not in ['mrp','germination_rate']:
                        df[col] = df[col].fillna('')
                st.success(f"Valid CSV – {len(df)} rows.")
                st.dataframe(df.head(10), use_container_width=True)
                if st.button("🚀 Upload All to Database", type="primary"):
                    if db.insert_many(TABLE, df.to_dict(orient="records")):
                        st.success(f"✅ Added {len(df)} seeds!")
                        st.balloons()
                    else:
                        st.error("Bulk insert failed.")
        except Exception as e:
            st.error(f"Error: {e}")
