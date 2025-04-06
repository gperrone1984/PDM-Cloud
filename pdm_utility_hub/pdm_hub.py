import streamlit as st

st.set_page_config(
    page_title="PDM Utility Hub",
    page_icon="🛠️",
    layout="centered"
)

# CSS per sidebar larga e stile card
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] > div:first-child {
        width: 550px;
    }
    .app-card {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        text-align: center;
        transition: box-shadow 0.3s ease-in-out;
        background-color: #f9f9f9;
        height: 180px; /* Altezza ridotta per solo titolo */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .app-card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .app-card h3 {
        margin-top: 10px;
        margin-bottom: 10px;
        color: #333;
    }
    /* Nasconde freccia e sottolineatura link */
    a[data-testid="stPageLink"] > div[data-testid="stText"] > span:before {
        content: "" !important;
        margin-right: 0 !important;
    }
     a[data-testid="stPageLink"] {
        text-decoration: none;
     }
    /* Stile per descrizione sotto le card */
     .app-description {
        font-size: 0.9em;
        color: #666;
        margin-top: -10px; /* Avvicina la descrizione alla card */
        padding: 0 15px; /* Padding laterale */
     }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Bottone per tornare all'Hub nella Sidebar ---
# Questo apparirà su tutte le pagine, inclusa questa
st.sidebar.page_link("pdm_hub.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---") # Separatore opzionale

# --- Contenuto Principale Hub ---
st.title("🛠️ PDM Utility Hub")
st.markdown("---")
st.markdown("Select an application below.")
st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

# --- Card App 1 ---
with col1:
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.page_link(
        "pages/1_Bundle_Set_Images_Creator.py",
        label="### Bundle & Set Images Creator",
        icon="📦"
        )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<p class="app-description">Automatically downloads, processes, and organizes images for product bundles and sets.</p>', unsafe_allow_html=True)


# --- Card App 2 ---
with col2:
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.page_link(
        "pages/2_Repository_Image_Download_Renaming.py",
        label="### Repository Image Download & Renaming",
        icon="🖼️"
        )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<p class="app-description">Downloads, resizes, and renames images from selected repositories (Switzerland, Farmadati).</p>', unsafe_allow_html=True)


# --- Footer (Opzionale) ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("PDM Utility Hub - Internal Team Tool")
