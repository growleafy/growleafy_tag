"""
GrowLeafy - Nursery Database & Tag Printing Application
Main Application Entry Point
"""

import streamlit as st
import os
import time
from dotenv import load_dotenv
from utils.database import DatabaseManager

# Page configuration MUST be the first Streamlit command
st.set_page_config(
    page_title="GrowLeafy | Nursery Hub",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

from components import (
    dashboard,
    plant_database,
    agrochemicals,
    pots_planters,
    seeds,
    garden_tools,
    watering_tools,
    garden_decor,
    nursery_operations,       # NEW: Phase 1 Operations
    tag_generator,
    invoice_generator,
    search,
    reports,
    ai_chat
)

# Load environment variables
load_dotenv()

# Initialize database connection
@st.cache_resource(show_spinner=False)
def init_database():
    """Create DatabaseManager with Supabase credentials."""
    url = None
    key = None

    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except KeyError:
        pass

    if not url or not key:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        st.error("🚨 Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY in .env or Streamlit secrets.")
        st.stop()

    return DatabaseManager(url=url, key=key)


class GrowLeafyApp:
    def __init__(self):
        self.db = init_database()
        self.initialize_session_state()
        self.load_css()

    def initialize_session_state(self):
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"
        if 'theme' not in st.session_state:
            st.session_state.theme = "Light"
        if 'ai_enabled' not in st.session_state:
            st.session_state.ai_enabled = True

    def load_css(self):
        try:
            with open('assets/styles.css') as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        except FileNotFoundError:
            pass  # no styling is fine

    def render_sidebar(self):
        with st.sidebar:
            st.markdown("<h1 style='text-align: center; color: #2e7d32;'>🌿 GrowLeafy</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray; font-size: 0.9em; margin-top: -15px;'>Nursery Management</p>", unsafe_allow_html=True)
            st.markdown("---")

            # Updated navigation – includes all modules
            menu_items = {
                "Dashboard": "📊 Dashboard",
                "Plant Database": "🌱 Plant Database",
                "Agrochemicals": "🧪 Agrochemicals",
                "Pots & Planters": "🪴 Pots & Planters",
                "Seeds": "🌱 Seeds",
                "Garden Tools": "🛠 Garden Tools",
                "Watering Tools": "💧 Watering Tools",
                "Garden Decor": "🏡 Garden Decor",
                "Nursery Operations": "🌿 Nursery Ops",   # NEW
                "Tag Generator": "🏷️ Tag Generator",
                "Invoice Generator": "🧾 Invoice Generator",
                "Advanced Search": "🔍 Advanced Search",
                "Reports": "📈 Reports",
                "AI Assistant": "🤖 AI Assistant"
            }

            st.markdown("### Navigation")
            for page_key, label in menu_items.items():
                is_active = st.session_state.current_page == page_key
                button_type = "primary" if is_active else "secondary"
                if st.button(label, key=page_key, use_container_width=True, type=button_type):
                    if st.session_state.current_page != page_key:
                        st.session_state.current_page = page_key
                        st.rerun()

            st.markdown("---")

            with st.expander("⚙️ Application Settings", expanded=False):
                new_theme = st.selectbox(
                    "Theme",
                    ["Light", "Dark"],
                    index=0 if st.session_state.theme == "Light" else 1
                )
                if new_theme != st.session_state.theme:
                    st.session_state.theme = new_theme
                    st.toast(f"Theme switched to {new_theme} mode!", icon="🎨")
                    time.sleep(0.5)
                    st.rerun()

                new_ai_state = st.checkbox(
                    "Enable AI Assistant",
                    value=st.session_state.ai_enabled
                )
                if new_ai_state != st.session_state.ai_enabled:
                    st.session_state.ai_enabled = new_ai_state
                    status = "enabled" if new_ai_state else "disabled"
                    st.toast(f"AI Assistant {status}.", icon="🤖")

            st.markdown("<div style='text-align: center; margin-top: 50px; color: gray; font-size: 0.8em;'>© 2024 GrowLeafy v1.0.0</div>", unsafe_allow_html=True)

    def render_main_content(self):
        current_page = st.session_state.current_page

        page_components = {
            "Dashboard": dashboard.render,
            "Plant Database": plant_database.render,
            "Agrochemicals": agrochemicals.render,
            "Pots & Planters": pots_planters.render,
            "Seeds": seeds.render,
            "Garden Tools": garden_tools.render,
            "Watering Tools": watering_tools.render,
            "Garden Decor": garden_decor.render,
            "Nursery Operations": nursery_operations.render,   # NEW
            "Tag Generator": tag_generator.render,
            "Invoice Generator": invoice_generator.render,
            "Advanced Search": search.render,
            "Reports": reports.render,
            "AI Assistant": ai_chat.render
        }

        st.markdown('<div class="fluid-container">', unsafe_allow_html=True)

        if current_page in page_components:
            if current_page == "AI Assistant" and not st.session_state.ai_enabled:
                st.warning("The AI Assistant is currently disabled in your settings.")
            else:
                page_components[current_page](self.db)

        st.markdown('</div>', unsafe_allow_html=True)

    def run(self):
        self.render_sidebar()
        self.render_main_content()


if __name__ == "__main__":
    app = GrowLeafyApp()
    app.run()
