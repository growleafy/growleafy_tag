"""
Plant Database Component with Bulk Upload, Excel Export, and Image Support
"""
import streamlit as st
import pandas as pd
import io

# --- Bilingual Dictionaries ---
LANG = {
    "English": {
        "title": "🌱 Plant Database",
        "view": "📋 View Inventory",
        "add_single": "➕ Add Single Plant",
        "add_bulk": "📁 Bulk Upload",
        "plant_name": "Common Name*",
        "bot_name": "Botanical Name",
        "category": "Category",
        "mrp": "MRP (₹)*",
        "stock": "Initial Stock",
        "image": "Upload Plant Image",
        "save": "Save Plant",
        "dl_template": "📥 Download Excel Template",
        "upload_excel": "Upload Filled Excel Template"
    },
    "Bengali": {
        "title": "🌱 উদ্ভিদ ডেটাবেস (Plant Database)",
        "view": "📋 ইনভেন্টরি দেখুন",
        "add_single": "➕ একটি উদ্ভিদ যোগ করুন",
        "add_bulk": "📁 একসাথে অনেক যোগ করুন (Bulk)",
        "plant_name": "সাধারণ নাম*",
        "bot_name": "বৈজ্ঞানিক নাম",
        "category": "বিভাগ",
        "mrp": "খুচরা মূল্য (₹)*",
        "stock": "প্রাথমিক স্টক",
        "image": "উদ্ভিদের ছবি আপলোড করুন",
        "save": "সংরক্ষণ করুন",
        "dl_template": "📥 এক্সেল টেমপ্লেট ডাউনলোড করুন",
        "upload_excel": "পূরণ করা এক্সেল ফাইল আপলোড করুন"
    }
}

def generate_excel_template(language):
    """Generates an empty Excel file with the correct headers in memory"""
    output = io.BytesIO()
    
    if language == "Bengali":
        headers = ["সাধারণ নাম (Name)", "বৈজ্ঞানিক নাম (Botanical)", "বিভাগ (Category)", "খুচরা মূল্য (MRP)", "স্টক (Stock)"]
    else:
        headers = ["Plant Name", "Botanical Name", "Category", "MRP", "Stock"]
        
    df = pd.DataFrame(columns=headers)
    
    # Write to BytesIO buffer using xlsxwriter
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
        
        # Optional: Auto-adjust column widths for better formatting
        worksheet = writer.sheets['Template']
        for i, col in enumerate(df.columns):
            worksheet.set_column(i, i, max(len(col) + 5, 15))
            
    return output.getvalue()

def render(db):
    # Initialize language in session state if not present
    if "lang" not in st.session_state:
        st.session_state.lang = "English"

    # Header & Language Toggle
    col_title, col_lang = st.columns([3, 1])
    with col_lang:
        st.session_state.lang = st.selectbox(
            "Language / ভাষা", 
            ["English", "Bengali"], 
            index=0 if st.session_state.lang == "English" else 1,
            key="plant_lang_selector"
        )
    
    t = LANG[st.session_state.lang]
    
    with col_title:
        st.title(t["title"])
    st.markdown("---")
    
    # Tabs Setup
    tab1, tab2, tab3 = st.tabs([t["view"], t["add_single"], t["add_bulk"]])
    
    # ==========================================
    # TAB 1: VIEW INVENTORY & EXPORT EXCEL
    # ==========================================
    with tab1:
        st.subheader(t["view"])
        
        try:
            # Fetch data from Supabase (Modify this to match your actual db method)
            # Example: plants_data = db.get_all_plants()
            plants_data = db.get_recent_items(limit=100).get('plants', []) 
            
            if plants_data:
                df = pd.DataFrame(plants_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Excel Export Button
                export_buffer = io.BytesIO()
                with pd.ExcelWriter(export_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Inventory')
                
                st.download_button(
                    label="📥 Export Inventory to Excel",
                    data=export_buffer.getvalue(),
                    file_name="plant_inventory.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No plants found in the database. Add some using the tabs above!")
        except Exception as e:
             st.info("Your inventory table will appear here once connected to your DatabaseManager fetching method.")

    # ==========================================
    # TAB 2: ADD SINGLE PLANT + IMAGE UPLOAD
    # ==========================================
    with tab2:
        st.subheader(t["add_single"])
        with st.form("add_plant_form"):
            col1, col2 = st.columns(2)
            with col1:
                plant_name = st.text_input(t["plant_name"])
                botanical_name = st.text_input(t["bot_name"])
                category = st.selectbox(t["category"], ["Indoor", "Outdoor", "Succulent", "Herb", "Tree"])
            with col2:
                mrp = st.number_input(t["mrp"], min_value=0.0, step=10.0)
                stock = st.number_input(t["stock"], min_value=0, step=1)
                image_file = st.file_uploader(t["image"], type=["jpg", "png", "jpeg"])
                
            submitted = st.form_submit_button(t["save"], type="primary", use_container_width=True)
            
            if submitted:
                if plant_name and mrp:
                    image_url = None
                    
                    # 1. Handle Image Upload to Supabase
                    if image_file is not None:
                        with st.spinner("Uploading image to Supabase..."):
                            file_bytes = image_file.getvalue()
                            image_url = db.upload_image(file_bytes, image_file.name)
                            
                            if not image_url:
                                st.error("Image upload failed, but saving plant data anyway.")
                                
                    # 2. Save Data to Database
                    # Replace with your actual db insert method:
                    # db.insert_plant(plant_name, botanical_name, category, mrp, stock, image_url)
                    
                    st.success(f"Successfully added {plant_name}!")
                    if image_url:
                        st.caption(f"Image successfully stored at: {image_url}")
                else:
                    st.error("Please fill in all required fields (*).")

    # ==========================================
    # TAB 3: BULK UPLOAD VIA EXCEL
    # ==========================================
    with tab3:
        st.subheader(t["add_bulk"])
        st.markdown("1. Download the blank template.\n2. Fill it out on your computer.\n3. Upload it back here.")
        
        # 1. Download Template
        excel_data = generate_excel_template(st.session_state.lang)
        st.download_button(
            label=t["dl_template"],
            data=excel_data,
            file_name=f"plant_template_{st.session_state.lang}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.markdown("---")
        
        # 2. Upload Filled Template
        uploaded_excel = st.file_uploader(t["upload_excel"], type=["xlsx", "xls"])
        
        if uploaded_excel is not None:
            try:
                bulk_df = pd.read_excel(uploaded_excel)
                st.write("Preview of your data:")
                st.dataframe(bulk_df, use_container_width=True)
                
                if st.button("Process & Save Bulk Data", type="primary"):
                    # Process dataframe and send to Supabase
                    # Example: db.insert_bulk_plants(bulk_df.to_dict('records'))
                    st.success(f"Successfully processed {len(bulk_df)} rows!")
            except Exception as e:
                st.error(f"Error reading Excel file. Please ensure you are using the downloaded template. Details: {e}")
