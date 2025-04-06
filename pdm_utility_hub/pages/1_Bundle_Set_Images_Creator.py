# pages/1_Bundle_Set_Images_Creator.py
import streamlit as st
import streamlit.components.v1 as components
import os
import aiohttp
import asyncio
import pandas as pd
import shutil
import uuid
import time
from io import BytesIO
from PIL import Image, ImageChops
from cryptography.fernet import Fernet

st.set_page_config(
    page_title="Bundle & Set Creator",
    # layout="wide", # RIMOSSO per usare il default (centered)
    initial_sidebar_state="expanded"
)

# --- CSS Globale per nascondere navigazione default e impostare larghezza sidebar ---
# *** COPIA ESATTA DEL BLOCCO CSS DA pdm_hub.py (con nuovo background) ***
st.markdown(
    """
    <style>
    /* Imposta larghezza sidebar e FORZA con !important */
    [data-testid="stSidebar"] > div:first-child {
        width: 550px !important;
        min-width: 550px !important;
        max-width: 550px !important;
    }
    /* Nasconde la navigazione automatica generata da Streamlit nella sidebar */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* Sfondo per il contenitore principale - NUOVO COLORE FORZATO */
    div[data-testid="stAppViewContainer"] > section > div.block-container {
         background-color: #d8dfe6 !important; /* NUOVO COLORE */
         padding: 2rem 1rem 1rem 1rem !important;
         border-radius: 0.5rem !important;
    }
    .main .block-container {
         background-color: #d8dfe6 !important; /* NUOVO COLORE */
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
        color: #343a40;
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
        background-color: #f5faff;
        border: 1px solid #c4daee;
    }
    .app-button-link:hover {
        background-color: #eaf2ff;
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
        color: #343a40;
        padding: 0 15px;
        text-align: justify;
        width: 90%;
        margin: 0 auto;
     }

     /* Stili specifici di QUESTA app (Bundle Creator) */
     .stButton > button {
        background-color: #8984b3;
        color: white;
        border: none;
        padding: 8px 16px;
        text-align: center;
        font-size: 16px;
        border-radius: 8px;
        cursor: pointer;
    }
    .stButton > button:hover {
        background-color: #625e8a;
    }
    .stDownloadButton > button {
        background-color: #acbf9b;
        color: white;
        border: none;
        padding: 8px 16px;
        text-align: center;
        font-size: 16px;
        border-radius: 8px;
        cursor: pointer;
    }
    .stDownloadButton > button:hover {
        background-color: #97a888;
    }
    /* Sovrascrive il padding del background per questa pagina specifica */
    /* Dato che ora è layout centered, potremmo non aver bisogno di sovrascrivere */
    /* .main .block-container{
        padding-top: 1rem !important;
        background-color: transparent !important;
        border-radius: 0 !important;
    } */

    </style>
    """,
    unsafe_allow_html=True
)

# --- Bottone per tornare all'Hub nella Sidebar ---
st.sidebar.page_link("pdm_hub.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---") # Separatore opzionale

# ---------------------- Session State Management ----------------------
if "bundle_creator_session_id" not in st.session_state:
    st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())

# ---------------------- LOGIN RIMOSSO ----------------------

# ---------------------- Begin Main App Code ----------------------
# ... (Il resto del codice Python dell'app Bundle Creator rimane invariato) ...
# ... (da session_id = st.session_state["bundle_creator_session_id"] in poi) ...

# --- Titolo Modificato ---
st.title("PDM Bundle&Set Image Creator")

# --- How to Use Modificato ---
st.markdown(
    """
    **How to use:**

    1. Create a Quick Report in Akeneo containing the list of products.
    2. Select the following options:
       - File Type: CSV - All Attributes or Grid Context (for Grid Context, select ID and PZN included in the set) - With Codes - Without Media
    3. **Choose the language for language specific photos:** (if needed)
    4. **Choose bundle layout:** (Horizontal, Vertical, or Automatic)
    5. Click **Process CSV** to start the process.
    6. Download the files.
    7. **Before starting a new process, click on Clear Cache and Reset Data.**
    """
)

# --- Bottone Reset SPOSTATO QUI ---
if st.button("🧹 Clear Cache and Reset Data"):
    keys_to_remove = [k for k in st.session_state if k.startswith('bundle_') or k in ['fallback_ext', 'encryption_key', 'zip_data', 'bundle_list_data', 'missing_images_data', 'missing_images_df', 'processing_complete_bundle', 'file_uploader']]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    st.cache_data.clear()
    st.cache_resource.clear()
    # Assicurati che la funzione sia definita
    if 'clear_old_data' in locals():
        clear_old_data()
    st.success("Data cleared.")
    st.rerun()

# --- Sidebar Content Modificato ---
st.sidebar.header("What This App Does")
st.sidebar.markdown(
    """
    - ❓ **Automated Bundle&Set Creation:** Automatically create product bundles and mixed set by downloading and organizing images;
    - 🔎 **Language Selection:** Choose the language if you have language-specific photos. NL-FR, DE, FR;
    - 🔎 **Choose the layout for double/triple bundles:** Automatic, Horizontal or Vertical;
    - ✏️ **Dynamic Processing:** Combine images (double/triple) with proper resizing;
    - ✏️ **Rename images** using the specific bundle&set code (e.g. -h1, -p1-fr, -p1-nl, etc);
    - ❌ **Error Logging:** Missing images are logged in a CSV;
    - 📥 **Download:** Get a ZIP with all processed images and reports;
    - 🌐 **Interactive Preview:** Preview and download individual product images from the sidebar.
    """, unsafe_allow_html=True
)

# --- Sidebar Preview (Originale) ---
st.sidebar.header("Product Image Preview")
product_code_preview = st.sidebar.text_input("Enter Product Code:", key="preview_pzn_bundle")
selected_extension = st.sidebar.selectbox("Select Image Extension:", [str(i) for i in range(1, 19)], key="sidebar_ext_bundle")
with st.sidebar:
    col_button, col_spinner = st.columns([2, 1])
    show_image = col_button.button("Show Image", key="show_preview_bundle")
    spinner_placeholder = col_spinner.empty()

if show_image and product_code_preview:
    with spinner_placeholder:
        with st.spinner("Processing..."):
            pzn_url = product_code_preview
            if pzn_url.startswith(('1', '0')): pzn_url = f"D{pzn_url}"
            preview_url = f"https://cdn.shop-apotheke.com/images/{pzn_url}-p{selected_extension}.jpg"
            image_data = None
            try:
                import requests
                response = requests.get(preview_url, stream=True, timeout=10)
                if response.status_code == 200:
                     image_data = response.content
            except Exception:
                pass
    if image_data:
        try:
            image = Image.open(BytesIO(image_data))
            st.sidebar.image(image, caption=f"Product: {product_code_preview} (p{selected_extension})", use_container_width=True)
            st.sidebar.download_button(
                label="Download Image",
                data=image_data,
                file_name=f"{product_code_preview}-p{selected_extension}.jpg",
                mime="image/jpeg",
                key="dl_preview_bundle"
            )
        except Exception:
             st.sidebar.error("Could not display preview image.")
    else:
        st.sidebar.error(f"No image found for {product_code_preview} with -p{selected_extension}.jpg")

# --- Main Area UI (Originale) ---
uploaded_file = st.file_uploader("**Upload CSV File**", type=["csv"], key="file_uploader")
if uploaded_file:
    col1, col2 = st.columns(2)
    with col1:
        fallback_language = st.selectbox("**Choose the language for language specific photos:**", options=["None", "FR", "DE", "NL FR"], index=0, key="lang_select_bundle")
    with col2:
        layout_choice = st.selectbox("**Choose bundle layout:**", options=["Horizontal", "Vertical", "Automatic"], index=2, key="layout_select_bundle")

    if fallback_language == "NL FR":
        st.session_state["fallback_ext"] = "NL FR"
    elif fallback_language != "None":
        st.session_state["fallback_ext"] = f"1-{fallback_language.lower()}"
    else:
        st.session_state["fallback_ext"] = None

    if st.button("Process CSV", key="process_csv_bundle"):
        start_time = time.time()
        progress_bar = st.progress(0, text="Starting processing...")
        try:
            # Assicurati che la funzione sia definita
            if 'process_file_async' not in locals():
                 # Aggiungi una definizione vuota o un messaggio di errore se non definita
                 st.error("Processing function not found!")
                 st.stop()

            zip_data, missing_images_data, missing_images_df, bundle_list_data = asyncio.run(process_file_async(uploaded_file, progress_bar, layout=layout_choice))
            progress_bar.empty()
            elapsed_time = time.time() - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            st.success(f"Processing finished in {minutes}m {seconds}s.")

            st.session_state["zip_data"] = zip_data
            st.session_state["bundle_list_data"] = bundle_list_data
            st.session_state["missing_images_data"] = missing_images_data
            st.session_state["missing_images_df"] = missing_images_df
            st.session_state["processing_complete_bundle"] = True

        except Exception as e:
             progress_bar.empty()
             st.error(f"An error occurred: {e}")
             st.session_state["processing_complete_bundle"] = False


# --- Sezione Download Modificata (Senza Titolo, Verticale) ---
if st.session_state.get("processing_complete_bundle", False):
    st.markdown("---") # Separatore

    # Bottone Download ZIP
    if st.session_state.get("zip_data"):
        st.download_button(
            label="Download Bundle Images (ZIP)",
            data=st.session_state["zip_data"],
            file_name=f"BundleSet_{session_id}.zip",
            mime="application/zip",
            key="dl_zip_bundle_v"
        )
    else:
        st.info("No ZIP file generated.")

    # Bottone Download Lista Bundle
    if st.session_state.get("bundle_list_data"):
        st.download_button(
            label="Download Bundle List (CSV)",
            data=st.session_state["bundle_list_data"],
            file_name=f"bundle_list_{session_id}.csv",
            mime="text/csv",
            key="dl_list_bundle_v"
        )
    else:
        st.info("No bundle list generated.")

    # Sezione Immagini Mancanti
    missing_df = st.session_state.get("missing_images_df")
    if missing_df is not None and not missing_df.empty:
        st.markdown("---") # Separatore prima della tabella errori
        st.warning(f"{len(missing_df)} bundles with missing images:")
        st.dataframe(missing_df.head(), use_container_width=True) # Mostra tabella
        # Bottone Download Lista Errori
        if st.session_state.get("missing_images_data"):
            st.download_button(
                label="Download Missing List (CSV)",
                data=st.session_state["missing_images_data"],
                file_name=f"missing_images_{session_id}.csv",
                mime="text/csv",
                key="dl_missing_bundle_v"
            )
    elif missing_df is not None: # Esiste ma è vuoto
         st.success("No missing images reported.")
