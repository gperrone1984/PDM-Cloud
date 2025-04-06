# pages/3_Coming_Soon.py
import streamlit as st

st.set_page_config(
    page_title="Coming Soon",
    page_icon="🚧",
    initial_sidebar_state="expanded" # Sidebar visibile
)

# --- CSS Globale per nascondere navigazione default e impostare larghezza sidebar ---
# *** COPIA ESATTA DEL BLOCCO CSS DA pdm_hub.py ***
st.markdown(
    """
    <style>
    /* Imposta larghezza sidebar e FORZA con !important */
    [data-testid="stSidebar"] > div:first-child {
        width: 550px !important;
        min-width: 550px !important; /* Aggiunto per robustezza */
        max-width: 550px !important; /* Aggiunto per robustezza */
    }
    /* Nasconde la navigazione automatica generata da Streamlit nella sidebar */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* Sfondo per il contenitore principale - FORZATO con !important */
    /* Target più specifico e !important */
    div[data-testid="stAppViewContainer"] > section > div.block-container {
         background-color: #ccd6e0 !important; /* Blu/Grigio chiaro richiesto */
         padding: 2rem 1rem 1rem 1rem !important; /* Padding */
         border-radius: 0.5rem !important;
    }
    /* Fallback meno specifico se il precedente non funziona */
    .main .block-container {
         background-color: #ccd6e0 !important;
         padding: 2rem 1rem 1rem 1rem !important;
         border-radius: 0.5rem !important;
    }


    /* Stile base per i bottoni/placeholder delle app (dall'hub) */
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
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        margin-bottom: 0.75rem;
        text-align: center;
        line-height: 1.4;
        transition: background-color 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        color: #343a40; /* Testo grigio scuro */
    }
     .app-button-link svg, .app-button-placeholder svg,
     .app-button-link .icon, .app-button-placeholder .icon {
         margin-right: 0.6rem;
         flex-shrink: 0;
     }
    .app-button-link > div[data-testid="stText"] > span:before {
        content: "" !important; margin-right: 0 !important;
    }

    /* Colore UNICO per entrambi i bottoni cliccabili (dall'hub) */
    .app-button-link {
        background-color: #f5faff; /* Azzurro quasi impercettibile */
        border: 1px solid #c4daee; /* Bordo coordinato */
    }
    .app-button-link:hover {
        background-color: #eaf2ff; /* Azzurro leggermente più scuro */
        border-color: #a9cce3;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        cursor: pointer;
    }

    /* Stile Placeholder Coming Soon (non cliccabile) (dall'hub) */
    .app-button-placeholder {
        background-color: #f1f3f5;
        opacity: 0.7;
        cursor: default;
        box-shadow: none;
        color: #868e96;
        border: 1px dashed #cccccc;
    }
     .app-button-placeholder .icon {
         font-size: 1.5em;
     }


    /* Stile per descrizione sotto i bottoni (dall'hub) */
     .app-description {
        font-size: 0.9em;
        color: #343a40; /* Testo più scuro per leggibilità */
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


# --- Contenuto Pagina ---
st.title("🚧 Coming Soon")
st.image("https://static.streamlit.io/examples/owl.jpg", caption="Work in progress!", width=300)
st.info("This section is currently under development. New utilities will be added here in the future.")
st.balloons()
