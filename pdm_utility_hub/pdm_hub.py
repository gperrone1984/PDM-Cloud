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

    /* Stile base per i bottoni delle app (link) */
    a[data-testid="stPageLink"].app-button {
        display: flex;
        align-items: center;
        justify-content: center;
        /* Padding ridotto per bottoni più stretti */
        padding: 1.2rem 1.5rem;
        /* Colori più sobri */
        color: #31333F; /* Testo scuro */
        border-radius: 0.5rem;
        text-decoration: none;
        font-weight: bold;
        font-size: 1.05rem; /* Leggermente più piccolo */
        border: 1px solid #d1d7e0; /* Bordo grigio chiaro */
        transition: background-color 0.2s ease, box-shadow 0.2s ease;
        width: 100%;
        min-height: 100px; /* Altezza minima ridotta */
        box-shadow: 0 1px 2px rgba(0,0,0,0.04); /* Ombra molto leggera */
        margin-bottom: 0.75rem;
        text-align: center;
        line-height: 1.4;
    }
     a[data-testid="stPageLink"].app-button svg {
         margin-right: 0.6rem; /* Spazio icona ridotto */
         flex-shrink: 0;
     }
    a[data-testid="stPageLink"].app-button > div[data-testid="stText"] > span:before {
        content: "" !important; margin-right: 0 !important;
    }

    /* Colore specifico Bottone 1 (Bundle) - Grigio/Blu chiaro */
    a[data-testid="stPageLink"].app-button-bundle {
        background-color: #f0f2f6; /* Sfondo grigio chiaro default Streamlit */
    }
    a[data-testid="stPageLink"].app-button-bundle:hover {
        background-color: #e6eaf1; /* Grigio leggermente più scuro */
        border-color: #adb5bd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }

    /* Colore specifico Bottone 2 (Renaming) - Azzurro molto chiaro */
    a[data-testid="stPageLink"].app-button-rename {
         background-color: #e7f5ff; /* Azzurro pallido */
         border-color: #c4daee;
    }
    a[data-testid="stPageLink"].app-button-rename:hover {
        background-color: #d0eaff; /* Azzurro leggermente più scuro */
        border-color: #a9cce3;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }

    /* Stile per descrizione sotto i bottoni */
     .app-description {
        font-size: 0.9em;
        color: #666;
        padding: 0 10px;
        text-align: justify; /* Giustificato */
        min-height: 50px; /* Altezza minima ridotta */
        margin-bottom: 1.5rem;
     }

     /* Stile per la sezione Coming Soon (non cliccabile) */
     .coming-soon-placeholder {
         display: flex;
         flex-direction: column;
         align-items: center;
         justify-content: center;
         padding: 1.5rem;
         background-color: #f9f9f9;
         border-radius: 0.5rem;
         border: 1px dashed #cccccc;
         opacity: 0.7;
         min-height: 100px; /* Altezza simile ai bottoni */
         text-align: center;
         color: #6c757d;
     }
     .coming-soon-placeholder .icon {
         font-size: 2rem; /* Icona più piccola */
         margin-bottom: 0.5rem;
     }
      .coming-soon-placeholder h4 {
         font-size: 1.1rem;
         font-weight: bold;
         margin: 0;
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
# Aggiungiamo colonne laterali per restringere i bottoni centrali
col_space_left, col1, col2, col_space_right = st.columns([0.5, 2, 2, 0.5]) # Es: 0.5 spazio, 2 bottone, 2 bottone, 0.5 spazio

# --- Bottone App 1 ---
with col1:
    # Applica la classe CSS base e quella specifica del colore
    st.markdown('<a href="/Bundle_Set_Images_Creator" target="_self" class="app-button app-button-bundle" data-testid="stPageLink">📦 Bundle & Set Images Creator</a>', unsafe_allow_html=True)
    # Descrizione SOTTO il bottone - Modificata
    st.markdown('<p class="app-description">Automatically downloads, processes, and organizes images for product bundles and sets.</p>', unsafe_allow_html=True)


# --- Bottone App 2 ---
with col2:
    # Applica la classe CSS base e quella specifica del colore
    st.markdown('<a href="/Repository_Image_Download_Renaming" target="_self" class="app-button app-button-rename" data-testid="stPageLink">🖼️ Repository Image Download & Renaming</a>', unsafe_allow_html=True)
    # Descrizione SOTTO il bottone - Modificata
    st.markdown('<p class="app-description">Downloads, resizes, and renames images from selected repositories (e.g. Switzerland, Farmadati).</p>', unsafe_allow_html=True)

# --- Placeholder Coming Soon (Sotto, non cliccabile) ---
st.markdown("---") # Separatore

# Colonne per centrare il placeholder Coming Soon
col_cs_space1, col_cs_content, col_cs_space2 = st.columns([1, 1.5, 1]) # Colonna centrale leggermente più larga

with col_cs_content:
    # Placeholder non cliccabile
    st.markdown('<div class="coming-soon-placeholder">', unsafe_allow_html=True)
    st.markdown('<span class="icon">🚧</span>', unsafe_allow_html=True)
    st.markdown("<h4>Coming Soon</h4>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# --- Footer Modificato ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("v.1.0")
