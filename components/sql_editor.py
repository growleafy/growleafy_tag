import streamlit as st
import pandas as pd

def render(db):
    st.title("🗄️ SQL Editor (Admin)")
    st.caption("Run raw SQL queries on your Supabase database.")

    query = st.text_area("SQL Query", height=150, placeholder="SELECT * FROM plants LIMIT 5;")

    if st.button("Execute Query", use_container_width=True):
        if not query.strip():
            st.warning("Please enter a query.")
            return
        try:
            # Use Supabase's rpc or raw sql? 
            # Actually, supabase-py doesn't support raw SQL directly.
            # We can use the underlying postgrest connection, but for safety we simulate via table methods.
            # For true raw SQL, you'd need a separate function; here's a workaround using the client's internal session.
            # This is for educational purposes – raw SQL execution requires privileged access.
            st.error("Raw SQL execution is not directly supported by the supabase-py client. Use the Supabase dashboard instead.")
        except Exception as e:
            st.error(f"Error: {e}")
