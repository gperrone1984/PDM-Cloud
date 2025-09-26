import streamlit as st
import hashlib

# Initialize authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Page configuration
st.set_page_config(
    page_title="PDM Utility Hub TEST ENVIRONMENT",
    page_icon="🛠️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Force light theme
st._config.set_option("theme.base", "light")

# Hide default sidebar
st.markdown("""
    <style>
        section[data-testid="stSidebar"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# Authentication function
def authenticate(username: str, password: str) -> bool:
    try:
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        return (username == st.secrets["auth"]["username"] and 
                input_hash == st.secrets["auth"]["password_hash"])
    except Exception:
        st.error("Authentication system error")
        return False

# Show login form if not authenticated
if not st.session_state.authenticated:
    with st.container():
        st.markdown("""
        <div style='max-width: 500px; margin: 2rem auto; padding: 2rem; 
                    border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    background-color: white;'>
            <h2 style='color: #0369a1; text-align: center;'>
                🔐 PDM Utility Hub TEST ENVIRONMENT
            </h2>
            <h3 style='color: #0369a1; text-align: center;'>
                Login
            </h3>
        """, unsafe_allow_html=True)
        
        with st.form("Login"):
            username = st.text_input("Username").strip()
            password = st.text_input("Password", type="password").strip()
            
            if st.form_submit_button("Login"):
                if authenticate(username, password):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# --- MAIN CONTENT ---
st.title("🛠️ PDM Utility Hub TEST ENVIRONMENT")
st.markdown("---")
st.markdown("**Welcome to the Product Data Management Utility Hub. Select an application below to get started.**")

# Two-column layout
col1, col2 = st.columns(2)

with col1:
    if st.button("📦 Bundle & Set Images Creator", use_container_width=True):
        st.switch_page("pages/Bundle_Set_Images_Creator.py")
    st.markdown("""
        <p class="app-description">
            Automatically downloads, processes, and organizes images for product bundles and sets.
        </p>
    """, unsafe_allow_html=True)

        # Active Search App button
    if st.button("🔎 Search App", use_container_width=True):
        st.switch_page("pages/Search_App.py")
    st.markdown("""
        <p class="app-description">
            Extract rows containing specified keywords from uploaded Excel files.
        </p>
    """, unsafe_allow_html=True)

with col2:
    if st.button("🖼️ Repository Image Download & Renaming", use_container_width=True):
        st.switch_page("pages/Repository_Image_Download_Renaming.py")
    st.markdown("""
        <p class="app-description">
            Downloads, resizes, and renames images from selected repositories.
        </p>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption("v1.0 | Secure Access System")

# --- Custom CSS ---
st.markdown("""
    <style>
    body { background-color: #f5f5f5 !important; }

    .app-button-placeholder {
        background-color: #f8fafc !important;
        color: #64748b !important;
        border: 1px dashed #e2e8f0 !important;
        padding: 1.2rem !important;
        border-radius: 0.5rem !important;
        margin-bottom: 0.75rem !important;
        width: 90% !important;
        min-height: 100px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        opacity: 0.7;
    }

    .app-button-link {
        background-color: #f5faff;
        border: 1px solid #c4daee;
        padding: 1.2rem;
        border-radius: 0.5rem;
        font-weight: bold;
        font-size: 1.05rem;
        width: 90%;
        text-align: center;
        margin-bottom: 0.75rem;
        transition: background-color 0.2s ease;
        color: #343a40;
    }
    .app-button-link:hover {
        background-color: #eaf2ff;
        border-color: #a9cce3;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        cursor: pointer;
    }

    .app-description {
        font-size: 0.9em;
        color: #334155;
        padding: 0 15px;
        text-align: justify;
        width: 90%;
        margin: 0 auto;
    }

    button[kind="secondary"] {
        background-color: #e0f2fe !important;
        color: #0369a1 !important;
        border: 1px solid #bae6fd !important;
        padding: 1.2rem !important;
        border-radius: 0.5rem !important;
        font-weight: bold !important;
        font-size: 1.05rem !important;
        transition: all 0.2s ease !important;
    }
    button[kind="secondary"]:hover {
        background-color: #bae6fd !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08) !important;
    }
    </style>
""", unsafe_allow_html=True)
