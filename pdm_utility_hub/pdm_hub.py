# pdm_hub.py
import streamlit as st
from pathlib import Path # Utile per i percorsi

# --- Page Configuration ---
st.set_page_config(
    page_title="PDM Utility Hub",
    page_icon="🛠️", # Puoi scegliere un'altra icona se preferisci
    layout="centered" # Centra il contenuto principale
)

# --- Styling personalizzato leggero (opzionale) ---
st.markdown("""
<style>
    /* Stile per le card delle app */
    .app-card {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        text-align: center;
        transition: box-shadow 0.3s ease-in-out;
        background-color: #f9f9f9; /* Sfondo leggermente diverso */
        height: 250px; /* Altezza fissa per allineamento */
        display: flex; /* Abilita Flexbox */
        flex-direction: column; /* Impila elementi verticalmente */
        justify-content: center; /* Centra contenuto verticalmente */
        align-items: center; /* Centra contenuto orizzontalmente */
    }
    .app-card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .app-card h3 { /* Stile per il titolo dentro la card */
        margin-top: 10px;
        margin-bottom: 10px;
        color: #333;
    }
    .app-card p { /* Stile per la descrizione dentro la card */
        font-size: 0.9em;
        color: #666;
        padding-left: 10px; /* Aggiungi padding laterale se necessario */
        padding-right: 10px;
    }
    .app-card .icon { /* Stile per l'icona */
         font-size: 2.5em; /* Dimensione icona */
         display: block; /* Assicura che vada a capo */
         margin-bottom: 10px;
    }
    /* Nasconde la freccia standard di st.page_link per un look più pulito da bottone/card */
    a[data-testid="stPageLink"] > div[data-testid="stText"] > span:before {
        content: "" !important; /* Rimuove la freccia */
        margin-right: 0 !important;
    }
     a[data-testid="stPageLink"] {
        text-decoration: none; /* Rimuove sottolineatura link */
     }

    /* Nascondi la sidebar di default generata da Streamlit */
    /* ATTENZIONE: Questo nasconderà la navigazione! Usalo solo se vuoi SOLO le card centrali */
    /* [data-testid="stSidebar"] {
           display: none;
        } */
     /* Se vuoi nascondere la sidebar, potresti dover aggiustare il padding del main content */
     /* .main > div {
            padding-left: 1rem;
            padding-right: 1rem;
        } */

</style>
""", unsafe_allow_html=True)

# --- Header Principale ---
st.title("🛠️ PDM Utility Hub")
st.markdown("---")
st.markdown("Welcome to the Product Data Management Utility Hub. Select an application below to get started.")
st.markdown("<br>", unsafe_allow_html=True) # Aggiunge un po' di spazio

# --- Layout a Colonne per le Card ---
col1, col2, col3 = st.columns(3)

# --- Card App 1: Bundle & Set Images Creator ---
with col1:
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.markdown('<span class="icon">📦</span>', unsafe_allow_html=True)
    # Crea un link cliccabile che punta alla pagina specifica
    # Il percorso è relativo alla cartella 'pages'
    st.page_link(
        "pages/1_Bundle_Set_Images_Creator.py",
        label="### Bundle & Set Images Creator", # Usa Markdown per H3
        icon=None # Nasconde l'icona di default del link
        )
    st.markdown("""
    <p>
    Automatically downloads, processes, and organizes images
    for product bundles and sets based on an Akeneo CSV report.
    </p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# --- Card App 2: Repository Image Download & Renaming ---
with col2:
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.markdown('<span class="icon">🖼️</span>', unsafe_allow_html=True)
    st.page_link(
        "pages/2_Repository_Image_Download_Renaming.py",
        label="### Repository Image Download & Renaming",
        icon=None
        )
    st.markdown("""
    <p>
    Downloads, resizes (1000x1000), and renames images
    from selected repositories (Switzerland, Farmadati) with the '-h1' suffix.
    </p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Card App 3: Coming Soon (Non cliccabile) ---
with col3:
    # Stile inline per opacità se vuoi che sembri disabilitata
    st.markdown('<div class="app-card" style="opacity: 0.6; background-color: #e9ecef;">', unsafe_allow_html=True)
    st.markdown('<span class="icon">🚧</span>', unsafe_allow_html=True)
    st.markdown("### Coming Soon", unsafe_allow_html=True) # Solo testo, non un link
    st.markdown("""
    <p>
    Future utilities and tools will be available here. Stay tuned for updates!
    </p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Footer (Opzionale) ---
st.markdown("---")
st.caption("PDM Utility Hub - Internal Team Tool")

# NOTA: Non aggiungere st.sidebar... qui. Streamlit lo popolerà automaticamente (a meno che non lo nascondi con CSS).
