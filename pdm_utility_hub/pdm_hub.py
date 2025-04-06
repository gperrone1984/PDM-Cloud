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

    /* Sfondo per il contenitore principale (solo in questa pagina) */
    /* Seleziona l'elemento che contiene le colonne */
    .main .block-container {
         /* background-color: #f8f9fa; /* Grigio chiarissimo */
         /* padding-top: 2rem; /* Aggiusta padding se necessario */
         /* padding-bottom: 2rem; */
    }
    /* Nota: Cambiare lo sfondo principale può essere difficile a causa della struttura di Streamlit.
       Potrebbe essere più semplice mantenere lo sfondo di default e concentrarsi sui bottoni.
       Se vuoi provare, decommenta le righe sopra e vedi l'effetto. */


    /* Stile base per i bottoni delle app (link) */
    a[data-testid="stPageLink"].app-button {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.5rem 2rem;
        color: white; /* Testo bianco per entrambi i bottoni colorati */
        border-radius: 0.5rem;
        text-decoration: none;
        font-weight: bold;
        font-size: 1.1rem;
        border: none; /* Rimuoviamo bordo di default, il colore fa da sé */
        transition: background-color 0.3s ease, box-shadow 0.3s ease;
        width: 100%;
        min-height: 120px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* Ombra più definita */
        margin-bottom: 0.75rem;
        text-align: center;
        line-height: 1.4;
    }
     a[data-testid="stPageLink"].app-button svg {
         margin-right: 0.75rem;
         flex-shrink: 0;
     }
    a[data-testid="stPageLink"].app-button > div[data-testid="stText"] > span:before {
        content: "" !important; margin-right: 0 !important;
    }

    /* Colore specifico Bottone 1 (Bundle) */
    a[data-testid="stPageLink"].app-button-bundle {
        background-color: #3498db; /* Blu cielo */
    }
    a[data-testid="stPageLink"].app-button-bundle:hover {
        background-color: #2980b9; /* Blu più scuro */
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }

    /* Colore specifico Bottone 2 (Renaming) */
    a[data-testid="stPageLink"].app-button-rename {
         background-color: #1abc9c; /* Teal */
    }
    a[data-testid="stPageLink"].app-button-rename:hover {
        background-color: #16a085; /* Teal più scuro */
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }

    /* Stile specifico per il bottone Coming Soon */
     a[data-testid="stPageLink"].coming-soon-button {
         padding: 1rem 1.5rem;
         min-height: 80px;
         font-size: 1rem;
         background-color: #e9ecef; /* Grigio chiaro */
         color: #6c757d; /* Testo grigio scuro */
         border: 1px dashed #adb5bd; /* Bordo tratteggiato */
         box-shadow: none; /* Rimuovi ombra */
         opacity: 0.8;
     }
     a[data-testid="stPageLink"].coming-soon-button:hover {
         opacity: 1;
         background-color: #dde2e8;
         color: #495057;
         box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Ombra leggera al hover */
     }


    /* Stile per descrizione sotto i bottoni */
     .app-description {
        font-size: 0.9em;
        color: #666;
        padding: 0 10px;
        text-align: justify;
        min-height: 70px;
        margin-bottom: 1.5rem;
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

# --- Bottone App 1 ---
with col1:
    # Applica la classe CSS base e quella specifica del colore
    st.markdown('<a href="/Bundle_Set_Images_Creator" target="_self" class="app-button app-button-bundle" data-testid="stPageLink">📦 Bundle & Set Images Creator</a>', unsafe_allow_html=True)
    st.markdown('<p class="app-description">Automatically downloads, processes, and organizes images for product bundles and sets based on an Akeneo CSV report.</p>', unsafe_allow_html=True)


# --- Bottone App 2 ---
with col2:
    # Applica la classe CSS base e quella specifica del colore
    st.markdown('<a href="/Repository_Image_Download_Renaming" target="_self" class="app-button app-button-rename" data-testid="stPageLink">🖼️ Repository Image Download & Renaming</a>', unsafe_allow_html=True)
    st.markdown('<p class="app-description">Downloads, resizes (1000x1000), and renames images from selected repositories (Switzerland, Farmadati) with the \'-h1\' suffix.</p>', unsafe_allow_html=True)

# --- Bottone Coming Soon (Sotto, cliccabile) ---
st.markdown("---") # Separatore
col_space1, col_button_cs, col_space2 = st.columns([1, 2, 1])

with col_button_cs:
    # Applica la classe CSS base e quella specifica coming-soon
    st.markdown('<a href="/Coming_Soon" target="_self" class="app-button coming-soon-button" data-testid="stPageLink">🚧 Coming Soon</a>', unsafe_allow_html=True)


# --- Footer Modificato ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("v.1.0")
