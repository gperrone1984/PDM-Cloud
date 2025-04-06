import streamlit as st

st.set_page_config(
    page_title="PDM Utility Hub",
    page_icon="🛠️",
    layout="centered",
    initial_sidebar_state="expanded" # Assicura che la sidebar sia visibile per il bottone
)

# --- CSS Globale per nascondere navigazione default e impostare larghezza sidebar ---
# Questo CSS verrà applicato a TUTTE le pagine perché è nell'hub principale
# e Streamlit tende a caricare CSS globalmente per la sessione.
# Per sicurezza, lo replicheremo anche nelle altre pagine.
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

    /* Stile per le card cliccabili */
    .app-card {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px; /* Spazio tra card e descrizione */
        text-align: center;
        transition: box-shadow 0.3s ease-in-out;
        background-color: #f9f9f9;
        height: 150px; /* Altezza per contenere titolo e icona */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        cursor: pointer; /* Indica che è cliccabile */
    }
    .app-card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .app-card h3 { /* Stile per il titolo dentro la card */
        margin-top: 10px;
        margin-bottom: 10px;
        color: #333;
    }
     .app-card .icon { /* Stile per l'icona */
         font-size: 2.5em; /* Dimensione icona */
         display: block; /* Assicura che vada a capo */
         margin-bottom: 10px;
    }
    /* Nasconde freccia e sottolineatura link standard */
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
        margin-top: -15px; /* Avvicina la descrizione alla card */
        padding: 0 10px; /* Padding laterale */
        text-align: center; /* Centra descrizione */
        min-height: 60px; /* Altezza minima per allineare descrizioni */
     }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Bottone per tornare all'Hub nella Sidebar ---
# Questo apparirà su tutte le pagine perché è anche negli altri file .py
st.sidebar.page_link("pdm_hub.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---") # Separatore opzionale

# --- Contenuto Principale Hub ---
st.title("🛠️ PDM Utility Hub")
st.markdown("---")
# Testo di benvenuto in grassetto
st.markdown("**Welcome to the Product Data Management Utility Hub. Select an application below to get started.**")
st.markdown("<br>", unsafe_allow_html=True) # Spazio

# Layout a 3 colonne come nell'immagine
col1, col2, col3 = st.columns(3)

# --- Card App 1 ---
with col1:
    # Usiamo st.page_link direttamente dentro la colonna, lo stile CSS lo farà sembrare una card
    st.page_link(
        "pages/1_Bundle_Set_Images_Creator.py",
        label="### Bundle & Set Images Creator", # Titolo dentro la card virtuale
        icon="📦" # Icona dentro la card virtuale
        )
    # Descrizione SOTTO la card (fuori dal link)
    st.markdown('<p class="app-description">Automatically downloads, processes, and organizes images for product bundles and sets based on an Akeneo CSV report.</p>', unsafe_allow_html=True)


# --- Card App 2 ---
with col2:
    st.page_link(
        "pages/2_Repository_Image_Download_Renaming.py",
        label="### Repository Image Download & Renaming",
        icon="🖼️"
        )
    st.markdown('<p class="app-description">Downloads, resizes (1000x1000), and renames images from selected repositories (Switzerland, Farmadati) with the \'-h1\' suffix.</p>', unsafe_allow_html=True)

# --- Card App 3: Coming Soon (Non cliccabile) ---
with col3:
    # Card non cliccabile, solo visualizzazione
    st.markdown('<div class="app-card" style="opacity: 0.6; background-color: #e9ecef; cursor: default;">', unsafe_allow_html=True)
    st.markdown('<span class="icon">🚧</span>', unsafe_allow_html=True)
    st.markdown("### Coming Soon", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    # Descrizione per Coming Soon
    st.markdown('<p class="app-description">Future utilities and tools will be available here. Stay tuned for updates!</p>', unsafe_allow_html=True)


# --- Footer (Opzionale) ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("PDM Utility Hub - Internal Team Tool")
