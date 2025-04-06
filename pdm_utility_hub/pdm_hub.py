# pdm_hub.py
import streamlit as st

st.set_page_config(
    page_title="PDM Utility Hub",
    page_icon="🛠️",
    layout="centered", # Manteniamo centrato per il contenuto generale
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

    /* Stile per i bottoni delle app (link) */
    a[data-testid="stPageLink"].app-button { /* Aggiunta classe per specificità */
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.5rem 2rem; /* Padding aumentato per renderli più grandi */
        background-color: #f0f2f6;
        color: #31333F;
        border-radius: 0.5rem;
        text-decoration: none;
        font-weight: bold;
        font-size: 1.1rem;
        border: 1px solid #dcdcdc;
        transition: background-color 0.3s ease, box-shadow 0.3s ease;
        width: 100%; /* Occupa tutta la colonna */
        min-height: 120px; /* Altezza minima aumentata per uniformità */
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        margin-bottom: 0.75rem; /* Spazio tra bottone e descrizione */
        text-align: center; /* Centra testo se va a capo */
        line-height: 1.4; /* Migliora leggibilità se testo va a capo */
    }
    a[data-testid="stPageLink"].app-button:hover {
        background-color: #e6eaf1;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #09529c;
    }
    /* Stile per l'icona dentro il bottone */
     a[data-testid="stPageLink"].app-button svg {
         margin-right: 0.75rem; /* Più spazio tra icona e testo */
         flex-shrink: 0; /* Evita che l'icona si restringa */
     }
     /* Rimuove la freccia standard */
    a[data-testid="stPageLink"].app-button > div[data-testid="stText"] > span:before {
        content: "" !important;
        margin-right: 0 !important;
    }

    /* Stile per descrizione sotto i bottoni */
     .app-description {
        font-size: 0.9em;
        color: #666;
        padding: 0 10px;
        text-align: justify; /* Testo giustificato */
        min-height: 70px; /* Altezza minima aumentata */
        margin-bottom: 1.5rem; /* Più spazio sotto la descrizione */
     }

     /* Stile specifico per il bottone Coming Soon (opzionale, per differenziarlo) */
     a[data-testid="stPageLink"].coming-soon-button {
         padding: 1rem 1.5rem; /* Leggermente più piccolo? */
         min-height: 80px;
         font-size: 1rem;
         background-color: #e9ecef; /* Colore diverso */
         border-style: dashed; /* Bordo tratteggiato */
         opacity: 0.8;
     }
     a[data-testid="stPageLink"].coming-soon-button:hover {
         opacity: 1;
         background-color: #dde2e8;
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
    # Applica la classe CSS al link
    st.markdown('<a href="/Bundle_Set_Images_Creator" target="_self" class="app-button" data-testid="stPageLink">📦 Bundle & Set Images Creator</a>', unsafe_allow_html=True)
    # Descrizione SOTTO il bottone
    st.markdown('<p class="app-description">Automatically downloads, processes, and organizes images for product bundles and sets based on an Akeneo CSV report.</p>', unsafe_allow_html=True)


# --- Bottone App 2 ---
with col2:
    # Applica la classe CSS al link
    st.markdown('<a href="/Repository_Image_Download_Renaming" target="_self" class="app-button" data-testid="stPageLink">🖼️ Repository Image Download & Renaming</a>', unsafe_allow_html=True)
    st.markdown('<p class="app-description">Downloads, resizes (1000x1000), and renames images from selected repositories (Switzerland, Farmadati) with the \'-h1\' suffix.</p>', unsafe_allow_html=True)

# --- Bottone Coming Soon (Sotto, cliccabile) ---
st.markdown("---") # Separatore

# Usiamo colonne per centrare e controllare la larghezza del bottone Coming Soon
# Ad esempio, una colonna vuota, una per il bottone, una vuota
col_space1, col_button_cs, col_space2 = st.columns([1, 2, 1]) # Proporzioni (1 parte vuota, 2 parti bottone, 1 parte vuota)

with col_button_cs:
    # Applica la classe CSS al link e la classe specifica coming-soon
    st.markdown('<a href="/Coming_Soon" target="_self" class="app-button coming-soon-button" data-testid="stPageLink">🚧 Coming Soon</a>', unsafe_allow_html=True)
    # Nessuna descrizione sotto Coming Soon


# --- Footer Modificato ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("v.1.0") # Footer aggiornato
