# pdm_hub.py
import streamlit as st

st.set_page_config(
    page_title="PDM Utility Hub",
    page_icon="🛠️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CSS Globale ---
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

    /* Sfondo per il contenitore principale */
    .main .block-container {
         background-color: #f8f9fa; /* Grigio chiarissimo */
         padding: 2rem 1rem 1rem 1rem; /* Padding */
         border-radius: 0.5rem;
    }
    /* Assicura che il padding non venga sovrascritto */
    div.block-container {
        padding: 2rem 1rem 1rem 1rem;
    }


    /* Stile base per i bottoni/placeholder delle app */
    .app-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-bottom: 1.5rem;
    }
    .app-button-link, .app-button-placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.2rem 1.5rem;
        border-radius: 0.5rem;
        text-decoration: none;
        font-weight: bold;
        font-size: 1.05rem;
        border: 1px solid #dee2e6; /* Bordo grigio chiaro */
        width: 90%;
        min-height: 100px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        margin-bottom: 0.75rem;
        text-align: center;
        line-height: 1.4;
        transition: background-color 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        color: #343a40; /* Testo grigio scuro per leggibilità su sfondi chiari */
    }
     .app-button-link svg, .app-button-placeholder svg,
     .app-button-link .icon, .app-button-placeholder .icon {
         margin-right: 0.6rem;
         flex-shrink: 0;
     }
    .app-button-link > div[data-testid="stText"] > span:before {
        content: "" !important; margin-right: 0 !important;
    }

    /* Effetto Hover solo per i link cliccabili */
    .app-button-link:hover {
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        border-color: #adb5bd;
        cursor: pointer;
    }

    /* Colore specifico Bottone 1 (Bundle) - Azzurro Polvere Chiaro */
    .app-button-bundle {
        background-color: #e0fbfc; /* Azzurro molto chiaro */
        border-color: #c7eeeb;
    }
    .app-button-bundle:hover {
         background-color: #c7eeeb; /* Leggermente più scuro/saturo */
    }

    /* Colore specifico Bottone 2 (Renaming) - Verde Acqua Chiaro */
    .app-button-rename {
         background-color: #e6fff0; /* Verde molto chiaro */
         border-color: #cff0db;
    }
    .app-button-rename:hover {
        background-color: #cff0db; /* Leggermente più scuro/saturo */
    }

    /* Stile Placeholder Coming Soon (non cliccabile) */
    .app-button-placeholder {
        background-color: #f1f3f5;
        opacity: 0.7;
        cursor: default;
        box-shadow: none;
        color: #868e96;
        border-color: #e9ecef;
    }
     .app-button-placeholder .icon {
         font-size: 1.5em;
     }


    /* Stile per descrizione sotto i bottoni */
     .app-description {
        font-size: 0.9em;
        color: #6c757d;
        padding: 0 15px;
        text-align: justify;
        width: 90%;
        margin: 0 auto;
     }

    </style>
    """,
    unsafe_allow_html=True
)

# --- Bottone per tornare all'Hub nella Sidebar ---
st.sidebar.page_link("pdm_hub.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---") # Separatore opzionale

# --- Contenuto Principale Hub ---
st.title("🛠️ PDM Utility Hub")
st.markdown("---")
st.markdown("**Welcome to the Product Data Management Utility Hub. Select an application below to get started.**")
st.markdown("<br>", unsafe_allow_html=True) # Spazio

# Layout a 2 colonne per i bottoni principali
col1, col2 = st.columns(2)

# --- Colonna 1: App Bundle + Coming Soon ---
with col1:
    # Contenitore per Bottone 1 + Descrizione
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    # Bottone 1 (Cliccabile)
    st.markdown('<a href="/Bundle_Set_Images_Creator" target="_self" class="app-button-link app-button-bundle" data-testid="stPageLink">📦 Bundle & Set Images Creator</a>', unsafe_allow_html=True)
    # Descrizione 1
    st.markdown('<p class="app-description">Automatically downloads, processes, and organizes images for product bundles and sets.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Contenitore per Placeholder Coming Soon
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    # Placeholder Coming Soon (Non Cliccabile)
    st.markdown('<div class="app-button-placeholder"><span class="icon">🚧</span> Coming Soon</div>', unsafe_allow_html=True)
    # Nessuna descrizione per Coming Soon
    st.markdown('</div>', unsafe_allow_html=True)


# --- Colonna 2: App Renaming ---
with col2:
    # Contenitore per Bottone 2 + Descrizione
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    # Bottone 2 (Cliccabile)
    st.markdown('<a href="/Repository_Image_Download_Renaming" target="_self" class="app-button-link app-button-rename" data-testid="stPageLink">🖼️ Repository Image Download & Renaming</a>', unsafe_allow_html=True)
    # Descrizione 2
    st.markdown('<p class="app-description">Downloads, resizes, and renames images from selected repositories (e.g. Switzerland, Farmadati).</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# --- Footer Modificato ---
st.markdown("---")
st.caption("v.1.0")
