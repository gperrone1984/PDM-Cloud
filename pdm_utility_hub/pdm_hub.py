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

    /* Stile per i bottoni delle app */
    /* Targetizza il link generato da st.page_link */
    a[data-testid="stPageLink"] {
        display: flex; /* Usa flexbox per allineare icona e testo */
        align-items: center; /* Allinea verticalmente */
        justify-content: center; /* Allinea orizzontalmente */
        padding: 1rem 1.5rem; /* Padding interno */
        background-color: #f0f2f6; /* Colore sfondo bottone */
        color: #31333F; /* Colore testo */
        border-radius: 0.5rem; /* Bordi arrotondati */
        text-decoration: none; /* Rimuovi sottolineatura */
        font-weight: bold; /* Testo in grassetto */
        font-size: 1.1rem; /* Dimensione font */
        border: 1px solid #dcdcdc; /* Bordo leggero */
        transition: background-color 0.3s ease, box-shadow 0.3s ease; /* Transizione hover */
        width: 100%; /* Occupa tutta la colonna */
        min-height: 100px; /* Altezza minima per uniformità */
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); /* Ombra leggera */
        margin-bottom: 0.75rem; /* Spazio tra bottone e descrizione */
    }
    a[data-testid="stPageLink"]:hover {
        background-color: #e6eaf1; /* Colore sfondo al hover */
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* Ombra più pronunciata al hover */
        color: #09529c; /* Cambia colore testo al hover (opzionale) */
    }
    /* Stile per l'icona dentro il bottone (se presente) */
     a[data-testid="stPageLink"] svg {
         margin-right: 0.5rem; /* Spazio tra icona e testo */
     }
     /* Rimuove la freccia standard (già presente ma ri-confermato) */
    a[data-testid="stPageLink"] > div[data-testid="stText"] > span:before {
        content: "" !important;
        margin-right: 0 !important;
    }

    /* Stile per descrizione sotto i bottoni */
     .app-description {
        font-size: 0.9em;
        color: #666;
        padding: 0 10px; /* Padding laterale */
        text-align: center; /* Centra descrizione */
        min-height: 60px; /* Altezza minima per allineare descrizioni */
     }

     /* Stile per la sezione Coming Soon */
     .coming-soon-section {
         text-align: center;
         margin-top: 2rem; /* Spazio sopra */
         padding: 1rem;
         background-color: #f9f9f9;
         border-radius: 0.5rem;
         border: 1px dashed #cccccc; /* Bordo tratteggiato */
         opacity: 0.8; /* Leggermente trasparente */
     }
     .coming-soon-section h4 { /* Titolo più piccolo */
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        color: #555;
     }
     .coming-soon-section p {
         font-size: 0.85em;
         color: #777;
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
    st.page_link(
        "pages/1_Bundle_Set_Images_Creator.py",
        label="Bundle & Set Images Creator", # Testo del bottone
        icon="📦" # Icona opzionale
        )
    # Descrizione SOTTO il bottone
    st.markdown('<p class="app-description">Automatically downloads, processes, and organizes images for product bundles and sets based on an Akeneo CSV report.</p>', unsafe_allow_html=True)


# --- Bottone App 2 ---
with col2:
    st.page_link(
        "pages/2_Repository_Image_Download_Renaming.py",
        label="Repository Image Download & Renaming",
        icon="🖼️"
        )
    st.markdown('<p class="app-description">Downloads, resizes (1000x1000), and renames images from selected repositories (Switzerland, Farmadati) with the \'-h1\' suffix.</p>', unsafe_allow_html=True)

# --- Sezione Coming Soon (Sotto i bottoni) ---
st.markdown("---") # Separatore
st.markdown("<div class='coming-soon-section'>", unsafe_allow_html=True)
st.markdown("#### 🚧 Coming Soon") # Titolo più piccolo
st.markdown("<p>Future utilities and tools will be available here. Stay tuned for updates!</p>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)


# --- Footer Modificato ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("v.1.0") # Footer aggiornato
