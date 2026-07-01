"""
Pots & Planters Component – Cascading categories + Bulk Import
"""
import streamlit as st
import pandas as pd
import io

TABLE = "pots_planters"

# ----------------------------------------------------------------------
# Pre-defined hierarchy for Pots & Planters
# ----------------------------------------------------------------------
POTS_HIERARCHY = {
    "Plastic Pots": [
        "Nursery Pot", "Round Pot", "Square Pot", "Tall Pot", "Hanging Pot",
        "Self-Watering Pot", "Orchid Pot", "Bonsai Pot", "Decorative Pot"
    ],
    "Terracotta Pots": [
        "Round", "Square", "Hanging", "Bonsai", "Decorative"
    ],
    "Ceramic Planters": [
        "Glossy", "Matte", "Hand Painted", "Indoor", "Decorative"
    ],
    "Cement / Concrete Planters": [
        "Round", "Square", "Rectangular", "Trough", "Outdoor"
    ],
    "FRP (Fiber) Planters": [
        "Tall", "Bowl", "Cube", "Designer"
    ],
    "Wooden Planters": [
        "Box", "Barrel", "Raised Bed", "Decorative"
    ],
    "Metal Planters": [
        "Iron", "Steel", "Aluminium", "Decorative"
    ],
    "Grow Bags": [
        "HDPE", "Fabric", "Geo Fabric", "UV Stabilized"
    ],
    "Nursery Bags": [
        "Poly Bag", "Root Trainer", "Seedling Bag"
    ],
    "Seedling Trays": [
        "50 Cell", "72 Cell", "98 Cell", "104 Cell", "128 Cell", "200 Cell"
    ],
    "Hanging Accessories": [
        "Hanger", "Chain", "Hook", "Rope"
    ],
    "Pot Saucers": [],
    "Pot Stands": [],
    "Pot Covers": [],
    "Accessories": []
}

# ----------------------------------------------------------------------
# Category / Subcategory selectors
# ----------------------------------------------------------------------
def _category_selector(default=None):
    """Return the chosen major category (free text if 'Other')."""
    predefined = list(POTS_HIERARCHY.keys())
    options = predefined + ["Other"]
    if default and default in predefined:
        idx = options.index(default)
    elif default and default not in predefined:
        idx = options.index("Other")
    else:
        idx = 0
    choice = st.selectbox("Category", options, index=idx)
    if choice == "Other":
        return st.text_input("Enter custom category", value=default if (default and default not in predefined) else "")
    return choice


def _subcategory_selector(category, default=None):
    """Return the subcategory based on category, with option to type new."""
    if category in POTS_HIERARCHY and POTS_HIERARCHY[category]:
        subs = POTS_HIERARCHY[category]
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
        # No subcategories defined or category is custom – free text
        return st.text_input("Subcategory", value=default if default else "")


# ----------------------------------------------------------------------
# Main render
# ----------------------------------------------------------------------
def render(db):
    st.title("🪴 Pots & Planters")
    st.caption("Manage your planter inventory with dynamic categories and bulk import")

    tab1, tab2 = st.tabs(["📋 Inventory", "📤 Bulk Upload"])

    with tab1:
        _render_inventory(db)

    with tab2:
        _render_bulk_upload(db)


# ----------------------------------------------------------------------
# Inventory tab – View, Add, Edit / Delete
# ----------------------------------------------------------------------
def _render_inventory(db):
    mode = st.radio("Action", ["View All", "Add New", "Edit / Delete"], key="pots_mode", horizontal=True)

    if mode == "View All":
        items = db.fetch_all(TABLE)
        if items:
            df = pd.DataFrame(items)
            st.dataframe(df, use_container_width=True)
            st.metric("Total Pots & Planters", len(items))
        else:
            st.info("No items yet. Use 'Add New' to create one.")

    elif mode == "Add New":
        with st.form("add_pot"):
            name = st.text_input("Product Name *")
            category = _category_selector()
            subcategory = _subcategory_selector(category)
            material = st.text_input("Material")
            size = st.text_input("Size")
            sku = st.text_input("SKU")
            mrp = st.number_input("MRP (₹)", min_value=0.0, format="%.2f")
            description = st.text_area("Description")
            if st.form_submit_button("💾 Save"):
                if not name:
                    st.error("Product name is required.")
                else:
                    data = {
                        "name": name,
                        "category": category,
                        "subcategory": subcategory,
                        "material": material,
                        "size": size,
                        "sku": sku,
                        "mrp": mrp,
                        "description": description
                    }
                    if db.insert_one(TABLE, data):
                        st.success("Pot / Planter added!")
                        st.rerun()
                    else:
                        st.error("Failed to save.")

    elif mode == "Edit / Delete":
        all_items = db.fetch_all(TABLE)
        if not all_items:
            st.info("No items found.")
            return
        df = pd.DataFrame(all_items)
        selected_id = st.selectbox(
            "Select item to edit/delete",
            df['id'],
            format_func=lambda x: f"{df[df['id']==x].iloc[0]['name']} (SKU: {df[df['id']==x].iloc[0].get('sku','')})"
        )
        item = df[df['id'] == selected_id].iloc[0]

        with st.form("edit_pot"):
            name = st.text_input("Product Name", item.get('name', ''))
            # Pre-fill category/subcategory with existing values
            current_cat = item.get('category', '')
            current_sub = item.get('subcategory', '')
            category = _category_selector(default=current_cat)
            subcategory = _subcategory_selector(category, default=current_sub)
            material = st.text_input("Material", item.get('material', ''))
            size = st.text_input("Size", item.get('size', ''))
            sku = st.text_input("SKU", item.get('sku', ''))
            mrp = st.number_input("MRP", value=float(item.get('mrp', 0)), min_value=0.0, format="%.2f")
            description = st.text_area("Description", item.get('description', ''))

            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Update"):
                    data = {
                        "name": name,
                        "category": category,
                        "subcategory": subcategory,
                        "material": material,
                        "size": size,
                        "sku": sku,
                        "mrp": mrp,
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
                        st.error("Deletion failed.")


# ----------------------------------------------------------------------
# Bulk upload tab – similar to agrochemicals
# ----------------------------------------------------------------------
def _render_bulk_upload(db):
    st.subheader("📤 Bulk Import – Pots & Planters")
    st.markdown("Download the CSV template, fill in your products, and upload to add them all at once. "
                "**Existing records will not be affected.**")

    # 1. Template download
    template_columns = [
        "name", "category", "subcategory", "material", "size",
        "sku", "mrp", "description"
    ]
    template_df = pd.DataFrame(columns=template_columns)
    # Add example rows
    template_df.loc[0] = [
        "Round Plastic Pot 10\"", "Plastic Pots", "Round Pot", "Plastic",
        "10 inch", "PP-R-10", 80.00, "Lightweight round plastic pot"
    ]
    template_df.loc[1] = [
        "Ceramic Glossy Planter", "Ceramic Planters", "Glossy", "Ceramic",
        "12 inch", "CP-GL-12", 450.00, "Glossy ceramic planter for indoor use"
    ]

    csv_buffer = io.StringIO()
    template_df.to_csv(csv_buffer, index=False)
    st.download_button(
        "📥 Download CSV Template",
        data=csv_buffer.getvalue(),
        file_name="pots_planters_template.csv",
        mime="text/csv"
    )

    st.markdown("---")

    # 2. Upload file
    uploaded_file = st.file_uploader("Upload your filled CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, dtype=str)  # read as string
            df.columns = df.columns.str.strip()
            missing = set(template_columns) - set(df.columns)
            if missing:
                st.error(f"Missing required columns: {', '.join(missing)}")
            else:
                # Convert mrp to numeric
                df['mrp'] = pd.to_numeric(df['mrp'], errors='coerce').fillna(0.0)
                # Fill NA for text columns
                for col in ['description', 'material', 'size', 'category', 'subcategory']:
                    df[col] = df[col].fillna('')

                st.success(f"Valid CSV – {len(df)} rows detected.")
                st.dataframe(df.head(10), use_container_width=True)

                if st.button("🚀 Upload All to Database", type="primary"):
                    records = df.to_dict(orient="records")
                    if db.insert_many(TABLE, records):
                        st.success(f"✅ Successfully added {len(records)} items!")
                        st.balloons()
                    else:
                        st.error("Bulk insert failed. Check logs or try a smaller batch.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
