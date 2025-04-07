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
    /* Imposta larghezza sidebar a 540px e FORZA con !important */
    [data-testid="stSidebar"] > div:first-child {
        width: 540px !important;
        min-width: 540px !important;
        max-width: 540px !important;
    }
    /* Nasconde la navigazione automatica generata da Streamlit nella sidebar */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* Rimosso sfondo forzato per l'AREA PRINCIPALE - Lascia gestire al tema */
    /* section.main { */
        /* background-color: #d8dfe6 !important; /* RIMOSSO */
    /* } */

    /* Rendi trasparente il contenitore interno e mantieni il padding */
    /* Questo permette allo sfondo del tema di essere visibile */
    div[data-testid="stAppViewContainer"] > section > div.block-container {
         background-color: transparent !important;
         padding: 2rem 1rem 1rem 1rem !important; /* Padding per contenuto */
         border-radius: 0 !important; /* Nessun bordo arrotondato interno */
    }
    .main .block-container {
         background-color: transparent !important;
         padding: 2rem 1rem 1rem 1rem !important;
         border-radius: 0 !important;
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
        width: 90%;
        min-height: 100px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04); /* Ombra leggera mantenuta */
        margin-bottom: 0.75rem;
        text-align: center;
        line-height: 1.4;
        transition: background-color 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        /* Rimossi color, background-color, border specifici per adattarsi al tema */
        /* color: #343a40; */ /* RIMOSSO */
        border: 1px solid var(--border-color, #cccccc); /* Usa variabile CSS se disponibile o fallback */
    }
     .app-button-link svg, .app-button-placeholder svg,
     .app-button-link .icon, .app-button-placeholder .icon {
         margin-right: 0.6rem;
         flex-shrink: 0;
     }
    .app-button-link > div[data-testid="stText"] > span:before {
        content: "" !important; margin-right: 0 !important;
    }

    /* Stile per bottoni cliccabili - Rimosso colore specifico */
    .app-button-link {
        /* background-color: #f5faff; */ /* RIMOSSO */
        /* border: 1px solid #c4daee; */ /* RIMOSSO - Usato fallback sopra */
        cursor: pointer; /* Mantenuto cursore */
    }
    .app-button-link:hover {
        /* background-color: #eaf2ff; */ /* RIMOSSO */
        /* border-color: #a9cce3; */ /* RIMOSSO */
        box-shadow: 0 2px 4px rgba(0,0,0,0.08); /* Effetto ombra su hover mantenuto */
        /* Streamlit gestirà il cambio colore di sfondo/bordo su hover in base al tema */
    }

    /* Stile Placeholder Coming Soon (non cliccabile) */
    .app-button-placeholder {
        /* background-color: #f1f3f5; */ /* RIMOSSO */
        opacity: 0.7; /* Opacità mantenuta per distinguerlo */
        cursor: default;
        box-shadow: none;
        /* color: #868e96; */ /* RIMOSSO - Lascia gestire al tema il colore testo "disabilitato" */
        border-style: dashed; /* Mantenuto stile tratteggiato per distinguerlo */
        /* border: 1px dashed #cccccc; */ /* RIMOSSO - Usato fallback sopra con stile dashed */
    }
     .app-button-placeholder .icon {
         font-size: 1.5em;
     }


    /* Stile per descrizione sotto i bottoni */
     .app-description {
        font-size: 0.9em;
        /* color: #343a40; */ /* RIMOSSO - Lascia gestire al tema */
        padding: 0 15px;
        text-align: justify;
        width: 90%;
        margin: 0 auto;
     }

    /* Aggiusta colore link nella sidebar per coerenza tema (opzionale ma consigliato) */
    [data-testid="stSidebar"] a:link, [data-testid="stSidebar"] a:visited {
        /* color: inherit; /* Eredita colore dal tema */
        text-decoration: none;
    }
    [data-testid="stSidebar"] a:hover {
        text-decoration: underline; /* O altro effetto hover desiderato */
    }


    </style>
    """,
    unsafe_allow_html=True
)

# --- Bottone per tornare all'Hub nella Sidebar ---
# Assicurati che il link usi st.page_link per una migliore integrazione
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
    # Usare st.page_link è preferibile per la navigazione interna
    # Ma manteniamo il tuo HTML customizzato per preservare lo stile esatto
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    # Nota: Il target="_self" è implicito con st.page_link, ma qui serve per l'<a> custom
    st.markdown('<a href="/Bundle_Set_Images_Creator" target="_self" class="app-button-link" data-testid="stPageLink">📦 Bundle & Set Images Creator</a>', unsafe_allow_html=True)
    st.markdown('<p class="app-description">Automatically downloads, processes, and organizes images for product bundles and sets.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    st.markdown('<div class="app-button-placeholder"><span class="icon">🚧</span> Coming Soon</div>', unsafe_allow_html=True)
    # Aggiunta descrizione anche per il placeholder se desiderato
    # st.markdown('<p class="app-description">Future application description here.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# --- Colonna 2: App Renaming ---
with col2:
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    st.markdown('<a href="/Repository_Image_Download_Renaming" target="_self" class="app-button-link" data-testid="stPageLink">🖼️ Repository Image Download & Renaming</a>', unsafe_allow_html=True)
    st.markdown('<p class="app-description">Downloads, resizes, and renames images from selected repositories (e.g. Switzerland, Farmadati).</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# --- Footer Modificato ---
st.markdown("---")
st.caption("v.1.0")
