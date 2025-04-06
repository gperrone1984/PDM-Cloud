# pages/2_Repository_Image_Download_Renaming.py
import streamlit as st
import pandas as pd
import csv
import os
import zipfile
from PIL import Image, ImageOps, ImageChops, UnidentifiedImageError
from io import BytesIO
import tempfile
import uuid
import asyncio
import aiohttp
import requests # Mantenuto per Farmadati sincrono
import xml.etree.ElementTree as ET # Per Farmadati XML
from zeep import Client, Transport, Settings # Per Farmadati SOAP
from zeep.wsse.username import UsernameToken
from zeep.cache import InMemoryCache
from zeep.plugins import HistoryPlugin
from urllib.parse import quote # Per URL encoding Farmadati

# --- Page Configuration ---
st.set_page_config(
    page_title="Image Download & Renaming",
    layout="centered" # O 'wide' se preferisci più spazio
)

# ----- LOGIN RIMOSSO -----

# ----- Custom CSS -----
# Mantieni solo stili specifici per questa app se possibile
st.markdown("""
    <style>
        h1, h2, h3 {color: #2c3e50; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;}
        /* Stili Sidebar specifici - dovrebbero funzionare bene */
        .sidebar-title {font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 0px;}
        .sidebar-subtitle {font-size: 16px; font-weight: bold; color: #2c3e50; margin-top: 10px; margin-bottom: 5px;}
        .sidebar-desc {font-size: 14px; color: #2c3e50; margin-top: 5px; margin-bottom: 15px; line-height: 1.4;}
        .stDownloadButton>button {
             background-color: #3498db;
             color: white; /* Testo bianco per contrasto */
             font-weight: bold;
             border: none; padding: 10px 24px;
             font-size: 16px;
             border-radius: 4px;
             cursor: pointer;
        }
         .stDownloadButton>button:hover {
             background-color: #2980b9; /* Colore leggermente più scuro al hover */
         }
        .server-select-label {font-size: 16px; font-weight: bold; margin-bottom: 5px; color: #2c3e50;}
        /* Modifica per applicare lo sfondo alla sidebar corretta */
        [data-testid="stSidebar"] > div:first-child {
            background-color: #ecf0f1;
            padding: 20px; /* Aggiunto padding */
            border-radius: 5px; /* Bordi arrotondati */
            }
    </style>
""", unsafe_allow_html=True)

# ----- Sidebar -----
st.sidebar.markdown("<div class='sidebar-title'>Image Download & Renaming</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='sidebar-subtitle'>What This App Does</div>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div class='sidebar-desc'>
- 📥 Downloads images from the selected source.<br>
- 🇨🇭 **Switzerland:** Uses Pharmacode via Documedis API.<br>
- 🇮🇹 **Farmadati:** Uses AIC code via Farmadati Web Services.<br>
- ✨ Processes images: trims whitespace, resizes to fit 1000x1000 (JPEG), adds white canvas, saves as JPEG (Quality 95).<br>
- 🏷️ Renames images using `{SKU}-h1.jpg` format.
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("<div class='server-select-label'>Select Image Source</div>", unsafe_allow_html=True)
server_country = st.sidebar.selectbox(
    "Source:", # Label più corta
    options=["Switzerland", "Farmadati"], # Rimosso Coming Soon per ora
    index=0,
    key="renaming_server_select" # Chiave specifica
    )

# ----- Initialize Session State (con prefisso) -----
if "renaming_app_session_id" not in st.session_state:
    st.session_state.renaming_app_session_id = str(uuid.uuid4())
if "renaming_uploader_key" not in st.session_state:
    st.session_state.renaming_uploader_key = str(uuid.uuid4())
# Flags di stato specifici per questa app
if "renaming_processing_done" not in st.session_state:
    st.session_state.renaming_processing_done = False
if "renaming_start_processing" not in st.session_state:
    st.session_state.renaming_start_processing = False


# ----- Clear Cache Button -----
if st.button("🧹 Clear Form and Reset"):
    # Resetta lo stato specifico di questa app
    keys_to_reset = [
        "renaming_processing_done", "renaming_start_processing",
        "renaming_zip_path_ch", "renaming_error_path_ch", # Specifici per Svizzera
        "renaming_zip_buffer_fd", "renaming_error_data_fd", # Specifici per Farmadati
        "manual_input_switzerland", "renaming_ch_file", # Input Svizzera
        "manual_input_farmadati", "renaming_fd_file", # Input Farmadati
        # "renaming_uploader_key" # Rigenerato sotto
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    # Rigenera la chiave dell'uploader per forzare il reset del widget file_uploader
    st.session_state.renaming_uploader_key = str(uuid.uuid4())
    st.success("Form cleared. You can now enter new SKUs or upload a new file.")
    st.rerun() # Ricarica per applicare le modifiche


# Function to combine SKUs from file and manual input
# @st.cache_data # Potremmo cacciare questa funzione? Forse no, dipende dall'uploader
def get_sku_list(uploaded_file_obj, manual_text, uploader_key):
    """
    Reads SKUs from an uploaded file (CSV or Excel) or manual text input.
    Looks for a column named 'sku' (case-insensitive).
    Returns a list of unique SKUs as strings.
    Cache depends on the uploader key to invalidate when file changes.
    """
    sku_list = []
    df_file = None

    # Process uploaded file
    if uploaded_file_obj is not None:
        try:
            file_name = uploaded_file_obj.name.lower()
            if file_name.endswith(".csv"):
                # Rileva delimitatore
                uploaded_file_obj.seek(0)
                sample_bytes = uploaded_file_obj.read(2048)
                uploaded_file_obj.seek(0)
                # Decodifica con fallback per evitare errori
                sample = sample_bytes.decode('utf-8', errors='replace')

                delimiter = ';' # Default a punto e virgola
                try:
                    # Prova i delimitatori comuni
                    sniffer = csv.Sniffer()
                    dialect = sniffer.sniff(sample, delimiters=';,\t|')
                    delimiter = dialect.delimiter
                    # st.info(f"Detected CSV delimiter: '{delimiter}'")
                except csv.Error:
                    # st.warning("Could not automatically detect delimiter, using ';'.")
                    pass # Usa il default
                except Exception:
                     # st.warning("Sniffer failed, using delimiter ';'")
                     pass # Usa il default

                # Leggi con dtype=str per evitare conversioni
                df_file = pd.read_csv(uploaded_file_obj, delimiter=delimiter, dtype=str, skipinitialspace=True, on_bad_lines='warn')

            elif file_name.endswith((".xlsx", ".xls")):
                df_file = pd.read_excel(uploaded_file_obj, dtype=str)
            else:
                st.error("Unsupported file type. Please upload CSV or Excel.")
                return [] # Ritorna lista vuota

            # Trova la colonna 'sku' (case-insensitive)
            sku_column = None
            for col in df_file.columns:
                # Rimuovi spazi extra dal nome colonna prima del confronto
                if col.strip().lower() == "sku":
                    sku_column = col
                    break

            if sku_column:
                # Estrai SKU, converti in stringa, rimuovi spazi e valori nulli/vuoti
                # Applica .astype(str) DOPO aver gestito i NaN per evitare errori
                file_skus = df_file[sku_column].dropna().astype(str).str.strip()
                sku_list.extend(file_skus[file_skus != ''].tolist())
            else:
                st.error("Column 'sku' not found in the uploaded file. Please ensure the column exists and is named correctly (case-insensitive).")
                return [] # Non possiamo procedere senza colonna SKU

        except pd.errors.ParserError as pe:
             st.error(f"Error parsing CSV file: {pe}. Check delimiter and file structure.")
             return []
        except Exception as e:
            st.error(f"Error reading file: {e}")
            # Non continuare se il file non può essere letto
            return []

    # Process manual input
    if manual_text:
        # Split lines, strip whitespace, filter empty lines
        manual_skus = [line.strip() for line in manual_text.splitlines() if line.strip()]
        sku_list.extend(manual_skus)

    # Rimuovi duplicati mantenendo l'ordine (approssimativamente) e pulisci
    seen = set()
    unique_sku_list = []
    for sku in sku_list:
        clean_sku = str(sku).strip()
        if clean_sku and clean_sku.lower() != 'nan' and clean_sku not in seen:
            unique_sku_list.append(clean_sku)
            seen.add(clean_sku)

    # if not unique_sku_list and (uploaded_file_obj or manual_text):
    #      st.warning("No valid, unique SKUs found in the provided input after cleaning.")

    return unique_sku_list

# Funzione comune per processare e salvare immagine (usata da entrambi)
def process_and_save_image(original_sku, image_bytes, download_folder):
    """Processes image: opens, checks, trims, resizes, adds canvas, saves as JPEG."""
    try:
        img = Image.open(BytesIO(image_bytes))
        # Controllo immagine vuota/nera/bianca
        if img.mode != 'L': gray_img = img.convert('L')
        else: gray_img = img
        extrema = gray_img.getextrema()
        if extrema == (0, 0): raise ValueError("Image is completely black")
        if extrema == (255, 255): raise ValueError("Image is completely white")

        img = ImageOps.exif_transpose(img) # Corregge orientamento

        # Trim whitespace
        bg = Image.new(img.mode, img.size, (255, 255, 255)) # Assume sfondo bianco
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if bbox:
             # Margine opzionale
             bbox = (max(0, bbox[0]-2), max(0, bbox[1]-2),
                    min(img.width, bbox[2]+2), min(img.height, bbox[3]+2))
             img = img.crop(bbox)
        # else: immagine è tutta bianca o non ha bordi

        if img.width == 0 or img.height == 0: raise ValueError("Image became empty after trimming")

        # Ridimensiona mantenendo aspect ratio per stare in 1000x1000
        img.thumbnail((1000, 1000), Image.LANCZOS)

        # Crea canvas bianco 1000x1000 e incolla al centro
        canvas = Image.new("RGB", (1000, 1000), (255, 255, 255))
        offset_x = (1000 - img.width) // 2
        offset_y = (1000 - img.height) // 2
        canvas.paste(img, (offset_x, offset_y))

        # Salva come JPEG con suffisso -h1
        new_filename = f"{original_sku}-h1.jpg"
        img_path = os.path.join(download_folder, new_filename)
        canvas.save(img_path, "JPEG", quality=95)
        return True # Successo

    except UnidentifiedImageError:
        raise ValueError("Cannot identify image file (corrupted/wrong format)")
    except ValueError as ve: # Propaga errori specifici (vuota, nera, bianca, trim vuoto)
        raise ve
    except Exception as e:
        raise RuntimeError(f"Error during image processing: {e}")


# ======================================================
# SECTION: Switzerland
# ======================================================
if server_country == "Switzerland":
    st.header("🇨🇭 Switzerland Image Processing (Documedis)")
    st.markdown("""
    **Instructions:**
    1.  Provide SKUs (Pharmacodes) via file upload (CSV/Excel with `sku` column) or paste them below.
    2.  The app downloads images using the Pharmacode (e.g., `CH012345` -> `12345`).
    3.  Images are processed (trimmed, resized, centered on 1000x1000 white canvas) and saved as `{SKU}-h1.jpg`.
    4.  Click **Search & Process Images**.
    """)

    # Input Utente
    manual_input_ch = st.text_area("Paste SKUs (Pharmacodes) here (one per line):", key="manual_input_switzerland")
    uploaded_file_ch = st.file_uploader(
        "Or Upload File (Excel/CSV with 'sku' column)",
        type=["xlsx", "csv"],
        key=st.session_state.renaming_uploader_key # Usa la chiave per reset
        )

    # Pulsante Avvio
    if st.button("Search & Process Images", key="process_switzerland_button"):
         st.session_state.renaming_start_processing = True
         st.session_state.renaming_processing_done = False
         # Resetta risultati precedenti
         if "renaming_zip_path_ch" in st.session_state: del st.session_state.renaming_zip_path_ch
         if "renaming_error_path_ch" in st.session_state: del st.session_state.renaming_error_path_ch

    # Logica di Processamento Svizzera
    if st.session_state.renaming_start_processing and not st.session_state.renaming_processing_done:

        sku_list_ch = get_sku_list(uploaded_file_ch, manual_input_ch, st.session_state.renaming_uploader_key)

        if not sku_list_ch:
            st.warning("No valid SKUs provided. Please upload a file or paste SKUs.")
            st.session_state.renaming_start_processing = False # Interrompi
        else:
            st.info(f"Found {len(sku_list_ch)} unique SKUs to process for Switzerland.")
            error_list_ch = []  # Lista per tuple (sku, reason)
            total_count_ch = len(sku_list_ch)
            progress_bar_ch = st.progress(0, text="Starting Documedis image processing...")

            # --- Funzioni specifiche per Svizzera ---
            def get_image_url_ch(product_code):
                pharmacode = str(product_code).strip()
                if pharmacode.upper().startswith("CH"):
                    pharmacode = pharmacode[2:].lstrip("0")
                else:
                    pharmacode = pharmacode.lstrip("0")
                if not pharmacode: return None, "Invalid/Empty Pharmacode after cleaning"
                url = f"https://documedis.hcisolutions.ch/2020-01/api/products/image/PICFRONT3D/Pharmacode/{pharmacode}/F"
                return url, None

            async def fetch_and_process_ch(session, original_sku, download_folder):
                """Fetches image from Documedis, processes it, handles errors."""
                image_url, error_msg = get_image_url_ch(original_sku)
                if error_msg:
                    error_list_ch.append((original_sku, error_msg))
                    return

                try:
                    async with session.get(image_url, timeout=30) as response:
                        if response.status == 200:
                            content = await response.read()
                            if not content:
                                 error_list_ch.append((original_sku, "Downloaded empty content"))
                                 return
                            # Esegui processamento in un thread separato
                            try:
                                success = await asyncio.to_thread(process_and_save_image, original_sku, content, download_folder)
                                if not success: # Errore gestito internamente a process_and_save
                                    # L'errore specifico dovrebbe essere già stato loggato o sollevato
                                    error_list_ch.append((original_sku,"Processing failed (check warnings)"))
                            except (ValueError, RuntimeError) as proc_e: # Cattura errori da process_and_save
                                 error_list_ch.append((original_sku, f"Processing error: {proc_e}"))
                            except Exception as generic_proc_e:
                                 error_list_ch.append((original_sku, f"Unexpected processing error: {generic_proc_e}"))

                        elif response.status == 404:
                             error_list_ch.append((original_sku, "Image not found (404)"))
                        else:
                            error_list_ch.append((original_sku, f"HTTP Error {response.status}"))

                except asyncio.TimeoutError:
                     error_list_ch.append((original_sku, "Download timeout"))
                except aiohttp.ClientError as e:
                     error_list_ch.append((original_sku, f"Network error: {e}"))
                except Exception as e:
                     error_list_ch.append((original_sku, f"Unexpected error: {e}"))


            async def process_all_images_ch(download_folder):
                """Manages concurrent downloads and processing for Switzerland."""
                connector = aiohttp.TCPConnector(limit=50)
                async with aiohttp.ClientSession(connector=connector) as session:
                    tasks = [fetch_and_process_ch(session, sku, download_folder) for sku in sku_list_ch]
                    processed_count = 0
                    for f in asyncio.as_completed(tasks):
                        await f # Aspetta che il task finisca
                        processed_count += 1
                        progress = processed_count / total_count_ch
                        progress_bar_ch.progress(progress, text=f"Processed {processed_count}/{total_count_ch} SKUs...")
                progress_bar_ch.progress(1.0, text="Documedis processing complete!")


            # --- Esecuzione del Processamento Asincrono ---
            with st.spinner("Downloading and processing Documedis images..."):
                 with tempfile.TemporaryDirectory() as temp_download_folder:
                    asyncio.run(process_all_images_ch(temp_download_folder))

                    # --- Creazione ZIP ---
                    zip_path_ch = None # Inizializza a None
                    processed_files_exist = any(f.is_file() for f in os.scandir(temp_download_folder))

                    if processed_files_exist:
                        # Usa un file temporaneo nominato per lo zip
                        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip_file:
                            zip_path_ch = tmp_zip_file.name
                        try:
                            with zipfile.ZipFile(zip_path_ch, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                for item in os.listdir(temp_download_folder):
                                    item_path = os.path.join(temp_download_folder, item)
                                    if os.path.isfile(item_path):
                                        zipf.write(item_path, arcname=item)
                            st.session_state["renaming_zip_path_ch"] = zip_path_ch # Salva percorso valido
                            st.success(f"Successfully processed and zipped images.")
                        except Exception as e:
                             st.error(f"Error creating ZIP file: {e}")
                             if zip_path_ch and os.path.exists(zip_path_ch): os.remove(zip_path_ch)
                             st.session_state["renaming_zip_path_ch"] = None # Resetta path
                    else:
                         st.warning("No images were successfully processed. ZIP file not created.")
                         st.session_state["renaming_zip_path_ch"] = None


                    # --- Creazione CSV Errori ---
                    error_path_ch = None # Inizializza a None
                    if error_list_ch:
                        st.warning(f"{len(error_list_ch)} SKUs could not be processed. See error list.")
                        error_df_ch = pd.DataFrame(error_list_ch, columns=["SKU", "Reason"])
                        error_df_ch = error_df_ch.drop_duplicates().sort_values(by="SKU") # Rimuovi duplicati e ordina
                        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", newline="", encoding="utf-8-sig") as tmp_error_file:
                            error_df_ch.to_csv(tmp_error_file, index=False, sep=';') # Usa ; come separatore
                            error_path_ch = tmp_error_file.name
                        st.session_state["renaming_error_path_ch"] = error_path_ch # Salva percorso
                    else:
                        st.info("All SKUs processed successfully or no errors encountered.")
                        st.session_state["renaming_error_path_ch"] = None

            # Fine processamento Svizzera
            st.session_state["renaming_processing_done"] = True
            st.session_state.renaming_start_processing = False # Resetta il trigger


    # --- Sezione Download Svizzera ---
    if st.session_state.get("renaming_processing_done", False) and server_country == "Switzerland":
        st.markdown("---")
        st.subheader("Download Results (Switzerland)")
        col1_ch_dl, col2_ch_dl = st.columns(2)

        with col1_ch_dl:
            zip_path_to_download = st.session_state.get("renaming_zip_path_ch")
            if zip_path_to_download and os.path.exists(zip_path_to_download):
                with open(zip_path_to_download, "rb") as fp_zip:
                    st.download_button(
                        label="Download Images (ZIP)",
                        data=fp_zip,
                        file_name=f"switzerland_images_{st.session_state.renaming_app_session_id[:8]}.zip",
                        mime="application/zip",
                        key="dl_ch_zip"
                    )
                # Considera di rimuovere il file temp dopo il download? O lasciarlo?
                # Se si rimuove, l'utente non può scaricarlo di nuovo senza riprocessare.
                # os.remove(zip_path_to_download)
            else:
                 st.info("No image ZIP file available for download.")

        with col2_ch_dl:
            error_path_to_download = st.session_state.get("renaming_error_path_ch")
            if error_path_to_download and os.path.exists(error_path_to_download):
                 with open(error_path_to_download, "rb") as fp_err:
                     st.download_button(
                        label="Download Error List (CSV)",
                        data=fp_err,
                        file_name=f"errors_switzerland_{st.session_state.renaming_app_session_id[:8]}.csv",
                        mime="text/csv",
                        key="dl_ch_err"
                    )
                 # os.remove(error_path_to_download) # Rimuovere?
            else:
                st.info("No error list available for download.")


# ======================================================
# SECTION: Farmadati
# ======================================================
elif server_country == "Farmadati":
    st.header("🇮🇹 Farmadati Image Processing (Italy)")
    st.markdown("""
    **Instructions:**
    1.  Provide SKUs (AIC codes) via file upload (CSV/Excel with `sku` column) or paste them below.
    2.  The app fetches Farmadati data to map AIC to image names, then downloads images.
    3.  Images are processed (trimmed, resized, centered on 1000x1000 white canvas) and saved as `{SKU}-h1.jpg`.
    4.  Click **Search & Process Images**.
    """)
    st.warning("Farmadati processing requires downloading a mapping file and can be slower.")

    # Credenziali Farmadati (da st.secrets se disponibile)
    # Metti le tue credenziali reali qui o in secrets.toml
    FARMADATI_USERNAME = st.secrets.get("FARMADATI_USERNAME", "YOUR_USERNAME")
    FARMADATI_PASSWORD = st.secrets.get("FARMADATI_PASSWORD", "YOUR_PASSWORD")
    WSDL_URL = 'http://webservices.farmadati.it/WS2/FarmadatiItaliaWebServicesM2.svc?wsdl'
    DATASET_CODE = "TDZ" # Dataset per mapping AIC -> Nome immagine

    # Input Utente
    manual_input_fd = st.text_area("Paste SKUs (AIC codes) here (one per line):", key="manual_input_farmadati")
    uploaded_file_fd = st.file_uploader(
        "Or Upload File (Excel/CSV with 'sku' column)",
        type=["xlsx", "csv"],
        key=st.session_state.renaming_uploader_key # Usa la chiave per reset
        )

    # Pulsante Avvio
    if st.button("Search & Process Images", key="process_farmadati_button"):
        if FARMADATI_USERNAME == "YOUR_USERNAME" or FARMADATI_PASSWORD == "YOUR_PASSWORD":
             st.error("Farmadati credentials not configured. Please set them in the code or Streamlit secrets.")
        else:
            st.session_state.renaming_start_processing = True
            st.session_state.renaming_processing_done = False
            # Resetta risultati precedenti
            if "renaming_zip_buffer_fd" in st.session_state: del st.session_state.renaming_zip_buffer_fd
            if "renaming_error_data_fd" in st.session_state: del st.session_state.renaming_error_data_fd

    # Logica Processamento Farmadati
    if st.session_state.renaming_start_processing and not st.session_state.renaming_processing_done:

        sku_list_fd = get_sku_list(uploaded_file_fd, manual_input_fd, st.session_state.renaming_uploader_key)

        if not sku_list_fd:
            st.warning("No valid SKUs provided. Please upload a file or paste SKUs.")
            st.session_state.renaming_start_processing = False # Interrompi
        else:
            st.info(f"Found {len(sku_list_fd)} unique SKUs to process for Farmadati.")
            progress_bar_fd = st.progress(0, text="Initializing Farmadati connection...")

            # --- Funzioni specifiche per Farmadati ---
            @st.cache_resource(ttl=3600) # Cache mapping per 1 ora
            def get_farmadati_mapping(_username, _password, _wsdl, _dataset_code):
                """Downloads and parses the Farmadati dataset TDZ."""
                st.info(f"Fetching Farmadati dataset '{_dataset_code}' (may take a minute)...")
                history = HistoryPlugin()
                transport = Transport(cache=InMemoryCache())
                settings = Settings(strict=False, xml_huge_tree=True, timeout=180) # Timeout più lungo
                try:
                    client = Client(wsdl=_wsdl, wsse=UsernameToken(_username, _password), transport=transport, plugins=[history], settings=settings)
                    response = client.service.GetDataSet(_username, _password, _dataset_code, "GETRECORDS", 1)
                except Exception as e:
                    st.error(f"Failed to connect/fetch Farmadati WSDL/DataSet: {e}")
                    st.stop()

                if response.CodEsito != "OK" or response.ByteListFile is None:
                    st.error(f"Farmadati Error fetching dataset: {response.CodEsito} - {response.DescEsito}")
                    st.stop()

                st.info("Dataset downloaded, parsing XML...")
                code_to_image_map = {}
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        zip_path = os.path.join(tmp_dir, f"{_dataset_code}.zip")
                        with open(zip_path, "wb") as f: f.write(response.ByteListFile)
                        with zipfile.ZipFile(zip_path, 'r') as z:
                            xml_filename = next((name for name in z.namelist() if name.upper().endswith('.XML')), None)
                            if not xml_filename: raise FileNotFoundError("No XML file in Farmadati ZIP")
                            z.extract(xml_filename, tmp_dir)
                            xml_full_path = os.path.join(tmp_dir, xml_filename)

                        # Parsing XML efficiente
                        context = ET.iterparse(xml_full_path, events=('end',))
                        count = 0
                        for event, elem in context:
                            if elem.tag == 'RECORD':
                                aic_elem = elem.find('FDI_T218') # AIC Code
                                img_name_elem = elem.find('FDI_T438') # Image File Name
                                if aic_elem is not None and img_name_elem is not None and aic_elem.text and img_name_elem.text:
                                    aic = aic_elem.text.strip().lstrip("0") # Pulisci AIC
                                    if aic: code_to_image_map[aic] = img_name_elem.text.strip()
                                elem.clear()
                                count += 1
                                if count % 10000 == 0: st.info(f"Parsed {count} records...") # Feedback per parsing lungo

                        if not code_to_image_map: raise ValueError("Mapping dictionary is empty after parsing.")
                        st.success(f"Farmadati mapping loaded ({len(code_to_image_map)} entries).")
                        return code_to_image_map

                except Exception as e:
                    st.error(f"Error processing Farmadati dataset XML: {e}")
                    st.stop()

            # --- Esecuzione Processamento Farmadati ---
            try:
                aic_to_image_map = get_farmadati_mapping(FARMADATI_USERNAME, FARMADATI_PASSWORD, WSDL_URL, DATASET_CODE)
                if not aic_to_image_map:
                     st.error("Failed to load AIC-to-Image mapping. Cannot proceed.")
                     st.session_state.renaming_start_processing = False
                     st.stop()

                total_fd = len(sku_list_fd)
                error_list_fd = [] # Lista tuple (sku, reason)
                processed_count_fd = 0
                zip_buffer_fd = BytesIO() # ZIP in memoria

                with zipfile.ZipFile(zip_buffer_fd, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
                    with requests.Session() as http_session: # Riusa connessione HTTP
                        for i, sku in enumerate(sku_list_fd):
                            progress_text = f"Processing Farmadati SKU {i+1}/{total_fd}: {sku}"
                            progress_bar_fd.progress((i + 1) / total_fd, text=progress_text)

                            # Pulisci SKU (AIC): rimuovi 'IT', rimuovi zeri iniziali
                            clean_sku = str(sku).strip()
                            if clean_sku.upper().startswith("IT"):
                                clean_sku = clean_sku[2:]
                            clean_sku = clean_sku.lstrip("0")

                            if not clean_sku:
                                error_list_fd.append((sku, "Invalid/Empty AIC after cleaning"))
                                continue

                            image_filename = aic_to_image_map.get(clean_sku)
                            if not image_filename:
                                error_list_fd.append((sku, "AIC not found in Farmadati mapping"))
                                continue

                            # Costruisci URL GetDoc (con URL encoding del nome file)
                            safe_filename = quote(image_filename)
                            image_url = f"https://ws.farmadati.it/WS_DOC/GetDoc.aspx?accesskey={FARMADATI_PASSWORD}&tipodoc=Z&nomefile={safe_filename}"

                            try:
                                response = http_session.get(image_url, timeout=45) # Timeout più lungo per Farmadati
                                response.raise_for_status() # Controlla errori HTTP

                                if not response.content:
                                    error_list_fd.append((sku, "Downloaded empty content"))
                                    continue

                                # Processa immagine (usa la funzione comune)
                                processed_image_buffer = BytesIO() # Buffer per l'immagine processata
                                try:
                                    process_and_save_image(sku, response.content, None) # Passa None per folder, ritorna buffer? No, la funzione salva su file... Modifichiamo?
                                    # Modifichiamo process_and_save_image per ritornare BytesIO se no folder
                                    # Riprogettazione rapida: creiamo la cartella temp qui
                                    with tempfile.TemporaryDirectory() as single_img_temp_dir:
                                         process_and_save_image(sku, response.content, single_img_temp_dir)
                                         # Leggi il file appena salvato e aggiungilo allo zip
                                         saved_file_path = os.path.join(single_img_temp_dir, f"{sku}-h1.jpg")
                                         if os.path.exists(saved_file_path):
                                             zipf.write(saved_file_path, arcname=f"{sku}-h1.jpg")
                                             processed_count_fd += 1
                                         else:
                                             # Questo non dovrebbe succedere se process_and_save non lancia eccezioni
                                             error_list_fd.append((sku, "Processing seemed ok, but file not saved"))

                                except (ValueError, RuntimeError) as proc_e:
                                     error_list_fd.append((sku, f"Processing error: {proc_e}"))
                                except Exception as generic_proc_e:
                                     error_list_fd.append((sku, f"Unexpected processing error: {generic_proc_e}"))


                            except requests.exceptions.RequestException as e:
                                reason = f"Network error: {e}"
                                if hasattr(e, 'response') and e.response is not None:
                                    if e.response.status_code == 404: reason = "Image not found on server (404)"
                                    else: reason = f"HTTP Error {e.response.status_code}"
                                elif isinstance(e, requests.exceptions.Timeout): reason = "Download timeout"
                                error_list_fd.append((sku, reason))
                            except Exception as e:
                                error_list_fd.append((sku, f"Unexpected error: {e}"))

                progress_bar_fd.progress(1.0, text="Farmadati processing complete!")

                # Salva risultati nello stato
                if processed_count_fd > 0:
                    zip_buffer_fd.seek(0)
                    st.session_state["renaming_zip_buffer_fd"] = zip_buffer_fd # Salva il buffer
                    st.success(f"Successfully processed {processed_count_fd} Farmadati images.")
                else:
                    st.warning("No Farmadati images were successfully processed.")
                    st.session_state["renaming_zip_buffer_fd"] = None

                if error_list_fd:
                    st.warning(f"{len(error_list_fd)} SKUs failed during Farmadati processing.")
                    error_df_fd = pd.DataFrame(error_list_fd, columns=["SKU", "Reason"])
                    error_df_fd = error_df_fd.drop_duplicates().sort_values(by="SKU")
                    csv_error_fd = error_df_fd.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                    st.session_state["renaming_error_data_fd"] = csv_error_fd # Salva i bytes del CSV
                else:
                    st.info("No errors reported during Farmadati processing.")
                    st.session_state["renaming_error_data_fd"] = None

            except Exception as e:
                 st.error(f"A critical error occurred during Farmadati setup or processing loop: {e}")
                 st.exception(e)

            # Fine processamento Farmadati
            st.session_state["renaming_processing_done"] = True
            st.session_state.renaming_start_processing = False # Resetta trigger

    # --- Sezione Download Farmadati ---
    if st.session_state.get("renaming_processing_done", False) and server_country == "Farmadati":
        st.markdown("---")
        st.subheader("Download Results (Farmadati)")
        col1_fd_dl, col2_fd_dl = st.columns(2)

        with col1_fd_dl:
             zip_data_fd = st.session_state.get("renaming_zip_buffer_fd") # Prendi il buffer
             if zip_data_fd:
                 st.download_button(
                    "Download Images (ZIP)",
                    data=zip_data_fd, # Passa il buffer direttamente
                    file_name=f"farmadati_images_{st.session_state.renaming_app_session_id[:8]}.zip",
                    mime="application/zip",
                    key="dl_fd_zip"
                 )
             else:
                 st.info("No Farmadati image ZIP available.")

        with col2_fd_dl:
            error_data_fd = st.session_state.get("renaming_error_data_fd") # Prendi i bytes del CSV
            if error_data_fd:
                 st.download_button(
                    "Download Error List (CSV)",
                    data=error_data_fd,
                    file_name=f"errors_farmadati_{st.session_state.renaming_app_session_id[:8]}.csv",
                    mime="text/csv",
                    key="dl_fd_err"
                 )
            else:
                 st.info("No Farmadati error list available.")
