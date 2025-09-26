# Repository Image Download & Renaming + Medipim (integrato)

import streamlit as st
import pandas as pd
import csv
import os
import zipfile
import shutil
from PIL import Image, ImageOps, ImageChops, UnidentifiedImageError, ImageDraw
from io import BytesIO
import tempfile
import uuid
import asyncio
import aiohttp
import xml.etree.ElementTree as ET  # libreria standard
import requests
from zeep import Client, Settings
from zeep.wsse.username import UsernameToken
from zeep.transports import Transport
from zeep.cache import InMemoryCache
from zeep.plugins import HistoryPlugin

# ======== Import aggiuntivi per Medipim ========
import io
import time
import json
import base64
import pathlib
import hashlib
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# ==============================================

# Configurazione pagina (DEVE essere la prima operazione)
st.set_page_config(
    page_title="Repository Image Download & Renaming",
    page_icon="🖼️",
    layout="centered"
)

# Verifica autenticazione
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# --- CSS Globale per nascondere navigazione default e impostare larghezza sidebar ---
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
     .sidebar-title {
         font-size: 36px !important;
         font-weight: bold !important;
         color: #2c3e50;
         margin-bottom: 0px;
     }
     .sidebar-subtitle {
         font-size: 18px !important;
         font-weight: bold !important;
         color: #2c3e50;
         margin-top: 10px;
         margin-bottom: 5px;
     }
     .sidebar-desc {
         font-size: 16px;
         color: #2c3e50;
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
          background-color: #ecf0f1 !important;
          padding: 10px !important;
     }

    </style>
    """,
    unsafe_allow_html=True
)

# --- Bottone per tornare all'Hub nella Sidebar ---
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")  # separatore

# ----- Sidebar Content -----
st.sidebar.markdown("<div class='sidebar-title'>PDM Image Download and Renaming App</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='sidebar-subtitle'>What This App Does</div>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div class='sidebar-desc'>
- 📥 Downloads images from the selected server<br>
- 🔄 Resizes images to 1000x1000 in JPEG<br>
- 🏷️ Renames with a '-h1, -h2, etc' suffix
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("<div class='server-select-label'>Select Server Image</div>", unsafe_allow_html=True)
server_country = st.sidebar.selectbox("", options=["Switzerland", "Farmadati", "Medipim"], index=0, key="server_select_renaming")

# ----- Session State (Originale) -----
if "renaming_uploader_key" not in st.session_state:
    st.session_state.renaming_uploader_key = str(uuid.uuid4())
if "renaming_session_id" not in st.session_state:
    st.session_state.renaming_session_id = str(uuid.uuid4())

# ---------------------------------------------------------
# Function to combine SKUs from file and manual input
# ---------------------------------------------------------
def get_sku_list(uploaded_file_obj, manual_text):
    sku_list = []
    df_file = None
    if uploaded_file_obj is not None:
        try:
            if uploaded_file_obj.name.lower().endswith("csv"):
                uploaded_file_obj.seek(0)
                sample = uploaded_file_obj.read(1024).decode("utf-8", errors='ignore')
                uploaded_file_obj.seek(0)
                delimiter = ';'  # Default
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=';,\t')
                    delimiter = dialect.delimiter
                except Exception:
                    pass  # Use default
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

    # --- Bottone Reset ---
    if st.button("🧹 Clear Cache and Reset Data"):
        keys_to_remove = [k for k in st.session_state.keys() if k.startswith("renaming_") or k in ["uploader_key", "session_id", "processing_done", "zip_path", "error_path", "farmadati_zip", "farmadati_errors", "farmadati_ready", "process_images_switzerland", "process_images_farmadati"]]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.renaming_uploader_key = str(uuid.uuid4())
        st.info("Cache cleared. Please re-upload your file.")
        st.rerun()

    manual_input = st.text_area("Or paste your SKUs here (one per line):", key="manual_input_switzerland")
    uploaded_file = st.file_uploader("Upload file (Excel or CSV)", type=["xlsx", "csv"], key=st.session_state.renaming_uploader_key)

    if st.button("Search Images", key="process_switzerland"):
        st.session_state.renaming_start_processing_ch = True
        st.session_state.renaming_processing_done_ch = False
        if "renaming_zip_path_ch" in st.session_state:
            del st.session_state.renaming_zip_path_ch
        if "renaming_error_path_ch" in st.session_state:
            del st.session_state.renaming_error_path_ch

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
                if not pharmacode:
                    return None
                return f"https://documedis.hcisolutions.ch/2020-01/api/products/image/PICFRONT3D/Pharmacode/{pharmacode}/F"

            def process_and_save(original_sku, content, download_folder):
                try:
                    img = Image.open(BytesIO(content))
                    if img.mode != 'L':
                        gray = img.convert("L")
                    else:
                        gray = img
                    extrema = gray.getextrema()
                    if extrema == (0, 0):
                        raise ValueError("Empty image (black)")
                    if extrema == (255, 255):
                        raise ValueError("Empty image (white)")

                    img = ImageOps.exif_transpose(img)
                    bg = Image.new(img.mode, img.size, (255, 255, 255))
                    diff = ImageChops.difference(img, bg)
                    bbox = diff.getbbox()
                    if bbox:
                        img = img.crop(bbox)

                    if img.width == 0 or img.height == 0:
                        raise ValueError("Image empty after trim")

                    img.thumbnail((1000, 1000), Image.LANCZOS)
                    canvas = Image.new("RGB", (1000, 1000), (255, 255, 255))
                    offset_x = (1000 - img.width) // 2
                    offset_y = (1000 - img.height) // 2
                    canvas.paste(img, (offset_x, offset_y))
                    new_filename = f"{original_sku}-h1.jpg"
                    img_path = os.path.join(download_folder, new_filename)
                    canvas.save(img_path, "JPEG", quality=95)
                    return True
                except Exception:
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
                except Exception:
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
        if "renaming_zip_buffer_fd" in st.session_state:
            del st.session_state.renaming_zip_buffer_fd
        if "renaming_error_data_fd" in st.session_state:
            del st.session_state.renaming_error_data_fd

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
                        with open(zip_path_fd, "wb") as f:
                            f.write(response.ByteListFile)
                        with zipfile.ZipFile(zip_path_fd, 'r') as z:
                            xml_file = next((name for name in z.namelist() if name.upper().endswith('.XML')), None)
                            if not xml_file:
                                raise FileNotFoundError("XML not in ZIP")
                            z.extract(xml_file, tmp_dir)
                            xml_full_path = os.path.join(tmp_dir, xml_file)

                        context = ET.iterparse(xml_full_path, events=('end',))
                        for _, elem in context:
                            if elem.tag == 'RECORD':
                                t218 = elem.find('FDI_T218')
                                t438 = elem.find('FDI_T438')
                                if t218 is not None and t438 is not None and t218.text and t438.text:
                                    aic = t218.text.strip().lstrip("0")
                                    if aic:
                                        code_to_image[aic] = t438.text.strip()
                                elem.clear()
                    return code_to_image
                except Exception as e:
                    st.error(f"Error parsing Farmadati XML: {e}")
                    st.stop()

            def process_image_fd(img_bytes):
                try:
                    try:
                        img = Image.open(BytesIO(img_bytes))
                    except UnidentifiedImageError:
                        content_str = img_bytes.decode('utf-8', errors='ignore')
                        if "System.Web.HttpException" in content_str or "ASP.NET" in content_str:
                            raise ValueError("ASPX error page received instead of image")
                        else:
                            raise ValueError("Unknown image format")

                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')

                    if img.mode == 'L':
                        extrema = img.getextrema()
                    else:
                        gray = img.convert('L')
                        extrema = gray.getextrema()

                    if extrema == (0, 0) or extrema == (255, 255):
                        raise ValueError("Empty/blank image")

                    img = ImageOps.exif_transpose(img)

                    bg = Image.new(img.mode, img.size, (255, 255, 255))
                    diff = ImageChops.difference(img, bg)
                    bbox = diff.getbbox()
                    if bbox:
                        img = img.crop(bbox)

                    if img.width == 0 or img.height == 0:
                        raise ValueError("Empty image after trimming")

                    img.thumbnail((1000, 1000), Image.LANCZOS)

                    canvas = Image.new("RGB", (1000, 1000), (255, 255, 255))
                    offset = ((1000 - img.width) // 2, (1000 - img.height) // 2)
                    canvas.paste(img, offset)

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
                                progress_bar_fd.progress((i + 1) / total_fd, text=f"Processing {sku} ({i + 1}/{total_fd})")
                                original_sku = str(sku).strip()

                                clean_sku = original_sku.upper()
                                if not clean_sku.startswith("IT"):
                                    clean_sku = "IT" + clean_sku.lstrip("0")
                                else:
                                    clean_sku = "IT" + clean_sku[2:].lstrip("0")

                                if not clean_sku[2:]:
                                    error_list_fd.append((original_sku, "Invalid AIC (empty after IT)"))
                                    continue

                                image_name = aic_to_image.get(clean_sku[2:])
                                if not image_name:
                                    error_list_fd.append((original_sku, "AIC not in mapping"))
                                    continue

                                image_url = f"https://ws.farmadati.it/WS_DOC/GetDoc.aspx?accesskey={PASSWORD}&tipodoc=Z&nomefile={requests.utils.quote(image_name)}"

                                try:
                                    response = http_session.get(image_url, timeout=45)
                                    response.raise_for_status()

                                    content_type = response.headers.get('Content-Type', '').lower()
                                    if 'text/html' in content_type or 'text/plain' in content_type:
                                        if "System.Web.HttpException" in response.text:
                                            raise ValueError("ASPX error page received")

                                    if not response.content:
                                        raise ValueError("Empty response")

                                    processed_buffer = process_image_fd(response.content)
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
# SECTION: Medipim (NUOVO)
# ======================================================
elif server_country == "Medipim":
    st.header("Medipim Image Processing")
    st.markdown("""
    :information_source: **How to use:**
    - :arrow_right: **Insert your Medipim login credentials** (email and password).
    - :arrow_right: **Create a list of products:** Rename the column **sku** or use the Quick Report in Akeneo.
    - :arrow_right: **In Akeneo, select the following options:**
        - **File Type:** CSV or Excel  
        - **All Attributes or Grid Context** (for Grid Context, select ID)  
        - **With Codes**  
        - **Without Media**
    - :arrow_right: **Paste SKUs manually or upload a file (Excel/CSV).**
    - :arrow_right: **Select which images to download: NL only, FR only, or All (NL + FR).**
    """)

    # ---------------- Session state ----------------
    if "exports" not in st.session_state:
        st.session_state["exports"] = {}
    if "photo_zip" not in st.session_state:
        st.session_state["photo_zip"] = {}
    if "missing_lists" not in st.session_state:
        st.session_state["missing_lists"] = {}

    # ===============================
    # UI — Login & SKUs
    # ===============================
    with st.form("login_form", clear_on_submit=False):
        st.subheader("Medipim Credential")
        email = st.text_input("Email", value="", autocomplete="username")
        password = st.text_input("Password", value="", type="password", autocomplete="current-password")

        st.subheader("SKU or CNK codes input")
        sku_text = st.text_area(
            "Paste SKU or CNK codes (separated by spaces, commas, or newlines)",
            height=120,
            placeholder="e.g. BE04811337 or 4811337",
        )
        uploaded_skus = st.file_uploader(
            "Or upload a file with a 'sku' column (Excel or CSV)",
            type=["xlsx", "csv"],
            key="xls_skus"
        )

        scope = st.radio("**Select images**", ["All (NL + FR)", "NL only", "FR only"], index=0, horizontal=True)

        submitted = st.form_submit_button("**Download photos**")

    # Clear cache & data button
    clear_clicked = st.button("Clear cache and data", help="Delete temporary files and reset the app state")
    if clear_clicked:
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
        st.success(f"Cache cleared. Removed {removed} temp folder(s) and reset state.")

    # ===============================
    # Selenium driver + helpers (ROBUSTI)
    # ===============================
    def _find_chrome_binary_and_driver():
        """Prova a individuare Chrome/Chromium e chromedriver in vari percorsi."""
        import shutil as _shutil

        chrome_candidates = [
            os.environ.get("CHROME_PATH"),
            _shutil.which("chromium"),
            _shutil.which("chromium-browser"),
            _shutil.which("google-chrome"),
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/lib/chromium/chromium",
            "/opt/chrome/chrome",
        ]
        chrome_binary = next((p for p in chrome_candidates if p and os.path.exists(p)), None)

        driver_candidates = [
            os.environ.get("CHROMEDRIVER_PATH"),
            _shutil.which("chromedriver"),
            "/usr/bin/chromedriver",
            "/usr/lib/chromium/chromedriver",
            "/opt/chromedriver",
        ]
        chromedriver = next((p for p in driver_candidates if p and os.path.exists(p)), None)

        return chrome_binary, chromedriver

    def make_ctx(download_dir: str):
        """Crea un contesto Selenium robusto (headless new → headless classico; Service esplicito se driver presente)."""
        from selenium.webdriver.chrome.service import Service

        os.makedirs(download_dir, exist_ok=True)
        user_dir = os.path.join(tempfile.gettempdir(), f"chrome-user-{os.getpid()}")
        os.makedirs(user_dir, exist_ok=True)

        def build_options(headless_arg="--headless=new"):
            opt = webdriver.ChromeOptions()
            if headless_arg:
                opt.add_argument(headless_arg)
            opt.add_argument("--no-sandbox")
            opt.add_argument("--disable-dev-shm-usage")
            opt.add_argument("--disable-gpu")
            opt.add_argument("--no-zygote")
            opt.add_argument("--window-size=1440,1000")
            opt.add_argument("--remote-debugging-port=0")
            opt.add_argument(f"--user-data-dir={user_dir}")
            opt.add_experimental_option("prefs", {
                "download.default_directory": os.path.abspath(download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "download_restrictions": 0,
                "safebrowsing.enabled": True,
                "safebrowsing.disable_download_protection": True,
                "profile.default_content_setting_values.automatic_downloads": 1,
            })
            try:
                opt.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            except Exception:
                pass
            return opt

        chrome_binary, chromedriver = _find_chrome_binary_and_driver()

        # Prova 1: headless new
        opt = build_options("--headless=new")
        if chrome_binary:
            opt.binary_location = chrome_binary
        try:
            if chromedriver:
                service = Service(chromedriver)
                driver = webdriver.Chrome(service=service, options=opt)
            else:
                driver = webdriver.Chrome(options=opt)
        except WebDriverException as e_first:
            # Prova 2: headless classico
            opt = build_options("--headless")
            if chrome_binary:
                opt.binary_location = chrome_binary
            try:
                if chromedriver:
                    service = Service(chromedriver)
                    driver = webdriver.Chrome(service=service, options=opt)
                else:
                    driver = webdriver.Chrome(options=opt)
            except WebDriverException as e_second:
                msg = (
                    "Chrome failed to start.\n\n"
                    f"- chrome_binary: {chrome_binary!r}\n"
                    f"- chromedriver:  {chromedriver!r}\n"
                    f"- first error:   {e_first}\n"
                    f"- second error:  {e_second}\n\n"
                    "Controlla che in packages.txt ci siano 'chromium' e 'chromium-driver' e che i percorsi sopra esistano."
                )
                raise WebDriverException(msg) from e_second

        wait = WebDriverWait(driver, 40)
        actions = ActionChains(driver)

        # Abilita CDP per download ed eventi rete
        try:
            driver.execute_cdp_cmd("Network.enable", {})
        except Exception:
            pass
        try:
            driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": os.path.abspath(download_dir)})
        except Exception:
            pass

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

    def ensure_language(ctx, lang: str):  # 'nl' or 'fr'
        drv, wait = ctx["driver"], ctx["wait"]
        base = f"https://platform.medipim.be/{'nl/home' if lang=='nl' else 'fr/home'}"
        drv.get(base)
        handle_cookies(ctx)
        try:
            trig_span = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".I18nMenu .Dropdown > button.trigger span")))
            current = trig_span.text.strip().lower()
        except TimeoutException:
            current = ""
        if current != lang:
            try:
                trig = drv.find_element(By.CSS_SELECTOR, ".I18nMenu .Dropdown > button.trigger")
                drv.execute_script("arguments[0].click();", trig); time.sleep(0.2)
                if lang == "nl":
                    lang_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'I18nMenu')]//a[contains(@href,'/nl/')]")))
                else:
                    lang_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'I18nMenu')]//a[contains(@href,'/fr/')]")))
                drv.execute_script("arguments[0].click();", lang_link); time.sleep(0.4)
            except TimeoutException:
                pass

    def open_export_dropdown(ctx):
        drv, wait = ctx["driver"], ctx["wait"]
        split = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.SplitButton")))
        trigger = split.find_element(By.CSS_SELECTOR, "button.trigger")
        for _ in range(4):
            if trigger.get_attribute("aria-expanded") == "true":
                break
            drv.execute_script("arguments[0].click();", trigger); time.sleep(0.25)
        if trigger.get_attribute("aria-expanded") != "true":
            raise TimeoutException("Export dropdown did not open.")
        dd = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Dropdown.open div.dropdown")))
        return dd

    def click_excel_option(ctx, dropdown):
        actions = ctx["actions"]
        excel_btn = dropdown.find_element(By.CSS_SELECTOR, "div.actions > button:nth-of-type(2)")
        try:
            actions.move_to_element(excel_btn).pause(0.1).click().perform()
        except Exception:
            ctx["driver"].execute_script("arguments[0].click();", excel_btn)

    def select_all_attributes(ctx):
        drv = ctx["driver"]
        try:
            all_attr = WebDriverWait(drv, 8).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//a[contains(., 'Alles selecteren')] | //button[contains(., 'Alles selecteren')] | "
                    "//a[contains(., 'Sélectionner tout') or contains(., 'Selectionner tout')] | "
                    "//button[contains(., 'Sélectionner tout') or contains(., 'Selectionner tout')] | "
                    "//button[contains(., 'Select all')] | //a[contains(., 'Select all')]"
                ))
            )
            drv.execute_script("arguments[0].click();", all_attr)
        except TimeoutException:
            pass

    def wait_for_xlsx_on_disk(ctx, start_time: float, timeout=60) -> pathlib.Path | None:
        download_dir = ctx["download_dir"]
        end = time.time() + timeout
        margin = 2.0
        while time.time() < end:
            files = [
                (f, os.path.getmtime(os.path.join(download_dir, f)))
                for f in os.listdir(download_dir)
                if f.lower().endswith(".xlsx")
            ]
            fresh = [f for f, m in files if m >= (start_time - margin)]
            if fresh:
                fresh.sort(key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), reverse=True)
                return pathlib.Path(os.path.join(download_dir, fresh[0]))
            time.sleep(0.5)
        return None

    def try_save_xlsx_from_perflog(ctx, timeout=15) -> bytes | None:
        drv = ctx["driver"]
        deadline = time.time() + timeout
        seen = set()
        try:
            drv.execute_cdp_cmd("Network.enable", {})
        except Exception:
            pass
        while time.time() < deadline:
            try:
                logs = drv.get_log('performance')
            except Exception:
                logs = []
            for entry in logs:
                try:
                    payload = json.loads(entry.get('message', '{}'))
                    m = payload.get("message", {})
                except Exception:
                    continue
                if m.get("method") != "Network.responseReceived":
                    continue
                params = m.get("params", {})
                resp = params.get("response", {})
                req_id = params.get("requestId")
                if not req_id or req_id in seen:
                    continue
                seen.add(req_id)
                mime = (resp.get("mimeType") or "").lower()
                url = (resp.get("url") or "").lower()
                if ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in mime) or url.endswith(".xlsx"):
                    try:
                        body = drv.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                        data = body.get('body', '')
                        raw = base64.b64decode(data) if body.get('base64Encoded') else data.encode('utf-8', 'ignore')
                        return raw
                    except Exception:
                        pass
            time.sleep(0.3)
        return None

    def run_export_and_get_bytes(ctx, lang: str, refs: str) -> bytes | None:
        ensure_language(ctx, lang)
        if lang == "nl":
            url = f"https://platform.medipim.be/nl/producten?search=refcode[{refs.replace(' ', '%20')}]"
        else:
            url = f"https://platform.medipim.be/fr/produits?search=refcode[{refs.replace(' ', '%20')}]"

        drv, wait = ctx["driver"], ctx["wait"]
        drv.get(url)
        handle_cookies(ctx)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.SplitButton")))
        dd = open_export_dropdown(ctx)
        click_excel_option(ctx, dd)

        select_all_attributes(ctx)

        try:
            create_btn = WebDriverWait(drv, 25).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(., 'AANMAKEN')] | //button[contains(., 'Aanmaken')] | "
                    "//button[contains(., 'Create')] | "
                    "//button[contains(., 'Créer') or contains(., 'Creer')]"
                ))
            )
            drv.execute_script("arguments[0].click();", create_btn)
        except TimeoutException:
            pass

        try:
            WebDriverWait(drv, 40).until(
                EC.presence_of_element_located((By.XPATH,
                    "//*[contains(., 'Export is klaar') or contains(., 'Export gereed') or "
                    "contains(., 'Export ready') or contains(., 'Export prêt') or contains(., 'Export est prêt')]"
                ))
            )
        except TimeoutException:
            pass

        dl = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//button[contains(., 'DOWNLOAD')] | //a[contains(., 'DOWNLOAD')] | "
            "//button[contains(., 'Download')] | //a[contains(., 'Download')] | "
            "//button[contains(., 'Télécharger') or contains(., 'Telecharger')] | "
            "//a[contains(., 'Télécharger') or contains(., 'Telecharger')]"
        )))
        href = (dl.get_attribute("href") or dl.get_attribute("data-href") or "").strip().lower()
        start = time.time()
        if href and (not href.startswith("javascript")) and (not href.startswith("blob:")):
            drv.get(href)
        else:
            drv.execute_script("arguments[0].click();", dl)

        disk = wait_for_xlsx_on_disk(ctx, start_time=start, timeout=60)
        if disk and disk.exists():
            return disk.read_bytes()
        return try_save_xlsx_from_perflog(ctx, timeout=15)

    def do_login(ctx, email_addr: str, pwd: str):
        drv, wait = ctx["driver"], ctx["wait"]
        drv.get("https://platform.medipim.be/nl/inloggen")
        handle_cookies(ctx)
        try:
            email_el = wait.until(EC.presence_of_element_located((By.ID, "form0.email")))
            pwd_el = wait.until(EC.presence_of_element_located((By.ID, "form0.password")))
            email_el.clear(); email_el.send_keys(email_addr)
            pwd_el.clear();   pwd_el.send_keys(pwd)
            submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.SubmitButton")))
            drv.execute_script("arguments[0].click();", submit)
            wait.until(EC.invisibility_of_element_located((By.ID, "form0.email")))
        except TimeoutException:
            pass

    # ===============================
    # SKU parsing (normalizzata)
    # ===============================
    def _normalize_sku(raw: str) -> Optional[str]:
        """Rimuove tutto ciò che non è cifra e toglie gli zeri iniziali."""
        if not raw:
            return None
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return None
        return digits.lstrip("0") or digits  # se tutto zero, torna "0"

    def parse_skus(sku_text: str, uploaded_file) -> List[str]:
        skus: List[str] = []
        if sku_text:
            raw = sku_text.replace(",", " ").split()
            skus.extend([x.strip() for x in raw if x.strip()])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.lower().endswith(".csv"):
                    df = pd.read_csv(uploaded_file, dtype=str)
                else:
                    df = pd.read_excel(uploaded_file, engine="openpyxl")
                df.columns = [c.lower().strip() for c in df.columns]
                if "sku" in df.columns:
                    ex_skus = df["sku"].astype(str).map(lambda x: x.strip()).tolist()
                    skus.extend([x for x in ex_skus if x])
            except Exception as e:
                st.error(f"Failed to read uploaded file: {e}")
        # normalizza + dedup
        seen, out = set(), []
        for s in skus:
            norm = _normalize_sku(s)
            if norm and norm not in seen:
                seen.add(norm)
                out.append(norm)
        return out
    # ===============================
    # Photo processing — constants
    # ===============================
    DEDUP_DHASH_THRESHOLD = 3  # Hamming distance per dHash (0..64)
    TYPE_RANK = {
        "photo du produit": 1,
        "productfoto": 1,
        "photo de l'emballage": 2,
        "verpakkingsfoto": 2,
        "photo promotionnelle": 3,
        "sfeerbeeld": 3,
    }

    # ===============================
    # Helpers: Excel parse
    # ===============================
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

    # ===============================
    # Image helpers (cached & parallel)
    # ===============================
    @st.cache_data(show_spinner=False, ttl=24*3600, max_entries=10000)
    def _fetch_url_cached(url: str) -> Optional[bytes]:
        """Scarica e cache-a i bytes dell'immagine per URL (cache 24h)."""
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200 or not r.content:
                return None
            return r.content
        except Exception:
            return None

    def _download_many(urls: List[str], progress: Optional[st.progress] = None, max_workers: int = 16) -> Dict[str, Optional[bytes]]:
        """Scarica in parallelo gli URL, usando la cache per ogni URL."""
        results: Dict[str, Optional[bytes]] = {}
        total = len(urls)
        done = 0
        next_update = 0.0

        def task(u):
            return u, _fetch_url_cached(u)

        if total == 0:
            return results

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(task, u) for u in urls]
            for f in as_completed(futures):
                u, content = f.result()
                results[u] = content
                done += 1
                frac = done / total
                if progress and frac >= next_update:
                    progress.progress(min(1.0, frac))
                    next_update += 0.05  # update ogni 5%

        if progress:
            progress.progress(1.0)
        return results

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

    # Compat LANCZOS
    try:
        _RESAMPLE_LANCZOS = Image.Resampling.LANCZOS  # PIL >= 9.1
    except Exception:
        _RESAMPLE_LANCZOS = Image.LANCZOS

    def _dhash(image: Image.Image, hash_size: int = 8) -> int:
        """Perceptual difference hash (dHash)."""
        img = image.convert("L").resize((hash_size + 1, hash_size), _RESAMPLE_LANCZOS)
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

    def _hash_bytes(b: bytes) -> str:
        return hashlib.md5(b).hexdigest()

    def _process_one(url: str, content: Optional[bytes]) -> Tuple[str, Optional[Tuple[bytes, int, str]]]:
        """Elabora un'immagine (bytes → canvas 1000 → jpeg → dhash/md5)."""
        if content is None:
            return url, None
        try:
            img = Image.open(io.BytesIO(content))
            img.load()
            processed = _to_1000_canvas(img)
            dh = _dhash(processed, hash_size=8)
            jb = _jpeg_bytes(processed)
            md5 = _hash_bytes(jb)
            return url, (jb, dh, md5)
        except Exception:
            return url, None

    def _process_many(urls: List[str], contents: Dict[str, Optional[bytes]], progress: Optional[st.progress] = None, max_workers: int = 16) -> Dict[str, Optional[Tuple[bytes, int, str]]]:
        """Elabora in parallelo i contenuti scaricati."""
        results: Dict[str, Optional[Tuple[bytes, int, str]]] = {}
        total = len(urls)
        done = 0
        next_update = 0.0

        if total == 0:
            return results

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_process_one, u, contents.get(u)) for u in urls]
            for f in as_completed(futures):
                u, triple = f.result()
                results[u] = triple
                done += 1
                frac = done / total
                if progress and frac >= next_update:
                    progress.progress(min(1.0, frac))
                    next_update += 0.05

        if progress:
            progress.progress(1.0)
        return results

    # ===============================
    # Build ZIP (parallelo + dedup)
    # ===============================
    class ScaledProgress:
        """Proxy around una progress bar unica, con finestra [start,end]."""
        def __init__(self, widget, start: float, end: float):
            self.widget = widget
            self.start = float(start)
            self.end = float(end)
        def progress(self, frac: float):
            frac = max(0.0, min(1.0, float(frac)))
            val = self.start + (self.end - self.start) * frac
            self.widget.progress(min(1.0, max(0.0, val)))

    def build_zip_for_lang(xlsx_bytes: bytes, lang: str, progress: ScaledProgress) -> Tuple[bytes, int, int, List[Dict[str, str]]]:
        """
        Pipeline:
          1) Parse/sort
          2) Download parallelo (cache)
          3) Processing parallelo (canvas+hash)
          4) Dedup per CNK
          5) Scrittura ZIP
        """
        products_df, photos_df = _read_book(xlsx_bytes)
        id_cnk = _extract_id_cnk(products_df)
        photos_raw = _extract_photos(photos_df)

        id2cnk: Dict[str, str] = {str(row["ID"]).strip(): str(row["CNK"]).strip() for _, row in id_cnk.iterrows()}

        try:
            all_pids_set = set(photos_raw["Product ID"].astype(str).str.strip())
        except Exception:
            all_pids_set = set()

        def _rank_type(t: str) -> int:
            if not isinstance(t, str):
                return 99
            return TYPE_RANK.get(t.strip().lower(), 99)

        photos = photos_raw.dropna(subset=["URL"]).copy()
        photos["rank_type"] = photos["Type"].map(_rank_type)
        photos["rank_photoid"] = pd.to_numeric(photos["Photo ID"], errors="coerce").fillna(10**9).astype(int)
        photos.sort_values(["Product ID", "rank_type", "rank_photoid"], inplace=True)

        records = []
        for _, r in photos.iterrows():
            pid = str(r["Product ID"]).strip()
            url = str(r["URL"]).strip()
            cnk = id2cnk.get(pid)
            records.append({"pid": pid, "cnk": cnk, "url": url})

        # Download parallelo (0→40%)
        dl_prog = ScaledProgress(progress.widget, progress.start, progress.start + (progress.end - progress.start) * 0.40)
        url_list = [rec["url"] for rec in records]
        url_contents = _download_many(url_list, progress=dl_prog, max_workers=16)

        # Processing parallelo (40→85%)
        pr_prog = ScaledProgress(progress.widget, progress.start + (progress.end - progress.start) * 0.40, progress.start + (progress.end - progress.start) * 0.85)
        processed_map = _process_many(url_list, url_contents, progress=pr_prog, max_workers=16)

        # Dedup + ZIP (85→100%)
        zip_prog = ScaledProgress(progress.widget, progress.start + (progress.end - progress.start) * 0.85, progress.end)
        zip_buf = io.BytesIO()
        zf = zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED)

        attempted = 0
        saved = 0
        cnk_hashes: Dict[str, set] = {}
        cnk_phashes: Dict[str, List[int]] = {}
        missing: List[Dict[str, str]] = []

        total = len(records)
        done = 0
        next_update = 0.0

        for rec in records:
            attempted += 1
            pid = rec["pid"]
            cnk = rec["cnk"]
            url = rec["url"]

            if not cnk:
                missing.append({"Product ID": pid, "CNK": None, "URL": url, "Reason": "No CNK"})
                done += 1
                frac = done / max(1, total)
                if frac >= next_update:
                    zip_prog.progress(frac); next_update += 0.05
                continue

            triple = processed_map.get(url)
            if not triple:
                reason = "Download failed" if url_contents.get(url) is None else "Processing failed"
                missing.append({"Product ID": pid, "CNK": cnk, "URL": url, "Reason": reason})
                done += 1
                frac = done / max(1, total)
                if frac >= next_update:
                    zip_prog.progress(frac); next_update += 0.05
                continue

            jb, dh, md5 = triple

            if cnk not in cnk_hashes:
                cnk_hashes[cnk] = set()
            if cnk not in cnk_phashes:
                cnk_phashes[cnk] = []

            if md5 in cnk_hashes[cnk]:
                done += 1
                frac = done / max(1, total)
                if frac >= next_update:
                    zip_prog.progress(frac); next_update += 0.05
                continue
            if any(_hamming(dh, existing) <= DEDUP_DHASH_THRESHOLD for existing in cnk_phashes[cnk]):
                done += 1
                frac = done / max(1, total)
                if frac >= next_update:
                    zip_prog.progress(frac); next_update += 0.05
                continue

            cnk_hashes[cnk].add(md5)
            cnk_phashes[cnk].append(dh)
            n = len(cnk_hashes[cnk])
            filename = f"BE0{cnk}-{lang}-h{n}.jpg"
            zf.writestr(filename, jb)
            saved += 1

            done += 1
            frac = done / max(1, total)
            if frac >= next_update:
                zip_prog.progress(frac); next_update += 0.05

        # prodotti senza righe "Photos"
        for pid, cnk in id_cnk.values:
            pid = str(pid)
            cnk = str(cnk)
            if pid not in all_pids_set:
                missing.append({"Product ID": pid, "CNK": cnk, "URL": None, "Reason": "No photos in export"})

        zf.close()
        zip_prog.progress(1.0)
        return zip_buf.getvalue(), attempted, saved, missing

    # ===============================
    # Orchestrator — single session per NL/FR (robusto)
    # ===============================
    def run_exports_with_progress_single_session(email: str, password: str, refs: str, langs: List[str], prog_widget, start: float, end: float):
        """
        Una sola sessione Chrome: login una volta, poi export per le lingue richieste
        """
        results = {}
        tmpdir = tempfile.mkdtemp(prefix="medipim_all_")
        ctx = None
        try:
            try:
                ctx = make_ctx(tmpdir)
            except WebDriverException as e:
                st.error(f"❌ Selenium/Chrome non avviato:\n\n{e}")
                return results

            do_login(ctx, email, password)
            step = (end - start) / max(1, len(langs))
            for i, lang in enumerate(langs):
                prog_widget.progress(start + step * i)
                data = run_export_and_get_bytes(ctx, lang, refs)
                if data:
                    results[lang] = data
                else:
                    st.error(f"{lang.upper()} export failed: no XLSX found.")
                prog_widget.progress(start + step * (i + 1))
        finally:
            if ctx and "driver" in ctx:
                try:
                    ctx["driver"].quit()
                except Exception:
                    pass
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
        return results

    # ===============================
    # Main flow
    # ===============================
    if submitted:
        st.session_state["exports"] = {}
        st.session_state["photo_zip"] = {}
        st.session_state["missing_lists"] = {}

        if not email or not password:
            st.error("Please enter your email and password.")
        else:
            skus = parse_skus(sku_text, uploaded_skus)
            if not skus:
                st.error("Please provide at least one SKU (textarea or Excel).")
            else:
                refs = " ".join(skus)
                if scope == "NL only":
                    langs = ["nl"]
                elif scope == "FR only":
                    langs = ["fr"]
                else:
                    langs = ["nl", "fr"]

                main_prog = st.progress(0.0)
                export_end = 0.5 if len(langs) == 1 else 0.6
                results = run_exports_with_progress_single_session(email, password, refs, langs, main_prog, 0.0, export_end)
                if not results:
                    st.stop()

                proc_start = export_end
                proc_end = 1.0
                per_lang = (proc_end - proc_start) / max(1, len(langs))

                for i, lg in enumerate(langs):
                    if lg in results:
                        st.info(f"Processing {lg.upper()} images…")
                        scaled = ScaledProgress(main_prog, proc_start + per_lang * i, proc_start + per_lang * (i + 1))
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

    # ===============================
    # Downloads (ZIP and missing list)
    # ===============================
    if st.session_state["photo_zip"]:
        ts = time.strftime("%Y%m%d_%H%M%S")
        base = f"medipim_photos_{ts}"

        st.markdown("### Downloads")
        if "all" in st.session_state["photo_zip"]:
            st.download_button(
                "Download ALL photos (ZIP)",
                data=io.BytesIO(st.session_state["photo_zip"]["all"]),
                file_name=f"{base}_ALL.zip",
                mime="application/zip",
                key="zip_all",
            )
        if "nl" in st.session_state["photo_zip"] and "all" not in st.session_state["photo_zip"]:
            st.download_button(
                "Download NL photos (ZIP)",
                data=io.BytesIO(st.session_state["photo_zip"]["nl"]),
                file_name=f"{base}_NL.zip",
                mime="application/zip",
                key="zip_nl",
            )
        if "fr" in st.session_state["photo_zip"] and "all" not in st.session_state["photo_zip"]:
            st.download_button(
                "Download FR photos (ZIP)",
                data=io.BytesIO(st.session_state["photo_zip"]["fr"]),
                file_name=f"{base}_FR.zip",
                mime="application/zip",
                key="zip_fr",
            )

        if st.session_state["missing_lists"]:
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
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="miss_xlsx",
                )
