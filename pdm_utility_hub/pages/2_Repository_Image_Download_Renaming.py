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
import xml.etree.ElementTree as ET
import requests
from zeep import Client, Settings
from zeep.wsse.username import UsernameToken
from zeep.transports import Transport
from zeep.cache import InMemoryCache
from zeep.plugins import HistoryPlugin

st.set_page_config(
    page_title="Image Download & Renaming",
    layout="centered", # O 'wide'
    initial_sidebar_state="expanded" # Sidebar visibile
)

# --- CSS Globale per nascondere navigazione default e impostare larghezza sidebar ---
# Replicato qui per sicurezza
st.markdown("""
    <style>
        /* Imposta larghezza sidebar */
        [data-testid="stSidebar"] > div:first-child {
            width: 550px;
        }
        /* Nasconde la navigazione automatica generata da Streamlit nella sidebar */
        [data-testid="stSidebarNav"] {
            display: none;
        }

        /* Stili originali dell'app (mantenuti) */
        .main {background-color: #f9f9f9; }
        h1, h2, h3 {color: #2c3e50; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;}
        .sidebar-title {font-size: 32px; font-weight: bold; color: #2c3e50; margin-bottom: 0px;}
        .sidebar-subtitle {font-size: 18px; color: #2c3e50; margin-top: 10px; margin-bottom: 5px;}
        .sidebar-desc {font-size: 16px; color: #2c3e50; margin-top: 5px; margin-bottom: 20px;}
        .stDownloadButton>button {background-color: #3498db; color: black; font-weight: bold; border: none; padding: 10px 24px; font-size: 16px; border-radius: 4px;}
        .server-select-label {font-size: 20px; font-weight: bold; margin-bottom: 5px;}
        /* Applica sfondo originale alla sidebar */
        [data-testid="stSidebar"] > div:first-child {
             background-color: #ecf0f1;
             padding: 10px;
             }
    </style>
""", unsafe_allow_html=True)

# --- Bottone per tornare all'Hub nella Sidebar ---
st.sidebar.page_link("pdm_hub.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---") # Separatore opzionale

# ----- LOGIN RIMOSSO -----
# Il codice originale dell'app inizia qui sotto

# ----- Sidebar Content (Originale, ma dopo il bottone Hub) -----
st.sidebar.markdown("<div class='sidebar-title'>PDM Image Download and Renaming App</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='sidebar-subtitle'>What This App Does</div>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div class='sidebar-desc'>
- 📥 Downloads images from the selected server<br>
- 🔄 Resizes images to 1000x1000 in JPEG<br>
- 🏷️ Renames with a '-h1' suffix
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("<div class='server-select-label'>Select Server Country/Image Source</div>", unsafe_allow_html=True)
# Aggiungi chiave univoca al selectbox
server_country = st.sidebar.selectbox("", options=["Switzerland", "Farmadati", "coming soon"], index=0, key="server_select_renaming")

# ----- Session State & Clear Cache (Originale) -----
# Usa chiavi specifiche per questa app
if "renaming_uploader_key" not in st.session_state:
    st.session_state.renaming_uploader_key = str(uuid.uuid4())
if "renaming_session_id" not in st.session_state:
     st.session_state.renaming_session_id = str(uuid.uuid4())

if st.button("🧹 Clear Cache and Reset Data"):
    # Rimuovi solo chiavi specifiche di questa app
    keys_to_remove = [k for k in st.session_state.keys() if k.startswith("renaming_") or k in ["uploader_key", "session_id", "processing_done", "zip_path", "error_path", "farmadati_zip", "farmadati_errors", "farmadati_ready", "process_images_switzerland", "process_images_farmadati"]]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    # Rigenera chiave uploader specifica
    st.session_state.renaming_uploader_key = str(uuid.uuid4())
    st.info("Cache cleared. Please re-upload your file.")
    st.rerun()


# Function to combine SKUs from file and manual input (Originale)
def get_sku_list(uploaded_file_obj, manual_text):
    sku_list = []
    df_file = None
    if uploaded_file_obj is not None:
        try:
            if uploaded_file_obj.name.lower().endswith("csv"):
                uploaded_file_obj.seek(0)
                sample = uploaded_file_obj.read(1024).decode("utf-8", errors='ignore')
                uploaded_file_obj.seek(0)
                delimiter = ';' # Default
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=';,\t')
                    delimiter = dialect.delimiter
                except Exception:
                    pass # Use default
                df_file = pd.read_csv(uploaded_file_obj, delimiter=delimiter, dtype=str)
            else:
                df_file = pd.read_excel(uploaded_file_obj, dtype=str)

            sku_column = None
            for col in df_file.columns:
                if col.strip().lower() == "sku":
                    sku_column = col
                    break
            if sku_column:
                file_skus = df_file[sku_column].dropna().astype(str).str.strip()
                sku_list.extend(file_skus[file_skus != ''].tolist())
            else:
                 st.warning("Column 'sku' not found in file.")

        except Exception as e:
            st.error(f"Error reading file: {e}")

    if manual_text:
        manual_skus = [line.strip() for line in manual_text.splitlines() if line.strip()]
        sku_list.extend(manual_skus)

    unique_sku_list = list(dict.fromkeys(sku for sku in sku_list if sku))
    return unique_sku_list

# ======================================================
# SECTION: Switzerland (Originale)
# ======================================================
if server_country == "Switzerland":
    st.header("Switzerland Server Image Processing")
    st.markdown("""
    :information_source: **How to use:**

    - :arrow_right: **Create a list of products:** Rename the column **sku** or use the Quick Report in Akeneo.
    - :arrow_right: **In Akeneo, select the following options:**
        - **File Type:** CSV or Excel
        - **All Attributes or Grid Context:** (for Grid Context, select ID)
        - **With Codes**
        - **Without Media**
    """)

    manual_input = st.text_area("Or paste your SKUs here (one per line):", key="manual_input_switzerland")
    uploaded_file = st.file_uploader("Upload file (Excel or CSV)", type=["xlsx", "csv"], key=st.session_state.renaming_uploader_key) # Usa chiave specifica

    # Usa stato specifico per triggerare
    if st.button("Search Images", key="process_switzerland"):
        st.session_state.renaming_start_processing_ch = True
        st.session_state.renaming_processing_done_ch = False
        # Pulisci stato vecchio
        if "renaming_zip_path_ch" in st.session_state: del st.session_state.renaming_zip_path_ch
        if "renaming_error_path_ch" in st.session_state: del st.session_state.renaming_error_path_ch


    if st.session_state.get("renaming_start_processing_ch") and not st.session_state.get("renaming_processing_done_ch", False):
        sku_list = get_sku_list(uploaded_file, manual_input)
        if not sku_list:
            st.warning("Please upload a file or paste some SKUs to process.")
            st.session_state.renaming_start_processing_ch = False # Resetta trigger
        else:
            st.info(f"Processing {len(sku_list)} SKUs for Switzerland...")
            error_codes = []
            total_count = len(sku_list)
            progress_bar = st.progress(0, text="Starting processing...")

            def get_image_url(product_code):
                pharmacode = str(product_code)
                if pharmacode.upper().startswith("CH"):
                    pharmacode = pharmacode[2:].lstrip("0")
                else:
                    pharmacode = pharmacode.lstrip("0")
                if not pharmacode: return None
                return f"https://documedis.hcisolutions.ch/2020-01/api/products/image/PICFRONT3D/Pharmacode/{pharmacode}/F"

            def process_and_save(original_sku, content, download_folder):
                try:
                    img = Image.open(BytesIO(content))
                    if img.mode != 'L': gray = img.convert("L")
                    else: gray = img
                    extrema = gray.getextrema()
                    if extrema == (0, 0): raise ValueError("Empty image (black)")
                    if extrema == (255, 255): raise ValueError("Empty image (white)")

                    img = ImageOps.exif_transpose(img)
                    bg = Image.new(img.mode, img.size, (255, 255, 255))
                    diff = ImageChops.difference(img, bg)
                    bbox = diff.getbbox()
                    if bbox: img = img.crop(bbox)

                    if img.width == 0 or img.height == 0: raise ValueError("Image empty after trim")

                    img.thumbnail((1000, 1000), Image.LANCZOS)
                    canvas = Image.new("RGB", (1000, 1000), (255, 255, 255))
                    offset_x = (1000 - img.width) // 2
                    offset_y = (1000 - img.height) // 2
                    canvas.paste(img, (offset_x, offset_y))
                    new_filename = f"{original_sku}-h1.jpg"
                    img_path = os.path.join(download_folder, new_filename)
                    canvas.save(img_path, "JPEG", quality=95)
                    return True
                except Exception as e:
                    # Loggare l'errore potrebbe essere utile, ma evitiamo output console diretto
                    # print(f"Error processing {original_sku}: {e}")
                    return False

            async def fetch_and_process_image(session, product_code, download_folder):
                image_url = get_image_url(product_code)
                if image_url is None:
                    error_codes.append(product_code)
                    return
                try:
                    # Aumenta timeout se necessario
                    async with session.get(image_url, timeout=30) as response:
                        if response.status == 200:
                            content = await response.read()
                            if not content:
                                error_codes.append(product_code) # Contenuto vuoto
                                return
                            # Esegui processamento in thread per non bloccare event loop
                            success = await asyncio.to_thread(process_and_save, product_code, content, download_folder)
                            if not success:
                                error_codes.append(product_code)
                        # Non aggiungere a errori per 404, è comune
                        # elif response.status == 404:
                        #    error_codes.append(product_code)
                        elif response.status != 404: # Logga altri errori HTTP
                            st.warning(f"HTTP {response.status} for {product_code}")
                            error_codes.append(product_code)
                        else: # 404
                             error_codes.append(product_code)
                except asyncio.TimeoutError:
                     st.warning(f"Timeout for {product_code}")
                     error_codes.append(product_code)
                except Exception as e:
                    st.warning(f"Error for {product_code}: {e}")
                    error_codes.append(product_code)

            async def run_processing(download_folder):
                # Limita connessioni concorrenti
                connector = aiohttp.TCPConnector(limit=50)
                async with aiohttp.ClientSession(connector=connector) as session:
                    tasks = [fetch_and_process_image(session, sku, download_folder) for sku in sku_list]
                    processed_count = 0
                    for f in asyncio.as_completed(tasks):
                        await f # Aspetta completamento task
                        processed_count += 1
                        # Aggiorna progress bar
                        progress_val = processed_count / total_count
                        progress_bar.progress(progress_val, text=f"Processed {processed_count}/{total_count}")
                progress_bar.progress(1.0, text="Processing complete!")


            # Esecuzione
            with st.spinner("Processing Switzerland images..."):
                # Usa cartella temporanea
                with tempfile.TemporaryDirectory() as download_folder:
                    asyncio.run(run_processing(download_folder))

                    # Crea ZIP
                    zip_path_ch = None
                    if any(os.scandir(download_folder)): # Se ci sono file processati
                         # Crea un file temporaneo per lo zip
                         with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip_file:
                            zip_path_ch = tmp_zip_file.name
                         # Crea l'archivio (make_archive aggiunge .zip al nome base)
                         shutil.make_archive(zip_path_ch[:-4], 'zip', download_folder)
                         st.session_state["renaming_zip_path_ch"] = zip_path_ch # Salva path completo
                    else:
                         st.session_state["renaming_zip_path_ch"] = None


                    # Crea CSV Errori
                    error_path_ch = None
                    unique_error_codes = sorted(list(set(error_codes))) # Rimuovi duplicati
                    if unique_error_codes:
                        error_df = pd.DataFrame(unique_error_codes, columns=["sku"])
                        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", newline="", encoding="utf-8-sig") as tmp_error_file:
                            error_df.to_csv(tmp_error_file, index=False, sep=';') # Usa ;
                            error_path_ch = tmp_error_file.name
                        st.session_state["renaming_error_path_ch"] = error_path_ch
                    else:
                        st.session_state["renaming_error_path_ch"] = None

            # Fine processamento
            st.session_state["renaming_processing_done_ch"] = True
            st.session_state.renaming_start_processing_ch = False # Resetta trigger


    # Sezione Download Svizzera (Originale)
    if st.session_state.get("renaming_processing_done_ch", False):
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            zip_path_dl = st.session_state.get("renaming_zip_path_ch")
            if zip_path_dl and os.path.exists(zip_path_dl):
                with open(zip_path_dl, "rb") as f:
                    st.download_button(
                        label="Download Images",
                        data=f,
                        # Usa ID sessione specifico per nome file
                        file_name=f"switzerland_images_{st.session_state.renaming_session_id[:6]}.zip",
                        mime="application/zip",
                        key="dl_ch_zip" # Chiave univoca
                    )
            else:
                 st.info("No images processed or ZIP not found.")
        with col2:
            error_path_dl = st.session_state.get("renaming_error_path_ch")
            if error_path_dl and os.path.exists(error_path_dl):
                with open(error_path_dl, "rb") as f_error:
                    st.download_button(
                        label="Download Missing Image List",
                        data=f_error,
                        file_name=f"errors_switzerland_{st.session_state.renaming_session_id[:6]}.csv",
                        mime="text/csv",
                        key="dl_ch_err" # Chiave univoca
                    )
            else:
                st.info("No errors found or error file not found.")

# ======================================================
# SECTION: Farmadati (Originale con credenziali hardcoded)
# ======================================================
elif server_country == "Farmadati":
    st.header("Farmadati Server Image Processing")
    st.markdown("""
    :information_source: **How to use:**

    - :arrow_right: **Create a list of products:** Rename the column **sku** or use the Quick Report in Akeneo.
    - :arrow_right: **In Akeneo, select the following options:**
        - **File Type:** CSV or Excel
        - **All Attributes or Grid Context:** (for Grid Context, select ID)
        - **With Codes**
        - **Without Media**
    """)

    manual_input_fd = st.text_area("Or paste your SKUs here (one per line):", key="manual_input_farmadati")
    farmadati_file = st.file_uploader("Upload file (column 'sku')", type=["xlsx", "csv"], key=st.session_state.renaming_uploader_key) # Usa chiave specifica

    # Usa stato specifico per triggerare
    if st.button("Search Images", key="process_farmadati"):
         st.session_state.renaming_start_processing_fd = True
         st.session_state.renaming_processing_done_fd = False
         # Pulisci stato vecchio
         if "renaming_zip_buffer_fd" in st.session_state: del st.session_state.renaming_zip_buffer_fd
         if "renaming_error_data_fd" in st.session_state: del st.session_state.renaming_error_data_fd


    if st.session_state.get("renaming_start_processing_fd") and not st.session_state.get("renaming_processing_done_fd", False):
        sku_list_fd = get_sku_list(farmadati_file, manual_input_fd)
        if not sku_list_fd:
            st.warning("Please upload a file or paste some SKUs to process.")
            st.session_state.renaming_start_processing_fd = False # Resetta trigger
        else:
            st.info(f"Processing {len(sku_list_fd)} SKUs for Farmadati...")

            # --- Farmadati Credentials and Setup (Hardcoded) ---
            USERNAME = "BDF250621d"
            PASSWORD = "wTP1tvSZ"
            WSDL_URL = 'http://webservices.farmadati.it/WS2/FarmadatiItaliaWebServicesM2.svc?wsdl'
            DATASET_CODE = "TDZ"

            # Funzione cache per mapping (Originale)
            @st.cache_resource(ttl=3600) # Cache per 1 ora
            def get_farmadati_mapping(_username, _password):
                st.info(f"Fetching Farmadati dataset '{DATASET_CODE}'...")
                history = HistoryPlugin()
                transport = Transport(cache=InMemoryCache())
                # Timeout più lunghi per API lenta
                settings = Settings(strict=False, xml_huge_tree=True, timeout=180)
                try:
                    client = Client(wsdl=WSDL_URL, wsse=UsernameToken(_username, _password), transport=transport, plugins=[history], settings=settings)
                    response = client.service.GetDataSet(_username, _password, DATASET_CODE, "GETRECORDS", 1)
                except Exception as e:
                    st.error(f"Farmadati Connection/Fetch Error: {e}")
                    # Fermati qui se non possiamo ottenere il mapping
                    st.stop()

                if response.CodEsito != "OK" or response.ByteListFile is None:
                    st.error(f"Farmadati API Error: {response.CodEsito} - {response.DescEsito}")
                    st.stop()

                st.info("Parsing Farmadati XML mapping...")
                code_to_image = {}
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        zip_path_fd = os.path.join(tmp_dir, f"{DATASET_CODE}.zip")
                        with open(zip_path_fd, "wb") as f: f.write(response.ByteListFile)
                        with zipfile.ZipFile(zip_path_fd, 'r') as z:
                            xml_file = next((name for name in z.namelist() if name.upper().endswith('.XML')), None)
                            if not xml_file: raise FileNotFoundError("XML not in ZIP")
                            z.extract(xml_file, tmp_dir)
                            xml_full_path = os.path.join(tmp_dir, xml_file)

                        # Parsing XML (Originale)
                        tree = ET.parse(xml_full_path)
                        root = tree.getroot()
                        for record in root.findall('RECORD'):
                            t218 = record.find('FDI_T218') # AIC
                            t438 = record.find('FDI_T438') # Image Name
                            if t218 is not None and t438 is not None and t218.text and t438.text:
                                aic = t218.text.strip().lstrip("0") # Pulisci AIC
                                if aic: code_to_image[aic] = t438.text.strip()

                    st.success(f"Farmadati mapping loaded ({len(code_to_image)} codes).")
                    return code_to_image
                except Exception as e:
                    st.error(f"Error parsing Farmadati XML: {e}")
                    st.stop()

            # Funzione processamento immagine Farmadati (Originale)
            def process_image_fd(img_bytes):
                try:
                    img = Image.open(BytesIO(img_bytes))
                    if img.mode != 'L': gray = img.convert("L")
                    else: gray = img
                    extrema = gray.getextrema()
                    if extrema == (0, 0) or extrema == (255, 255): raise ValueError("Empty image")

                    img = ImageOps.exif_transpose(img)

                    # Trim (Originale)
                    bg = Image.new(img.mode, img.size, img.getpixel((0,0))) # Usa pixel angolo per sfondo? Meglio bianco fisso?
                    # Usiamo bianco fisso per coerenza
                    bg_white = Image.new(img.mode, img.size, (255, 255, 255))
                    diff = ImageChops.difference(img, bg_white)
                    bbox = diff.getbbox()
                    if bbox: img = img.crop(bbox)
                    if img.width == 0 or img.height == 0: raise ValueError("Empty after trim")

                    # Resize/Canvas (Originale)
                    if img.width > 1000:
                        left = (img.width - 1000) // 2
                        img = img.crop((left, 0, left + 1000, img.height))
                    if img.height > 1000:
                        top = (img.height - 1000) // 2
                        img = img.crop((0, top, img.width, top + 1000))
                    if img.width < 1000 or img.height < 1000:
                        canvas = Image.new("RGB", (1000, 1000), "white")
                        left = (1000 - img.width) // 2
                        top = (1000 - img.height) // 2
                        canvas.paste(img, (left, top))
                        final_img = canvas
                    else:
                        final_img = img

                    # Salva in buffer
                    buffer = BytesIO()
                    final_img.save(buffer, "JPEG", quality=95) # Qualità 95
                    buffer.seek(0)
                    return buffer
                except Exception as e:
                     raise RuntimeError(f"Processing failed: {e}")


            # --- Esecuzione Processamento Farmadati (Originale) ---
            try:
                aic_to_image = get_farmadati_mapping(USERNAME, PASSWORD)
                if not aic_to_image:
                     st.error("Farmadati mapping failed.")
                     st.session_state.renaming_start_processing_fd = False # Resetta trigger
                else:
                    total_fd = len(sku_list_fd)
                    progress_bar_fd = st.progress(0, text="Starting Farmadati processing...")
                    error_list_fd = [] # Lista tuple (sku, reason)
                    processed_files_count = 0
                    zip_buffer = BytesIO() # ZIP in memoria

                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
                         # Usa requests sincrono come nell'originale
                         with requests.Session() as http_session:
                            for i, sku in enumerate(sku_list_fd):
                                progress_bar_fd.progress((i+1)/total_fd, text=f"Processing {sku} ({i+1}/{total_fd})")
                                clean_sku = str(sku).strip()
                                if clean_sku.upper().startswith("IT"): clean_sku = clean_sku[2:]
                                clean_sku = clean_sku.lstrip("0")

                                if not clean_sku:
                                    error_list_fd.append((sku, "Invalid AIC"))
                                    continue

                                image_name = aic_to_image.get(clean_sku)
                                if not image_name:
                                    error_list_fd.append((sku, "AIC not in mapping"))
                                    continue

                                from urllib.parse import quote
                                image_url = f"https://ws.farmadati.it/WS_DOC/GetDoc.aspx?accesskey={PASSWORD}&tipodoc=Z&nomefile={quote(image_name)}"

                                try:
                                    r = http_session.get(image_url, timeout=45) # Timeout
                                    r.raise_for_status() # Errore HTTP
                                    if not r.content:
                                         error_list_fd.append((sku, "Empty download"))
                                         continue

                                    # Processa immagine
                                    processed_buffer = process_image_fd(r.content)
                                    # Aggiungi a ZIP
                                    zipf.writestr(f"{sku}-h1.jpg", processed_buffer.read())
                                    processed_files_count += 1

                                except requests.exceptions.RequestException as req_e:
                                     reason = f"Network Error: {req_e}"
                                     if req_e.response is not None: reason = f"HTTP {req_e.response.status_code}"
                                     error_list_fd.append((sku, reason))
                                except Exception as proc_e: # Cattura errori da process_image_fd
                                     error_list_fd.append((sku, f"Processing Error: {proc_e}"))


                    progress_bar_fd.progress(1.0, text="Farmadati processing complete!")

                    # Salva risultati nello stato (Originale)
                    if processed_files_count > 0:
                        zip_buffer.seek(0)
                        st.session_state["renaming_zip_buffer_fd"] = zip_buffer
                    else:
                        st.session_state["renaming_zip_buffer_fd"] = None

                    if error_list_fd:
                        error_df = pd.DataFrame(error_list_fd, columns=["SKU", "Reason"])
                        error_df = error_df.drop_duplicates().sort_values(by="SKU")
                        csv_error = error_df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.session_state["renaming_error_data_fd"] = csv_error
                    else:
                        st.session_state["renaming_error_data_fd"] = None

            except Exception as critical_e:
                 st.error(f"Critical Error during Farmadati processing: {critical_e}")

            # Fine processamento
            st.session_state["renaming_processing_done_fd"] = True
            st.session_state.renaming_start_processing_fd = False # Resetta trigger


    # Sezione Download Farmadati (Originale)
    if st.session_state.get("renaming_processing_done_fd"):
        st.markdown("---")
        col1_fd_dl, col2_fd_dl = st.columns(2)
        with col1_fd_dl:
            zip_data = st.session_state.get("renaming_zip_buffer_fd")
            if zip_data:
                st.download_button(
                    "Download Images (ZIP)",
                    data=zip_data,
                    file_name=f"farmadati_images_{st.session_state.renaming_session_id[:6]}.zip",
                    mime="application/zip",
                    key="dl_fd_zip" # Chiave univoca
                )
            else:
                 st.info("No images processed.")
        with col2_fd_dl:
            error_data = st.session_state.get("renaming_error_data_fd")
            if error_data:
                st.download_button(
                    "Download Error List",
                    data=error_data,
                    file_name=f"errors_farmadati_{st.session_state.renaming_session_id[:6]}.csv",
                    mime="text/csv",
                    key="dl_fd_err" # Chiave univoca
                )
            else:
                st.info("No errors found.")

# ======================================================
# SECTION: coming soon (Originale)
# ======================================================
elif server_country == "coming soon":
    st.header("coming soon")
    st.info("This section is under development.") # Messaggio originale
    # st.stop() # Rimosso st.stop() implicito alla fine
