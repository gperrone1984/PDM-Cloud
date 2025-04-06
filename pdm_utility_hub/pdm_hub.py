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
         padding-top: 2rem;
         padding-bottom: 2rem;
         border-radius: 0.5rem; /* Arrotonda anche lo sfondo */
    }
    /* Assicura che il padding non venga sovrascritto */
    div.block-container {
        padding: 2rem 1rem 1rem 1rem; /* Aggiusta padding se necessario */
    }


    /* Stile base per i bottoni/placeholder delle app */
    .app-container {
        display: flex;
        flex-direction: column; /* Allinea bottone e descrizione verticalmente */
        align-items: center; /* Centra orizzontalmente nella colonna */
        margin-bottom: 1.5rem; /* Spazio sotto ogni blocco app */
    }
    .app-button-link, .app-button-placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.2rem 1.5rem; /* Padding per dimensione */
        color: #495057; /* Testo grigio scuro */
        border-radius: 0.5rem;
        text-decoration: none;
        font-weight: bold;
        font-size: 1.05rem;
        border: 1px solid #dee2e6; /* Bordo grigio chiaro */
        width: 90%; /* Larghezza leggermente ridotta, centrata da app-container */
        min-height: 100px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        margin-bottom: 0.75rem; /* Spazio tra bottone e descrizione */
        text-align: center;
        line-height: 1.4;
        background-color: #ffffff; /* Sfondo bianco di base */
        transition: background-color 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
     .app-button-link svg, .app-button-placeholder svg,
     .app-button-link .icon, .app-button-placeholder .icon { /* Gestisce sia SVG che span icon */
         margin-right: 0.6rem;
         flex-shrink: 0;
     }
    .app-button-link > div[data-testid="stText"] > span:before { /* Rimuove freccia link */
        content: "" !important; margin-right: 0 !important;
    }

    /* Effetto Hover solo per i link cliccabili */
    .app-button-link:hover {
        background-color: #e9ecef; /* Grigio molto chiaro al hover */
        border-color: #ced4da;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
        cursor: pointer;
    }

    /* Colore specifico Bottone 1 (Bundle) - Leggermente diverso */
    .app-button-bundle {
        /* background-color: #fdfdfe; */ /* Quasi bianco */
        /* border-color: #eef; */
    }
    .app-button-bundle:hover {
         /* background-color: #f0f2f8; */
    }

    /* Colore specifico Bottone 2 (Renaming) - Leggermente diverso */
    .app-button-rename {
         background-color: #f5faff; /* Azzurro quasi impercettibile */
         /* border-color: #eaf; */
    }
    .app-button-rename:hover {
        background-color: #eaf2ff;
    }

    /* Stile Placeholder Coming Soon (non cliccabile) */
    .app-button-placeholder {
        background-color: #f1f3f5; /* Grigio un po' più scuro */
        opacity: 0.7;
        cursor: default; /* Cursore non cliccabile */
        box-shadow: none; /* Senza ombra */
        color: #868e96; /* Testo più chiaro */
    }
     .app-button-placeholder .icon {
         font-size: 1.5em; /* Icona leggermente più piccola */
     }


    /* Stile per descrizione sotto i bottoni */
     .app-description {
        font-size: 0.9em;
        color: #6c757d; /* Grigio testo */
        padding: 0 15px; /* Padding laterale aumentato */
        text-align: justify;
        width: 90%; /* Larghezza uguale al bottone */
        margin: 0 auto; /* Centra la descrizione */
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


# --- RIMOSSA Sezione Coming Soon separata ---


# --- Footer Modificato ---
# st.markdown("<br><br>", unsafe_allow_html=True) # Rimuoviamo spazio extra se non serve
st.markdown("---")
st.caption("v.1.0")
