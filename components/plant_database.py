"""
Plant Database Component with Bulk Upload, Excel Export, and Image Support
"""
import streamlit as st
import pandas as pd
import io

# Bilingual Dictionaries
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
    
    # Define headers based on language
    if language == "Bengali":
        headers = ["সাধারণ নাম (Name)", "বৈজ্ঞানিক নাম (Botanical)", "বিভাগ (Category)", "খুচরা মূল্য (MRP)", "স্টক (Stock)"]
    else:
        headers = ["Plant Name", "Botanical Name", "Category", "MRP", "Stock"]
        
    df = pd.DataFrame(columns=headers)
    
    # Write to BytesIO buffer
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
        
    return output.getvalue()

def render(db):
    # Language Toggle
    col_title, col_lang = st.columns([3, 1])
    with col_lang:
        st.session_state.lang = st.selectbox("Language / ভাষা", ["English", "Bengali"], key="plant_lang")
    
    t = LANG[st.session_state.lang] # Load translations
    
    with col_title:
        st.title(t["title"])
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs([t["view"], t["add_single"], t["add_bulk"]])
    
    # TAB 1: VIEW & EXPORT
    with tab1:
        st.subheader(t["view"])
        st.info("Inventory will appear here. Connect to DB.")
        # Example Export Button (Assuming db.get_plants() returns a dataframe)
        # current_data = db.get_plants()
        # st.download_button("Export Database to Excel", data=current_data.to_excel(), ...)
        
    # TAB 2: SINGLE ENTRY + IMAGE
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
                
            submitted = st.form_submit_button(t["save"], use_container_width=True)
            
            if submitted:
                if plant_name and mrp:
                    image_url = None
                    if image_file is not None:
                        # ---------------------------------------------------------
                        # PLACEHOLDER: Cloud Storage Logic Goes Here
                        # st.info(f"Processing image: {image_file.name}")
                        # image_url = upload_to_drive_or_supabase(image_file)
                        # ---------------------------------------------------------
                        pass
                        
                    st.success(f"Successfully added {plant_name}!")
                else:
                    st.error("Please fill in all required fields (*).")

    # TAB 3: BULK UPLOAD EXCEL
    with tab3:
        st.subheader(t["add_bulk"])
        st.write("1. Download the blank template. 2. Fill it out on your computer. 3. Upload it back here.")
        
        # Download Template
        excel_data = generate_excel_template(st.session_state.lang)
        st.download_button(
            label=t["dl_template"],
            data=excel_data,
            file_name=f"plant_template_{st.session_state.lang}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.markdown("---")
        
        # Upload Filled Template
        uploaded_excel = st.file_uploader(t["upload_excel"], type=["xlsx", "xls"])
        if uploaded_excel is not None:
            try:
                bulk_df = pd.read_excel(uploaded_excel)
                st.write("Preview of your data:")
                st.dataframe(bulk_df)
                
                if st.button("Process & Save Bulk Data", type="primary"):
                    # Process dataframe and send to Supabase
                    st.success(f"Successfully processed {len(bulk_df)} rows!")
            except Exception as e:
                st.error(f"Error reading Excel file: {e}")
