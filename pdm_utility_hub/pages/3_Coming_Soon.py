import streamlit as st

st.set_page_config(
    page_title="Coming Soon",
    page_icon="🚧",
    initial_sidebar_state="expanded" # Sidebar visibile
)

# --- CSS Globale per nascondere navigazione default e impostare larghezza sidebar ---
# Replicato qui per sicurezza
st.markdown(
    """
    <style>
    /* Imposta larghezza sidebar */
    [data-testid="stSidebar"] > div:first-child {
        width: 550px;
    }
    /* Nasconde la navigazione automatica generata da Streamlit nella sidebar */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Bottone per tornare all'Hub nella Sidebar ---
st.sidebar.page_link("pdm_hub.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---") # Separatore opzionale


# --- Contenuto Pagina ---
st.title("🚧 Coming Soon")
st.image("https://static.streamlit.io/examples/owl.jpg", caption="Work in progress!", width=300)
st.info("This section is currently under development. New utilities will be added here in the future.")
st.balloons()
