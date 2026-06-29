"""
Reports & Analytics Component
"""
import streamlit as st
import pandas as pd
import plotly.express as px

def render(db):
    st.title("📈 Reports & Analytics")
    st.markdown("---")
    
    # Fetch all data (Assuming your db has these methods)
    # If not, you will need to map these to your actual Supabase fetch calls
    stats = db.get_statistics()
    
    tab1, tab2, tab3 = st.tabs(["📊 Inventory Health", "💰 Financial Overview", "📥 Export Data"])
    
    with tab1:
        st.subheader("Inventory Distribution")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Create a donut chart of inventory types using Plotly
            inventory_data = {
                "Category": ["Plants", "Fertilizers", "Insecticides", "Pesticides"],
                "Count": [
                    stats.get('total_plants', 0), 
                    stats.get('total_fertilizers', 0), 
                    stats.get('total_insecticides', 0), 
                    stats.get('total_pesticides', 0)
                ]
            }
            df_pie = pd.DataFrame(inventory_data)
            
            # Only render chart if there is data to prevent Plotly errors
            if df_pie['Count'].sum() > 0:
                fig = px.pie(df_pie, values='Count', names='Category', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data to generate chart. Add items to your databases.")

        with col2:
            st.subheader("⚠️ Low Stock Alerts")
            st.write("Items that need to be reordered soon:")
            # Placeholder for low stock logic
            # low_stock_df = pd.DataFrame(db.get_low_stock_items(threshold=10))
            st.warning("Low stock tracking will appear here once connected to inventory quantities.")

    with tab2:
        st.subheader("Estimated Inventory Value")
        st.info("This calculates the total MRP value of all currently stocked items.")
        
        # Placeholder metrics
        col_v1, col_v2, col_v3 = st.columns(3)
        col_v1.metric("Plant Value", "₹0.00")
        col_v2.metric("Chemicals & Fertilizers", "₹0.00")
        col_v3.metric("Total Retail Value", "₹0.00")

    with tab3:
        st.subheader("Download Database Backups")
        st.write("Export your data to CSV format for external analysis or backup.")
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            # You would pass real data frames here
            dummy_csv = pd.DataFrame({"Data": ["Pending DB Connection"]}).to_csv(index=False)
            st.download_button(label="📥 Export Plants Database (CSV)", data=dummy_csv, file_name="plants_export.csv", mime="text/csv", use_container_width=True)
            st.download_button(label="📥 Export Fertilizers Database (CSV)", data=dummy_csv, file_name="fertilizers_export.csv", mime="text/csv", use_container_width=True)
            
        with col_dl2:
            st.download_button(label="📥 Export Insecticides Database (CSV)", data=dummy_csv, file_name="insecticides_export.csv", mime="text/csv", use_container_width=True)
            st.download_button(label="📥 Export Pesticides Database (CSV)", data=dummy_csv, file_name="pesticides_export.csv", mime="text/csv", use_container_width=True)
