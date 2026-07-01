"""
Agrochemicals Component – Fertilizers, Plant Protection, Growth Regulators + Bulk Import
"""
import streamlit as st
import pandas as pd
import io

TABLE = "agrochemicals"

# Pre-defined hierarchy for Fertilizers
FERILIZER_CATEGORIES = {
    "Organic Fertilizers": [
        "Farmyard Manure (FYM)", "Vermicompost", "Compost", "Cow Manure",
        "Poultry Manure", "Goat Manure", "Neem Cake", "Mustard Cake",
        "Bone Meal", "Horn Meal", "Blood Meal", "Fish Meal",
        "Seaweed Granules", "Organic Plant Food"
    ],
    "Chemical Fertilizers": [
        "Nitrogen (N)", "Phosphorus (P)", "Potassium (K)", "NPK Complex",
        "Urea", "DAP", "MOP", "SSP", "Ammonium Sulphate",
        "Calcium Nitrate", "Potassium Nitrate", "Magnesium Sulphate"
    ],
    "Water Soluble Fertilizers (WSF)": [
        "NPK 19:19:19", "NPK 20:20:20", "NPK 13:40:13", "NPK 00:52:34",
        "NPK 00:00:50", "NPK 12:61:00", "Specialty WSF"
    ],
    "Liquid Fertilizers": [
        "Liquid NPK", "Liquid Seaweed", "Humic Acid", "Fulvic Acid",
        "Amino Acid", "Fish Emulsion", "Liquid Organic Fertilizer"
    ],
    "Micronutrients": [
        "Zinc", "Boron", "Iron", "Copper", "Manganese",
        "Molybdenum", "Chelated Mix", "Silicon"
    ],
    "Secondary Nutrients": ["Calcium", "Magnesium", "Sulphur"],
    "Biofertilizers": [
        "Azospirillum", "Azotobacter", "Rhizobium", "PSB", "KSB",
        "VAM / Mycorrhiza", "Trichoderma"
    ],
    "Soil Conditioners": [
        "Humic Acid", "Fulvic Acid", "Biochar", "Gypsum",
        "Agricultural Lime", "Cocopeat", "Perlite", "Vermiculite"
    ],
    "Plant Biostimulants": [
        "Seaweed Extract", "Amino Acid", "Protein Hydrolysate",
        "Fulvic Acid", "Humic Acid", "Microbial Biostimulants",
        "Enzyme Formulations"
    ]
}

PROTECTION_CATEGORIES = [
    "Insecticide", "Fungicide", "Herbicide", "Miticides (Acaricides)",
    "Nematicides", "Rodenticides", "Molluscicides", "General Pesticide"
]

TYPE_MAP = {
    "Fertilizer": "🌾 Fertilizers & Nutrients",
    "Plant Protection": "🛡️ Plant Protection Products",
    "Growth Regulator": "🧪 Plant Growth Regulators"
}

# ----------------------------------------------------------------------
# Subcategory selector helpers
# ----------------------------------------------------------------------
def subcategory_selector(db, existing_sub=""):
    all_subs = db.get_distinct_subcategories(TABLE)
    options = ["Select or type new..."] + all_subs
    if existing_sub in all_subs:
        idx = options.index(existing_sub)
    else:
        idx = 0
    selected = st.selectbox("Subcategory", options, index=idx,
                            help="Choose existing or define a new one below.")
    if selected == "Select or type new...":
        new_sub = st.text_input("New subcategory", value="")
        return new_sub.strip() if new_sub.strip() else None
    return selected


def _fertilizer_category_selector(default=None):
    predefined = list(FERILIZER_CATEGORIES.keys())
    options = predefined + ["Other"]
    if default and default in predefined:
        idx = options.index(default)
    elif default and default not in predefined:
        idx = options.index("Other")
    else:
        idx = 0
    choice = st.selectbox("Major Category", options, index=idx)
    if choice == "Other":
        return st.text_input("Enter custom major category", value=default if (default and default not in predefined) else "")
    return choice


def _fertilizer_subcategory_selector(major_cat, default=None):
    if major_cat in FERILIZER_CATEGORIES:
        subs = FERILIZER_CATEGORIES[major_cat]
        options = subs + ["Other"]
        if default and default in subs:
            idx = options.index(default)
        elif default and default not in subs:
            idx = options.index("Other")
        else:
            idx = 0
        choice = st.selectbox("Subcategory", options, index=idx)
        if choice == "Other":
            return st.text_input("Enter custom subcategory", value=default if (default and default not in subs) else "")
        return choice
    else:
        return st.text_input("Subcategory", value=default if default else "")


# ----------------------------------------------------------------------
# Main render
# ----------------------------------------------------------------------
def render(db):
    st.title("🧪 Agrochemicals")
    st.caption("Fertilizers, Plant Protection & Growth Regulators – with bulk import")

    tab1, tab2, tab3, tab4 = st.tabs([
        TYPE_MAP["Fertilizer"],
        TYPE_MAP["Plant Protection"],
        TYPE_MAP["Growth Regulator"],
        "📤 Bulk Upload"
    ])

    with tab1:
        st.subheader("🌾 Fertilizers & Nutrients")
        _render_fertilizer_table(db)

    with tab2:
        st.subheader("🛡️ Plant Protection Products")
        _render_agro_generic(db, "Plant Protection")

    with tab3:
        st.subheader("🧪 Plant Growth Regulators")
        _render_agro_generic(db, "Growth Regulator")

    with tab4:
        _render_bulk_upload(db)


# ----------------------------------------------------------------------
# Fertilizer CRUD (as before)
# ----------------------------------------------------------------------
def _render_fertilizer_table(db):
    agro_type = "Fertilizer"
    mode = st.radio("Action", ["View All", "Add New", "Edit / Delete"], key="fert_mode", horizontal=True)

    if mode == "View All":
        all_items = db.fetch_all(TABLE)
        if all_items:
            df = pd.DataFrame(all_items)
            df = df[df['type'] == agro_type]
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.metric("Total Fertilizers", len(df))
            else:
                st.info("No fertilizers yet.")
        else:
            st.info("No data in table.")

    elif mode == "Add New":
        with st.form("add_fertilizer"):
            product_name = st.text_input("Product Name *")
            brand = st.text_input("Brand")
            sku = st.text_input("SKU")
            mrp = st.number_input("MRP (₹)", min_value=0.0, format="%.2f")
            description = st.text_area("Description")
            target_use = st.text_input("Target Use / Notes")
            major_cat = _fertilizer_category_selector()
            subcat = _fertilizer_subcategory_selector(major_cat)
            if st.form_submit_button("💾 Save"):
                if not product_name:
                    st.error("Product name is required.")
                else:
                    data = {
                        "product_name": product_name,
                        "type": agro_type,
                        "category": major_cat,
                        "subcategory": subcat,
                        "brand": brand,
                        "sku": sku,
                        "mrp": mrp,
                        "description": description,
                        "target_use": target_use
                    }
                    if db.insert_one(TABLE, data):
                        st.success("Fertilizer added!")
                        st.rerun()
                    else:
                        st.error("Failed to save.")

    elif mode == "Edit / Delete":
        all_items = db.fetch_all(TABLE)
        if not all_items:
            st.info("No items.")
            return
        df = pd.DataFrame(all_items)
        df = df[df['type'] == agro_type]
        if df.empty:
            st.info("No fertilizers yet.")
            return
        selected_id = st.selectbox("Select fertilizer", df['id'],
                                   format_func=lambda x: f"{df[df['id']==x].iloc[0]['product_name']} (SKU: {df[df['id']==x].iloc[0].get('sku','')})")
        item = df[df['id'] == selected_id].iloc[0]
        with st.form("edit_fertilizer"):
            product_name = st.text_input("Product Name", item.get('product_name',''))
            brand = st.text_input("Brand", item.get('brand',''))
            sku = st.text_input("SKU", item.get('sku',''))
            mrp = st.number_input("MRP", value=float(item.get('mrp',0)), min_value=0.0, format="%.2f")
            description = st.text_area("Description", item.get('description',''))
            target_use = st.text_input("Target Use / Notes", value=item.get('target_use',''))
            current_cat = item.get('category','')
            current_sub = item.get('subcategory','')
            major_cat = _fertilizer_category_selector(default=current_cat)
            subcat = _fertilizer_subcategory_selector(major_cat, default=current_sub)
            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Update"):
                    data = {
                        "product_name": product_name,
                        "type": agro_type,
                        "category": major_cat,
                        "subcategory": subcat,
                        "brand": brand,
                        "sku": sku,
                        "mrp": mrp,
                        "description": description,
                        "target_use": target_use
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


# ----------------------------------------------------------------------
# Generic CRUD for Plant Protection / Growth Regulators
# ----------------------------------------------------------------------
def _render_agro_generic(db, agro_type):
    mode = st.radio("Action", ["View All", "Add New", "Edit / Delete"], key=agro_type, horizontal=True)

    if mode == "View All":
        all_items = db.fetch_all(TABLE)
        df = pd.DataFrame(all_items) if all_items else pd.DataFrame()
        if not df.empty:
            df = df[df['type'] == agro_type]
            st.dataframe(df, use_container_width=True)
            st.metric(f"Total {agro_type}s", len(df))
        else:
            st.info("No items yet.")

    elif mode == "Add New":
        with st.form(f"add_{agro_type}"):
            product_name = st.text_input("Product Name *")
            brand = st.text_input("Brand")
            sku = st.text_input("SKU")
            mrp = st.number_input("MRP (₹)", min_value=0.0, format="%.2f")
            description = st.text_area("Description")

            if agro_type == "Plant Protection":
                category = st.selectbox("Category", PROTECTION_CATEGORIES)
            else:
                category = st.text_input("Category (e.g., Auxin, Gibberellin)")

            subcategory = subcategory_selector(db)

            if agro_type == "Plant Protection":
                target_use = st.text_input("Target Pest / Disease / Weed")
            else:
                target_use = st.text_input("Purpose (e.g., rooting, flowering)")

            if st.form_submit_button("💾 Save"):
                if not product_name:
                    st.error("Product name required.")
                else:
                    data = {
                        "product_name": product_name,
                        "type": agro_type,
                        "category": category,
                        "subcategory": subcategory,
                        "brand": brand,
                        "sku": sku,
                        "mrp": mrp,
                        "description": description,
                        "target_use": target_use
                    }
                    if db.insert_one(TABLE, data):
                        st.success("Added!")
                        st.rerun()
                    else:
                        st.error("Failed.")

    elif mode == "Edit / Delete":
        all_items = db.fetch_all(TABLE)
        if not all_items:
            st.info("No items.")
            return
        df = pd.DataFrame(all_items)
        df = df[df['type'] == agro_type]
        if df.empty:
            st.info(f"No {agro_type} items.")
            return
        selected_id = st.selectbox("Select item", df['id'],
                                   format_func=lambda x: f"{df[df['id']==x].iloc[0]['product_name']} (SKU: {df[df['id']==x].iloc[0].get('sku','')})")
        item = df[df['id'] == selected_id].iloc[0]

        with st.form(f"edit_{agro_type}"):
            product_name = st.text_input("Product Name", item.get('product_name',''))
            brand = st.text_input("Brand", item.get('brand',''))
            sku = st.text_input("SKU", item.get('sku',''))
            mrp = st.number_input("MRP", value=float(item.get('mrp',0)), min_value=0.0, format="%.2f")
            description = st.text_area("Description", item.get('description',''))

            if agro_type == "Plant Protection":
                current_cat = item.get('category','')
                cat_options = PROTECTION_CATEGORIES.copy()
                if current_cat and current_cat not in cat_options:
                    cat_options.append(current_cat)
                category = st.selectbox("Category", cat_options,
                                        index=cat_options.index(current_cat) if current_cat in cat_options else 0)
            else:
                category = st.text_input("Category", value=item.get('category',''))

            subcategory = subcategory_selector(db, item.get('subcategory',''))

            target_use = st.text_input("Target / Purpose", value=item.get('target_use',''))

            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Update"):
                    data = {
                        "product_name": product_name,
                        "type": agro_type,
                        "category": category,
                        "subcategory": subcategory,
                        "brand": brand,
                        "sku": sku,
                        "mrp": mrp,
                        "description": description,
                        "target_use": target_use
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


# ----------------------------------------------------------------------
# BULK UPLOAD TAB
# ----------------------------------------------------------------------
def _render_bulk_upload(db):
    st.subheader("📤 Bulk Import – Agrochemicals")
    st.markdown("Download the CSV template, fill in your products, and upload to add them all at once. "
                "**Existing records will not be affected.**")

    # 1. Template download
    template_columns = [
        "product_name", "type", "category", "subcategory", "brand",
        "target_use", "sku", "mrp", "description"
    ]
    template_df = pd.DataFrame(columns=template_columns)
    # Add one example row
    template_df.loc[0] = [
        "Organic Vermicompost",
        "Fertilizer",
        "Organic Fertilizers",
        "Vermicompost",
        "GreenGrow",
        "Soil enrichment",
        "ORG-VC-01",
        350.00,
        "Pure vermicompost for home gardens"
    ]
    template_df.loc[1] = [
        "Neem Guard 500",
        "Plant Protection",
        "Insecticide",
        "Organic",
        "BioSafe",
        "Aphids, whiteflies",
        "PP-NG-02",
        250.00,
        "Neem oil based insecticide"
    ]

    csv_buffer = io.StringIO()
    template_df.to_csv(csv_buffer, index=False)
    st.download_button(
        "📥 Download CSV Template",
        data=csv_buffer.getvalue(),
        file_name="agrochemicals_template.csv",
        mime="text/csv"
    )

    st.markdown("---")

    # 2. Upload file
    uploaded_file = st.file_uploader("Upload your filled CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, dtype=str)  # read as string to preserve leading zeros
            df.columns = df.columns.str.strip()
            missing = set(template_columns) - set(df.columns)
            if missing:
                st.error(f"Missing required columns: {', '.join(missing)}")
            else:
                # Convert mrp to numeric
                df['mrp'] = pd.to_numeric(df['mrp'], errors='coerce').fillna(0.0)
                df['description'] = df['description'].fillna('')
                df['brand'] = df['brand'].fillna('')
                df['target_use'] = df['target_use'].fillna('')
                df['category'] = df['category'].fillna('')
                df['subcategory'] = df['subcategory'].fillna('')
                df['type'] = df['type'].fillna('Fertilizer')  # default if missing, though required

                st.success(f"Valid CSV – {len(df)} rows detected.")
                st.dataframe(df.head(10), use_container_width=True)

                if st.button("🚀 Upload All to Database", type="primary"):
                    records = df.to_dict(orient="records")
                    # Ensure 'created_at' is left to DB default
                    if db.insert_many(TABLE, records):
                        st.success(f"✅ Successfully added {len(records)} items to the database!")
                        st.balloons()
                    else:
                        st.error("Bulk insert failed. Check logs or try a smaller batch.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
