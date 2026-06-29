"""
GrowLeafy - Nursery Database & Tag Printing Application
Main Application Entry Point
"""

import streamlit as st
import os
from dotenv import load_dotenv
from utils.database import DatabaseManager
from components import (
    dashboard,
    plant_database,
    fertilizer_database,
    insecticide_database,
    pesticide_database,
    tag_generator,
    search,
    reports,
    ai_chat
)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="GrowLeafy - Plant Tag Generator & Nursery Database",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    with open('assets/styles.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize database connection
@st.cache_resource
def init_database():
    return DatabaseManager()

# Main Application Class
class GrowLeafyApp:
    def __init__(self):
        self.db = init_database()
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"
        if 'theme' not in st.session_state:
            st.session_state.theme = "light"
        if 'ai_enabled' not in st.session_state:
            st.session_state.ai_enabled = True
            
    def render_sidebar(self):
        """Render sidebar navigation"""
        with st.sidebar:
            st.image("https://via.placeholder.com/150x50?text=GrowLeafy", width=150)
            st.title("🌿 GrowLeafy")
            
            # Navigation menu
            st.markdown("---")
            
            menu_items = {
                "📊 Dashboard": "Dashboard",
                "🌱 Plant Database": "Plant Database",
                "🧪 Fertilizer Database": "Fertilizer Database",
                "🐛 Insecticide Database": "Insecticide Database",
                "🛡️ Pesticide Database": "Pesticide Database",
                "🏷️ Tag Generator": "Tag Generator",
                "🔍 Advanced Search": "Advanced Search",
                "📈 Reports": "Reports",
                "🤖 AI Assistant": "AI Assistant"
            }
            
            for label, page in menu_items.items():
                if st.button(label, key=page, use_container_width=True):
                    st.session_state.current_page = page
                    
            st.markdown("---")
            
            # Settings
            st.subheader("⚙️ Settings")
            st.session_state.theme = st.selectbox(
                "Theme",
                ["Light", "Dark"],
                index=0 if st.session_state.theme == "light" else 1
            )
            st.session_state.ai_enabled = st.checkbox(
                "Enable AI Assistant",
                value=st.session_state.ai_enabled
            )
            
            # Footer
            st.markdown("---")
            st.markdown("© 2024 GrowLeafy | v1.0.0")
            
    def render_main_content(self):
        """Render main content based on selected page"""
        current_page = st.session_state.current_page
        
        page_components = {
            "Dashboard": dashboard.render,
            "Plant Database": plant_database.render,
            "Fertilizer Database": fertilizer_database.render,
            "Insecticide Database": insecticide_database.render,
            "Pesticide Database": pesticide_database.render,
            "Tag Generator": tag_generator.render,
            "Advanced Search": search.render,
            "Reports": reports.render,
            "AI Assistant": ai_chat.render
        }
        
        if current_page in page_components:
            page_components[current_page](self.db)
            
    def run(self):
        """Run the application"""
        load_css()
        self.render_sidebar()
        self.render_main_content()

# Application entry point
if __name__ == "__main__":
    app = GrowLeafyApp()
    app.run()
