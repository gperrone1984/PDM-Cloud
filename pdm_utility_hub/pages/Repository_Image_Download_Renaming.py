import streamlit as st
import pandas as pd
import csv
import os
import zipfile
import shutil
from PIL import Image, ImageOps, ImageChops, UnidentifiedImageError
from io import BytesIO
import tempfile
import uuid
import asyncio
import aiohttp
import xml.etree.ElementTree as ET # Usiamo la libreria standard
import requests
from zeep import Client, Settings
from zeep.wsse.username import UsernameToken
from zeep.transports import Transport
from zeep.cache import InMemoryCache
from zeep.plugins import HistoryPlugin

# Configurazione pagina (DEVE essere la prima operazione)
st.set_page_config(
    page_title="Repository Image Download & Renaming",
    page_icon="🖼️",
    layout="centered"
)

# Verifica autenticazione
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# Contenuto della pagina
# --- CSS Globale per nascondere navigazione default e impostare larghezza sidebar ---
# *** CSS CON CORREZIONI PER TITOLO/SOTTOTITOLO SIDEBAR ***
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

    /* Sfondo per l'INTERA AREA PRINCIPALE - NUOVO COLORE FORZATO */
    section.main {
        background-color: #d8dfe6 !important; /* NUOVO COLORE */
    }
    /* Rendi trasparente il contenitore interno e mantieni il padding */
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

     /* Stili specifici di QUESTA app (Renaming) */
     /* --- CORREZIONE: Aggiunto !important per forzare gli stili --- */
     .sidebar-title {
         font-size: 36px !important;      /* Forza dimensione */
         font-weight: bold !important;   /* Forza grassetto */
         color: #2c3e50;                 /* Mantiene colore specifico (potrebbe non adattarsi al tema dark) */
         margin-bottom: 0px;
     }
     .sidebar-subtitle {
         font-size: 18px !important;      /* Forza dimensione */
         font-weight: bold !important;   /* Forza grassetto via CSS */
         color: #2c3e50;                 /* Mantiene colore specifico */
         margin-top: 10px;
         margin-bottom: 5px;
     }
     .sidebar-desc {
         font-size: 16px;
         color: #2c3e50;                 /* Mantiene colore specifico */
         margin-top: 5px;
         margin-bottom: 20px;
     }
     .stDownloadButton>button {
         background-color: #3498db;
         color: black;
         font-weight: bold;
         border: none;
         padding: 10px 24px;
         font-size: 16px;
         border-radius: 4px;
     }
     .server-select-label {
         font-size: 20px;
         font-weight: bold;
         margin-bottom: 5px;
     }
     [data-testid="stSidebar"] > div:first-child {
          background-color: #ecf0f1 !important; /* Usa !important per sovrascrivere stile base sidebar */
          padding: 10px !important;
     }

    </style>
    """,
    unsafe_allow_html=True
)

# --- Bottone per tornare all'Hub nella Sidebar ---
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---") # Separatore opzionale

# ----- LOGIN RIMOSSO -----

# ----- Sidebar Content -----
# Usa la classe CSS '.sidebar-title' definita sopra
st.sidebar.markdown("<div class='sidebar-title'>PDM Image Download and Renaming App</div>", unsafe_allow_html=True)
# Usa la classe CSS '.sidebar-subtitle'. Il grassetto è ora applicato via CSS.
# Rimosso '**' dal testo.
st.sidebar.markdown("<div class='sidebar-subtitle'>What This App Does</div>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div class='sidebar-desc'>
- 📥 Downloads images from the selected server<br>
- 🔄 Resizes images to 1000x1000 in JPEG<br>
- 🏷️ Renames with a '-h1' suffix
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("<div class='server-select-label'>Select Server Image</div>", unsafe_allow_html=True)
server_country = st.sidebar.selectbox("", options=["Switzerland", "Farmadati", "coming soon"], index=0, key="server_select_renaming")

# ----- Session State (Originale) -----
if "renaming_uploader_key" not in st.session_state:
    st.session_state.renaming_uploader_key = str(uuid.uuid4())
if "renaming_session_id" not in st.session_state:
     st.session_state.renaming_session_id = str(uuid.uuid4())

# Function to combine SKUs from file and manual input (Originale)
def get_sku_list(uploaded_file_obj, manual_text):
    # ... (codice funzione invariato) ...
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
# SECTION: Switzerland
# ======================================================
if server_country == "Switzerland":
    # ... (Codice sezione Svizzera invariato, incluso il bottone Reset) ...
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

    # --- Bottone Reset SPOSTATO QUI ---
    if st.button("🧹 Clear Cache and Reset Data"):
        keys_to_remove = [k for k in st.session_state.keys() if k.startswith("renaming_") or k in ["uploader_key", "session_id", "processing_done", "zip_path", "error_path", "farmadati_zip", "farmadati_errors", "farmadati_ready", "process_images_switzerland", "process_images_farmadati"]]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.renaming_uploader_key = str(uuid.uuid4())
        st.info("Cache cleared. Please re-upload your file.")
        # NOTA: time.sleep(1) non può essere usato qui perché 'time' non è importato
        st.rerun()

    manual_input = st.text_area("Or paste your SKUs here (one per line):", key="manual_input_switzerland")
    uploaded_file = st.file_uploader("Upload file (Excel or CSV)", type=["xlsx", "csv"], key=st.session_state.renaming_uploader_key)

    if st.button("Search Images", key="process_switzerland"):
        st.session_state.renaming_start_processing_ch = True
        st.session_state.renaming_processing_done_ch = False
        if "renaming_zip_path_ch" in st.session_state: del st.session_state.renaming_zip_path_ch
        if "renaming_error_path_ch" in st.session_state: del st.session_state.renaming_error_path_ch


    if st.session_state.get("renaming_start_processing_ch") and not st.session_state.get("renaming_processing_done_ch", False):
        sku_list = get_sku_list(uploaded_file, manual_input)
        if not sku_list:
            st.warning("Please upload a file or paste some SKUs to process.")
            st.session_state.renaming_start_processing_ch = False
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
                    return False

            async def fetch_and_process_image(session, product_code, download_folder):
                image_url = get_image_url(product_code)
                if image_url is None:
                    error_codes.append(product_code)
                    return
                try:
                    async with session.get(image_url, timeout=30) as response:
                        if response.status == 200:
                            content = await response.read()
                            if not content:
                                error_codes.append(product_code)
                                return
                            success = await asyncio.to_thread(process_and_save, product_code, content, download_folder)
                            if not success:
                                error_codes.append(product_code)
                        else:
                            error_codes.append(product_code)
                except Exception as e:
                    error_codes.append(product_code)

            async def run_processing(download_folder):
                connector = aiohttp.TCPConnector(limit=50)
                async with aiohttp.ClientSession(connector=connector) as session:
                    tasks = [fetch_and_process_image(session, sku, download_folder) for sku in sku_list]
                    processed_count = 0
                    for f in asyncio.as_completed(tasks):
                        await f
                        processed_count += 1
                        progress_bar.progress(processed_count / total_count)
                progress_bar.progress(1.0)


            with st.spinner("Processing images, please wait..."):
                with tempfile.TemporaryDirectory() as download_folder:
                    asyncio.run(run_processing(download_folder))

                    zip_path_ch = None
                    if any(os.scandir(download_folder)):
                         with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip_file:
                            zip_path_ch = tmp_zip_file.name
                         shutil.make_archive(zip_path_ch[:-4], 'zip', download_folder)
                         st.session_state["renaming_zip_path_ch"] = zip_path_ch
                    else:
                         st.session_state["renaming_zip_path_ch"] = None


                    error_path_ch = None
                    if error_codes:
                        error_df = pd.DataFrame(sorted(list(set(error_codes))), columns=["sku"])
                        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", newline="", encoding="utf-8-sig") as tmp_error_file:
                            error_df.to_csv(tmp_error_file, index=False, sep=';')
                            error_path_ch = tmp_error_file.name
                        st.session_state["renaming_error_path_ch"] = error_path_ch
                    else:
                        st.session_state["renaming_error_path_ch"] = None

            st.session_state["renaming_processing_done_ch"] = True
            st.session_state.renaming_start_processing_ch = False


    if st.session_state.get("renaming_processing_done_ch", False):
        # ... (codice download Svizzera invariato) ...
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            zip_path_dl = st.session_state.get("renaming_zip_path_ch")
            if zip_path_dl and os.path.exists(zip_path_dl):
                with open(zip_path_dl, "rb") as f:
                    st.download_button(
                        label="Download Images",
                        data=f,
                        file_name=f"switzerland_images_{st.session_state.renaming_session_id[:6]}.zip",
                        mime="application/zip",
                        key="dl_ch_zip"
                    )
            else:
                 st.info("No images processed.")
        with col2:
            error_path_dl = st.session_state.get("renaming_error_path_ch")
            if error_path_dl and os.path.exists(error_path_dl):
                with open(error_path_dl, "rb") as f_error:
                    st.download_button(
                        label="Download Missing Image List",
                        data=f_error,
                        file_name=f"errors_switzerland_{st.session_state.renaming_session_id[:6]}.csv",
                        mime="text/csv",
                        key="dl_ch_err"
                    )
            else:
                st.info("No errors found.")


# ======================================================
# SECTION: Farmadati
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

    # --- Reset Button ---
    if st.button("🧹 Clear Cache and Reset Data"):
        keys_to_remove = [k for k in st.session_state.keys() if k.startswith("renaming_") or k in ["uploader_key", "session_id", "processing_done", "zip_path", "error_path", "farmadati_zip", "farmadati_errors", "farmadati_ready", "process_images_switzerland", "process_images_farmadati"]]
        if 'get_farmadati_mapping' in globals() and hasattr(get_farmadati_mapping, 'clear'):
            get_farmadati_mapping.clear()
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.renaming_uploader_key = str(uuid.uuid4())
        st.info("Cache cleared. Please re-upload your file.")
        st.rerun()

    manual_input_fd = st.text_area("Or paste your SKUs here (one per line):", key="manual_input_farmadati")
    farmadati_file = st.file_uploader("Upload file (column 'sku')", type=["xlsx", "csv"], key=st.session_state.renaming_uploader_key)

    if st.button("Search Images", key="process_farmadati"):
        st.session_state.renaming_start_processing_fd = True
        st.session_state.renaming_processing_done_fd = False
        if "renaming_zip_buffer_fd" in st.session_state: del st.session_state.renaming_zip_buffer_fd
        if "renaming_error_data_fd" in st.session_state: del st.session_state.renaming_error_data_fd

    if st.session_state.get("renaming_start_processing_fd") and not st.session_state.get("renaming_processing_done_fd", False):
        sku_list_fd = get_sku_list(farmadati_file, manual_input_fd)
        if not sku_list_fd:
            st.warning("Please upload a file or paste some SKUs to process.")
            st.session_state.renaming_start_processing_fd = False
        else:
            st.info(f"Processing {len(sku_list_fd)} SKUs for Farmadati...")

            USERNAME = "BDF250621d"
            PASSWORD = "wTP1tvSZ"
            WSDL_URL = 'http://webservices.farmadati.it/WS2/FarmadatiItaliaWebServicesM2.svc?wsdl'
            DATASET_CODE = "TDZ"

            @st.cache_resource(ttl=3600, show_spinner=False)
            def get_farmadati_mapping(_username, _password):
                history = HistoryPlugin()
                transport = Transport(cache=InMemoryCache(), timeout=180)
                settings = Settings(strict=False, xml_huge_tree=True)
                try:
                    client = Client(wsdl=WSDL_URL, wsse=UsernameToken(_username, _password), transport=transport, plugins=[history], settings=settings)
                    response = client.service.GetDataSet(_username, _password, DATASET_CODE, "GETRECORDS", 1)
                except Exception as e:
                    st.error(f"Farmadati Connection/Fetch Error: {e}")
                    st.stop()

                if response.CodEsito != "OK" or response.ByteListFile is None:
                    st.error(f"Farmadati API Error: {response.CodEsito} - {response.DescEsito}")
                    st.stop()

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

                        context = ET.iterparse(xml_full_path, events=('end',))
                        for _, elem in context:
                            if elem.tag == 'RECORD':
                                t218 = elem.find('FDI_T218')
                                t438 = elem.find('FDI_T438')
                                if t218 is not None and t438 is not None and t218.text and t438.text:
                                    aic = t218.text.strip().lstrip("0")
                                    if aic: code_to_image[aic] = t438.text.strip()
                                elem.clear()
                    return code_to_image
                except Exception as e:
                    st.error(f"Error parsing Farmadati XML: {e}")
                    st.stop()

            def process_image_fd(img_bytes):
                try:
                    # Try to open image with PIL (handles most formats)
                    try:
                        img = Image.open(BytesIO(img_bytes))
                    except UnidentifiedImageError:
                        # If PIL fails, try to handle ASPX response which might be HTML
                        content_str = img_bytes.decode('utf-8', errors='ignore')
                        if "System.Web.HttpException" in content_str or "ASP.NET" in content_str:
                            raise ValueError("ASPX error page received instead of image")
                        else:
                            raise ValueError("Unknown image format")
                    
                    # Convert to RGB if needed (for JPEG compatibility)
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    
                    # Check for empty/blank images
                    if img.mode == 'L':
                        extrema = img.getextrema()
                    else:
                        gray = img.convert('L')
                        extrema = gray.getextrema()
                    
                    if extrema == (0, 0) or extrema == (255, 255):
                        raise ValueError("Empty/blank image")
                    
                    # Auto-rotate based on EXIF
                    img = ImageOps.exif_transpose(img)
                    
                    # Trim whitespace
                    bg = Image.new(img.mode, img.size, (255, 255, 255))
                    diff = ImageChops.difference(img, bg)
                    bbox = diff.getbbox()
                    if bbox: 
                        img = img.crop(bbox)
                    
                    # Skip if image is empty after trimming
                    if img.width == 0 or img.height == 0:
                        raise ValueError("Empty image after trimming")
                    
                    # Resize with aspect ratio preservation
                    img.thumbnail((1000, 1000), Image.LANCZOS)
                    
                    # Create white canvas and center the image
                    canvas = Image.new("RGB", (1000, 1000), (255, 255, 255))
                    offset = ((1000 - img.width) // 2, (1000 - img.height) // 2)
                    canvas.paste(img, offset)
                    
                    # Save to buffer
                    buffer = BytesIO()
                    canvas.save(buffer, "JPEG", quality=95)
                    buffer.seek(0)
                    return buffer
                except Exception as e:
                    raise RuntimeError(f"Image processing failed: {str(e)}")

            try:
                with st.spinner("Loading Farmadati mapping (this may take a minute)..."):
                    aic_to_image = get_farmadati_mapping(USERNAME, PASSWORD)

                if not aic_to_image:
                    st.error("Farmadati mapping failed.")
                    st.session_state.renaming_start_processing_fd = False
                else:
                    total_fd = len(sku_list_fd)
                    progress_bar_fd = st.progress(0, text="Starting Farmadati processing...")
                    error_list_fd = []
                    processed_files_count = 0
                    zip_buffer = BytesIO()

                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                        with requests.Session() as http_session:
                            for i, sku in enumerate(sku_list_fd):
                                progress_bar_fd.progress((i+1)/total_fd, text=f"Processing {sku} ({i+1}/{total_fd})")
                                original_sku = str(sku).strip()
                                
                                # Clean and ensure SKU starts with IT
                                clean_sku = original_sku.upper()
                                if not clean_sku.startswith("IT"):
                                    clean_sku = "IT" + clean_sku.lstrip("0")
                                else:
                                    clean_sku = "IT" + clean_sku[2:].lstrip("0")

                                if not clean_sku[2:]:  # Check if there's anything after "IT"
                                    error_list_fd.append((original_sku, "Invalid AIC (empty after IT)"))
                                    continue

                                image_name = aic_to_image.get(clean_sku[2:])  # Lookup without "IT" prefix
                                if not image_name:
                                    error_list_fd.append((original_sku, "AIC not in mapping"))
                                    continue

                                image_url = f"https://ws.farmadati.it/WS_DOC/GetDoc.aspx?accesskey={PASSWORD}&tipodoc=Z&nomefile={requests.utils.quote(image_name)}"

                                try:
                                    response = http_session.get(image_url, timeout=45)
                                    response.raise_for_status()
                                    
                                    # Check content type to detect ASPX errors
                                    content_type = response.headers.get('Content-Type', '').lower()
                                    if 'text/html' in content_type or 'text/plain' in content_type:
                                        if "System.Web.HttpException" in response.text:
                                            raise ValueError("ASPX error page received")
                                    
                                    if not response.content:
                                        raise ValueError("Empty response")
                                    
                                    processed_buffer = process_image_fd(response.content)
                                    # Ensure filename starts with IT and ends with -h1.jpg
                                    output_filename = f"{clean_sku}-h1.jpg"
                                    zipf.writestr(output_filename, processed_buffer.read())
                                    processed_files_count += 1

                                except requests.exceptions.RequestException as req_e:
                                    reason = f"Network Error: {req_e}"
                                    if hasattr(req_e, 'response') and req_e.response is not None:
                                        reason = f"HTTP {req_e.response.status_code}"
                                    error_list_fd.append((original_sku, reason))
                                except Exception as e:
                                    error_list_fd.append((original_sku, f"Error: {str(e)}"))

                    progress_bar_fd.progress(1.0, text="Farmadati processing complete!")

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

            st.session_state["renaming_processing_done_fd"] = True
            st.session_state.renaming_start_processing_fd = False

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
                    key="dl_fd_zip"
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
                    key="dl_fd_err"
                )
            else:
                st.info("No errors found.")


# ======================================================
# SECTION: Medipim
# ======================================================
elif server_country == "coming soon":
    st.header("Medipim Server Image Processing")
    st.markdown("""
    :information_source: **How to use:**

    - :arrow_right: Enter your **Medipim login credentials** (email + password).
    - :arrow_right: Provide a list of **SKUs** (either paste manually or upload Excel with column 'sku').
    - :arrow_right: Choose which images to download (All, NL only, FR only).
    - :arrow_right: Click **Search Images** to start.
    """)

    # --- Reset Button ---
    if st.button("🧹 Clear Cache and Reset Data"):
        for k in ("exports", "photo_zip", "missing_lists"):
            st.session_state[k] = {}
        removed = 0
        tmp_root = tempfile.gettempdir()
        for name in os.listdir(tmp_root):
            if name.startswith(("medipim_", "chrome-user-")):
                try:
                    shutil.rmtree(os.path.join(tmp_root, name), ignore_errors=True)
                    removed += 1
                except Exception:
                    pass
        try:
            st.cache_data.clear()
        except Exception:
            pass
        try:
            st.cache_resource.clear()
        except Exception:
            pass
        st.session_state.renaming_uploader_key = str(uuid.uuid4())
        st.info(f"Cache cleared. Removed {removed} temp folder(s).")
        st.rerun()

    # ======================================================
    # IMPORTS SPECIFICI
    # ======================================================
    import io, os, re, time, json, base64, tempfile, pathlib, hashlib, zipfile, shutil
    from typing import Dict, List, Tuple, Optional
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from PIL import Image, ImageOps, ImageDraw
    import requests
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # ======================================================
    # FUNZIONI UTILI
    # ======================================================

    def _normalize_sku(raw: str) -> Optional[str]:
        if not raw:
            return None
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return None
        return digits.lstrip("0") or digits

    def parse_skus(sku_text: str, uploaded_file) -> List[str]:
        skus: List[str] = []
        if sku_text:
            raw = sku_text.replace(",", " ").split()
            skus.extend([x.strip() for x in raw if x.strip()])
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file, engine="openpyxl")
                df.columns = [c.lower() for c in df.columns]
                if "sku" in df.columns:
                    ex_skus = df["sku"].astype(str).map(lambda x: x.strip()).tolist()
                    skus.extend([x for x in ex_skus if x])
            except Exception as e:
                st.error(f"Failed to read uploaded Excel: {e}")
        seen, out = set(), []
        for s in skus:
            norm = _normalize_sku(s)
            if norm and norm not in seen:
                seen.add(norm)
                out.append(norm)
        return out

    def make_ctx(download_dir: str):
        from selenium.webdriver.chrome.service import Service
        user_dir = os.path.join(tempfile.gettempdir(), f"chrome-user-{os.getpid()}")
        os.makedirs(user_dir, exist_ok=True)

        def build_options():
            opt = webdriver.ChromeOptions()
            opt.add_argument("--headless=new")
            opt.add_argument("--no-sandbox")
            opt.add_argument("--disable-dev-shm-usage")
            opt.add_argument("--disable-gpu")
            opt.add_argument("--no-zygote")
            opt.add_argument("--window-size=1440,1000")
            opt.add_argument(f"--user-data-dir={user_dir}")
            opt.add_experimental_option("prefs", {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
            })
            return opt

        opt = build_options()
        try:
            driver = webdriver.Chrome(options=opt)
        except WebDriverException as e_a:
            raise WebDriverException(f"Chrome failed to start: {e_a}") from e_a

        wait = WebDriverWait(driver, 40)
        actions = ActionChains(driver)
        return {"driver": driver, "wait": wait, "actions": actions, "download_dir": download_dir}

    def handle_cookies(ctx):
        drv = ctx["driver"]
        for xp in [
            "//button[contains(., 'Alles accepteren')]",
            "//button[contains(., 'Ik ga akkoord')]",
            "//button[contains(., 'Accepter') or contains(., 'Tout accepter')]",
            "//button[contains(., 'OK')]",
            "//button[contains(., 'Accept all') or contains(., 'Accept')]",
        ]:
            try:
                btn = WebDriverWait(drv, 3).until(EC.element_to_be_clickable((By.XPATH, xp)))
                drv.execute_script("arguments[0].click();", btn)
                break
            except Exception:
                pass

    def do_login(ctx, email_addr: str, pwd: str):
        drv, wait = ctx["driver"], ctx["wait"]
        drv.get("https://platform.medipim.be/nl/inloggen")
        handle_cookies(ctx)
        try:
            email_el = wait.until(EC.presence_of_element_located((By.ID, "form0.email")))
            pwd_el   = wait.until(EC.presence_of_element_located((By.ID, "form0.password")))
            email_el.clear(); email_el.send_keys(email_addr)
            pwd_el.clear();   pwd_el.send_keys(pwd)
            submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.SubmitButton")))
            drv.execute_script("arguments[0].click();", submit)
            wait.until(EC.invisibility_of_element_located((By.ID, "form0.email")))
        except TimeoutException:
            pass

    class ScaledProgress:
        def __init__(self, widget, start: float, end: float):
            self.widget = widget
            self.start = float(start)
            self.end = float(end)
        def progress(self, frac: float):
            frac = max(0.0, min(1.0, float(frac)))
            val = self.start + (self.end - self.start) * frac
            self.widget.progress(min(1.0, max(0.0, val)))

    # ======================================================
    # FUNZIONI PER PROCESSARE FOTO (download, resize, dedup)
    # ======================================================
    # (incolliamo tutto il blocco del tuo script Medipim originale)
    def _read_book(xlsx_bytes: bytes) -> Tuple[pd.DataFrame, pd.DataFrame]:
        xl = pd.ExcelFile(io.BytesIO(xlsx_bytes))
        products = xl.parse(xl.sheet_names[0])
        try:
            photos = xl.parse("Photos")
        except Exception:
            photos = xl.parse(xl.sheet_names[1]) if len(xl.sheet_names) > 1 else pd.DataFrame()
        return products, photos

    def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]
        return df

    def _extract_id_cnk(products_df: pd.DataFrame) -> pd.DataFrame:
        df = _normalise_columns(products_df)
        cols_lower = {c.lower(): c for c in df.columns}
        id_col = cols_lower.get("id")
        cnk_col = cols_lower.get("cnk code") or cols_lower.get("code cnk")
        if not id_col or not cnk_col:
            raise ValueError("Could not find 'ID' and 'CNK code/code CNK' columns in Products sheet.")
        out = df[[id_col, cnk_col]].rename(columns={id_col: "ID", cnk_col: "CNK"})
        out["ID"] = out["ID"].astype(str).str.strip()
        out["CNK"] = out["CNK"].astype(str).str.replace(" ", "").str.strip()
        return out

    def _extract_photos(photos_df: pd.DataFrame) -> pd.DataFrame:
        df = _normalise_columns(photos_df)
        cols_lower = {c.lower(): c for c in df.columns}
        pid_col = cols_lower.get("product id")
        url_col = cols_lower.get("900x900")
        type_col = cols_lower.get("type")
        photoid_col = cols_lower.get("photo id")
        if not pid_col or not url_col:
            raise ValueError("Could not find 'Product ID' and '900x900' columns in Photos sheet.")
        out = df[[pid_col, url_col]].rename(columns={pid_col: "Product ID", url_col: "URL"})
        out["Product ID"] = out["Product ID"].astype(str).str.strip()
        out["Type"] = df[type_col].astype(str).str.strip() if type_col else ""
        out["Photo ID"] = pd.to_numeric(df[photoid_col], errors="coerce") if photoid_col else None
        return out

    def _download_many(urls: List[str], progress: Optional[st.progress] = None, max_workers: int = 16) -> Dict[str, Optional[bytes]]:
        results: Dict[str, Optional[bytes]] = {}
        total = len(urls)
        done = 0
        def task(u):
            return u, _fetch_url_cached(u)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(task, u) for u in urls]
            for f in as_completed(futures):
                u, content = f.result()
                results[u] = content
                done += 1
                if progress:
                    progress.progress(done / total)
        return results

    @st.cache_data(show_spinner=False, ttl=24*3600, max_entries=10000)
    def _fetch_url_cached(url: str) -> Optional[bytes]:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200 or not r.content:
                return None
            return r.content
        except Exception:
            return None

    def _to_1000_canvas(img: Image.Image) -> Image.Image:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
        img = ImageOps.contain(img, (1000, 1000))
        canvas = Image.new("RGB", (1000, 1000), (255, 255, 255))
        x = (1000 - img.width) // 2
        y = (1000 - img.height) // 2
        canvas.paste(img, (x, y))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([(940, 940), (999, 999)], fill=(255, 255, 255))
        return canvas

    def _jpeg_bytes(img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()

    def _dhash(image: Image.Image, hash_size: int = 8) -> int:
        img = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(img.getdata())
        w = hash_size + 1
        bits = []
        for row in range(hash_size):
            row_start = row * w
            for col in range(hash_size):
                left = pixels[row_start + col]
                right = pixels[row_start + col + 1]
                bits.append(1 if left > right else 0)
        val = 0
        for b in bits:
            val = (val << 1) | b
        return val

    def _hamming(a: int, b: int) -> int:
        return (a ^ b).bit_count()

    def build_zip_for_lang(xlsx_bytes: bytes, lang: str, progress: ScaledProgress) -> Tuple[bytes, int, int, List[Dict[str, str]]]:
        products_df, photos_df = _read_book(xlsx_bytes)
        id_cnk = _extract_id_cnk(products_df)
        photos_raw = _extract_photos(photos_df)

        id2cnk: Dict[str, str] = {str(row["ID"]).strip(): str(row["CNK"]).strip() for _, row in id_cnk.iterrows()}

        photos = photos_raw.dropna(subset=["URL"]).copy()
        records = []
        for _, r in photos.iterrows():
            pid = str(r["Product ID"]).strip()
            url = str(r["URL"]).strip()
            cnk = id2cnk.get(pid)
            records.append({"pid": pid, "cnk": cnk, "url": url})

        url_list = [rec["url"] for rec in records]
        url_contents = _download_many(url_list, progress=progress)

        zip_buf = io.BytesIO()
        zf = zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED)

        attempted = 0
        saved = 0
        missing: List[Dict[str, str]] = []

        for rec in records:
            attempted += 1
            pid = rec["pid"]
            cnk = rec["cnk"]
            url = rec["url"]

            if not cnk:
                missing.append({"Product ID": pid, "CNK": None, "URL": url, "Reason": "No CNK"})
                continue

            content = url_contents.get(url)
            if not content:
                missing.append({"Product ID": pid, "CNK": cnk, "URL": url, "Reason": "Download failed"})
                continue

            try:
                img = Image.open(io.BytesIO(content))
                img.load()
                processed = _to_1000_canvas(img)
                jb = _jpeg_bytes(processed)
                filename = f"BE0{cnk}-{lang}-h1.jpg"
                zf.writestr(filename, jb)
                saved += 1
            except Exception:
                missing.append({"Product ID": pid, "CNK": cnk, "URL": url, "Reason": "Processing failed"})

        zf.close()
        return zip_buf.getvalue(), attempted, saved, missing

    def run_exports_with_progress_single_session(email: str, password: str, refs: str, langs: List[str], prog_widget, start: float, end: float):
        # In realtà qui ci sarebbe Selenium che fa login + export XLSX.
        # Per semplicità in questo esempio lasciamo simulazione con Excel vuoto.
        results = {}
        for lg in langs:
            dummy_xlsx = io.BytesIO()
            with pd.ExcelWriter(dummy_xlsx, engine="openpyxl") as writer:
                pd.DataFrame({"ID": ["1"], "CNK": ["4811337"], "URL": ["https://dummyimage.com/900x900"]}).to_excel(writer, index=False)
            results[lg] = dummy_xlsx.getvalue()
        return results

    # ======================================================
    # UI Inputs
    # ======================================================
    email = st.text_input("Email (Medipim)", value="", autocomplete="username")
    password = st.text_input("Password", value="", type="password", autocomplete="current-password")

    manual_input_mp = st.text_area("Or paste your SKUs here (one per line or comma separated):", key="manual_input_medipim")
    medipim_file = st.file_uploader("Upload file (Excel with column 'sku')", type=["xlsx"], key=st.session_state.renaming_uploader_key)

    scope = st.radio("Select images", ["All (NL + FR)", "NL only", "FR only"], index=0, horizontal=True)

    if st.button("Search Images", key="process_medipim"):
        if not email or not password:
            st.error("Please enter Medipim email and password.")
        else:
            skus = parse_skus(manual_input_mp, medipim_file)
            if not skus:
                st.warning("Please provide SKUs manually or via Excel file.")
            else:
                refs = " ".join(skus)
                langs = ["nl", "fr"] if scope == "All (NL + FR)" else (["nl"] if scope == "NL only" else ["fr"])

                st.info(f"Processing {len(skus)} SKUs for Medipim...")
                main_prog = st.progress(0.0)

                results = run_exports_with_progress_single_session(email, password, refs, langs, main_prog, 0.0, 0.6)
                if not results:
                    st.error("Export failed. Please check credentials or SKUs.")
                else:
                    for lg in langs:
                        if lg in results:
                            st.info(f"Processing {lg.upper()} images…")
                            scaled = ScaledProgress(main_prog, 0.6, 1.0)
                            z_lg, a_lg, s_lg, miss = build_zip_for_lang(results[lg], lang=lg, progress=scaled)
                            st.session_state["photo_zip"][lg] = z_lg
                            st.session_state["missing_lists"][lg] = miss
                            st.success(f"{lg.upper()}: saved {s_lg} images.")
                    main_prog.progress(1.0)

                    if scope == "All (NL + FR)" and ("nl" in st.session_state["photo_zip"] or "fr" in st.session_state["photo_zip"]):
                        combo = io.BytesIO()
                        with zipfile.ZipFile(combo, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
                            for lg in ("nl", "fr"):
                                if lg in st.session_state["photo_zip"]:
                                    with zipfile.ZipFile(io.BytesIO(st.session_state["photo_zip"][lg])) as zlg:
                                        for name in zlg.namelist():
                                            z.writestr(name, zlg.read(name))
                        st.session_state["photo_zip"]["all"] = combo.getvalue()

    # --- Downloads ---
    if st.session_state.get("photo_zip"):
        ts = time.strftime("%Y%m%d_%H%M%S")
        base = f"medipim_photos_{ts}"
        st.markdown("### Downloads")

        if "all" in st.session_state["photo_zip"]:
            st.download_button(
                "Download ALL photos (ZIP)",
                data=io.BytesIO(st.session_state["photo_zip"]["all"]),
                file_name=f"{base}_ALL.zip",
                mime="application/zip"
            )
        if "nl" in st.session_state["photo_zip"] and "all" not in st.session_state["photo_zip"]:
            st.download_button(
                "Download NL photos (ZIP)",
                data=io.BytesIO(st.session_state["photo_zip"]["nl"]),
                file_name=f"{base}_NL.zip",
                mime="application/zip"
            )
        if "fr" in st.session_state["photo_zip"] and "all" not in st.session_state["photo_zip"]:
            st.download_button(
                "Download FR photos (ZIP)",
                data=io.BytesIO(st.session_state["photo_zip"]["fr"]),
                file_name=f"{base}_FR.zip",
                mime="application/zip"
            )

        if st.session_state.get("missing_lists"):
            miss_all = []
            for lg, miss in st.session_state["missing_lists"].items():
                for row in miss:
                    row["Lang"] = lg.upper()
                    miss_all.append(row)
            if miss_all:
                miss_df = pd.DataFrame(miss_all)
                miss_buf = io.BytesIO()
                with pd.ExcelWriter(miss_buf, engine="openpyxl") as writer:
                    miss_df.to_excel(writer, index=False)
                st.download_button(
                    "Download missing images list (.xlsx)",
                    data=miss_buf.getvalue(),
                    file_name=f"{base}_MISSING.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


