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
from PIL import Image, ImageChops, UnidentifiedImageError
from cryptography.fernet import Fernet # Assicurati sia in requirements.txt

# --- Page Configuration (Specific for this page) ---
st.set_page_config(
    page_title="Bundle & Set Creator",
    layout="wide" # Puoi scegliere 'centered' o 'wide'
)

# ---------------------- Custom CSS (Potrebbe influenzare altre pagine) ----------------------
# Rimuovi o commenta stili CSS che non vuoi siano globali se causano problemi
st.markdown(
    """
    <style>
    /* Stile personalizzato per i pulsanti generici */
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
    /* Stile personalizzato per i bottoni di download */
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
    /* Riduci il padding superiore della parte centrale per far partire il testo più in alto */
    .main .block-container{ /* Rimosso .reportview-container */
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------- Session State Management (Rimosso 'authenticated') ----------------------
# 'session_id' è utile per isolare i file tra diverse esecuzioni/utenti
if "bundle_app_session_id" not in st.session_state: # Usa un nome univoco
    st.session_state["bundle_app_session_id"] = str(uuid.uuid4())

# ---------------------- LOGIN RIMOSSO ----------------------

# ---------------------- Begin Main App Code ----------------------
# Creazione di una cartella unica per ogni sessione
session_id = st.session_state["bundle_app_session_id"]
# La cartella di output per la sessione corrente (isolata)
base_folder = f"BundleSetOutput_{session_id}"

# ----- Pulizia automatica dei file della sessione corrente -----
def clear_old_data():
    current_session_id = st.session_state.get("bundle_app_session_id")
    if not current_session_id: return # Sicurezza

    folder_to_clear = f"BundleSetOutput_{current_session_id}"
    if os.path.exists(folder_to_clear):
        try:
            shutil.rmtree(folder_to_clear)
        except Exception as e:
            st.warning(f"Could not fully clear old data folder {folder_to_clear}: {e}")

    # Elimina eventuali ZIP della sessione corrente
    zip_path = f"BundleSetImages_{current_session_id}.zip"
    if os.path.exists(zip_path):
        try:
            os.remove(zip_path)
        except Exception as e:
            st.warning(f"Could not remove old zip file {zip_path}: {e}")

    # Elimina il file CSV degli errori se esistente
    missing_csv_path = f"missing_images_{current_session_id}.csv"
    bundle_list_csv_path = f"bundle_list_{current_session_id}.csv"
    if os.path.exists(missing_csv_path):
        try:
            os.remove(missing_csv_path)
        except Exception as e:
             st.warning(f"Could not remove old missing csv {missing_csv_path}: {e}")
    if os.path.exists(bundle_list_csv_path):
        try:
            os.remove(bundle_list_csv_path)
        except Exception as e:
             st.warning(f"Could not remove old bundle list csv {bundle_list_csv_path}: {e}")


# ---------------------- Helper Functions (Invariate) ----------------------
async def async_download_image(product_code, extension, session):
    # Se il product_code inizia per '1' o '0', aggiunge il prefisso "D"
    clean_product_code = str(product_code).strip()
    if clean_product_code.startswith(('1', '0')):
        clean_product_code = f"D{clean_product_code}"
    if not clean_product_code: return None, None # Codice vuoto

    url = f"https://cdn.shop-apotheke.com/images/{clean_product_code}-p{extension}.jpg"
    try:
        # Timeout per evitare attese infinite
        async with session.get(url, timeout=20) as response:
            if response.status == 200:
                content = await response.read()
                # Controllo base sul contenuto (non vuoto)
                if content:
                    return content, url
                else:
                    return None, url # Contenuto vuoto ma status 200? Strano, ma gestiamolo
            else:
                return None, url # Status non 200
    except asyncio.TimeoutError:
        # st.warning(f"Timeout downloading {url}") # Potrebbe essere troppo verboso
        return None, url
    except aiohttp.ClientError as e:
        # st.warning(f"Network error downloading {url}: {e}") # Potrebbe essere troppo verboso
        return None, url
    except Exception as e:
        # st.warning(f"Generic error downloading {url}: {e}") # Potrebbe essere troppo verboso
        return None, url


def trim(im):
    """Rimuove i bordi bianchi dall'immagine."""
    try:
        bg = Image.new(im.mode, im.size, (255, 255, 255))
        diff = ImageChops.difference(im, bg)
        bbox = diff.getbbox()
        if bbox:
            # Aggiungi un piccolo margine per evitare tagli troppo stretti
            bbox = (max(0, bbox[0]-2), max(0, bbox[1]-2),
                    min(im.width, bbox[2]+2), min(im.height, bbox[3]+2))
            return im.crop(bbox)
        return im # Nessun bordo trovato o immagine bianca
    except Exception:
        return im # In caso di errore, ritorna l'originale

def process_image_bundle(image_bytes, num_products, layout="automatic"):
    """Processa immagine per bundle: apre, trimma, combina se necessario, ridimensiona, mette su canvas."""
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img) # Corregge orientamento

        # Controlla se l'immagine è completamente bianca o nera prima del trim
        if img.mode != 'L': gray_img = img.convert('L')
        else: gray_img = img
        extrema = gray_img.getextrema()
        if extrema == (0, 0) or extrema == (255, 255):
             raise ValueError("Image is completely black or white.")

        img = trim(img) # Rimuove bordi bianchi

        if img.width == 0 or img.height == 0: # Controllo dopo trim
             raise ValueError("Image became empty after trimming.")

        if num_products in [2, 3]:
            width, height = img.size
            # Logica layout automatico
            chosen_layout = layout.lower()
            if chosen_layout == "automatic":
                chosen_layout = "vertical" if height < width else "horizontal"

            # Creazione immagine combinata
            if num_products == 2:
                if chosen_layout == "horizontal":
                    merged_width, merged_height = width * 2, height
                    merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
                    merged_image.paste(img, (0, 0))
                    merged_image.paste(img, (width, 0))
                else: # Vertical
                    merged_width, merged_height = width, height * 2
                    merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
                    merged_image.paste(img, (0, 0))
                    merged_image.paste(img, (0, height))
            else: # num_products == 3
                if chosen_layout == "horizontal":
                    merged_width, merged_height = width * 3, height
                    merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
                    merged_image.paste(img, (0, 0))
                    merged_image.paste(img, (width, 0))
                    merged_image.paste(img, (width * 2, 0))
                else: # Vertical
                    merged_width, merged_height = width, height * 3
                    merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
                    merged_image.paste(img, (0, 0))
                    merged_image.paste(img, (0, height))
                    merged_image.paste(img, (0, height * 2))

            # Ridimensiona immagine combinata per farla stare in 1000x1000
            merged_image.thumbnail((1000, 1000), Image.LANCZOS)
            final_image_content = merged_image

        else: # Bundle di 1 o > 3 (o se non specificato) - solo resize
            img.thumbnail((1000, 1000), Image.LANCZOS)
            final_image_content = img

        # Metti su canvas 1000x1000
        final_canvas = Image.new("RGB", (1000, 1000), (255, 255, 255))
        x_offset = (1000 - final_image_content.width) // 2
        y_offset = (1000 - final_image_content.height) // 2
        final_canvas.paste(final_image_content, (x_offset, y_offset))

        # Salva in buffer JPEG
        buffer = BytesIO()
        final_canvas.save(buffer, "JPEG", quality=100) # Qualità 100
        buffer.seek(0)
        return buffer

    except UnidentifiedImageError:
        raise ValueError("Cannot identify image file (corrupted or wrong format).")
    except ValueError as ve: # Propaga errore immagine vuota/nera/bianca
         raise ve
    except Exception as e:
        raise RuntimeError(f"Error during image processing: {e}")


def save_binary_file(path, data):
    """Salva in maniera sincrona dei dati binari su file."""
    try:
        with open(path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        st.warning(f"Failed to save file {os.path.basename(path)}: {e}")
        return False

async def async_get_nl_fr_images(product_code, session):
    tasks = [
        async_download_image(product_code, "1-fr", session),
        async_download_image(product_code, "1-nl", session)
    ]
    results = await asyncio.gather(*tasks)
    images = {}
    # Solo se il contenuto non è None
    if results[0][0]: images["1-fr"] = results[0][0]
    if results[1][0]: images["1-nl"] = results[1][0]
    return images

async def async_get_image_with_fallback(product_code, session):
    """Tenta di scaricare l'immagine con varie strategie di fallback."""
    # 1. Prova gestione speciale NL FR
    fallback_opt = st.session_state.get("bundle_fallback_ext", None)
    if fallback_opt == "NL FR":
        images_dict = await async_get_nl_fr_images(product_code, session)
        if images_dict: # Se trova almeno una tra FR o NL
            return images_dict, "NL FR" # Ritorna il dizionario

    # 2. Prova estensioni standard '1' poi '10'
    for ext in ["1", "10"]:
        content, _ = await async_download_image(product_code, ext, session)
        if content:
            return content, ext # Ritorna il contenuto binario e l'estensione trovata

    # 3. Prova fallback specifico (es. '1-fr', '1-de') se diverso da NL FR
    if fallback_opt and fallback_opt not in ["NL FR", None]:
        content, _ = await async_download_image(product_code, fallback_opt, session)
        if content:
            return content, fallback_opt # Ritorna contenuto binario e estensione fallback

    # 4. Nessuna immagine trovata
    return None, None


# ---------------------- Main Processing Function ----------------------
async def process_file_async(uploaded_file, progress_bar=None, layout="automatic"):
    session_id = st.session_state["bundle_app_session_id"]
    base_folder = f"BundleSetOutput_{session_id}" # Assicurati sia lo stesso nome
    missing_images_csv_path = f"missing_images_{session_id}.csv"
    bundle_list_csv_path = f"bundle_list_{session_id}.csv"

    # Crittografia (Mantenuta per ora)
    if "bundle_encryption_key" not in st.session_state:
        st.session_state["bundle_encryption_key"] = Fernet.generate_key()
    key = st.session_state["bundle_encryption_key"]
    f = Fernet(key)

    file_bytes = uploaded_file.read()
    try:
        # Nota: La crittografia potrebbe non essere necessaria senza login
        encrypted_bytes = f.encrypt(file_bytes)
        decrypted_bytes = f.decrypt(encrypted_bytes)
    except Exception as e:
        st.error(f"Error during file encryption/decryption: {e}. Check file integrity or remove encryption step.")
        return None, None, None, None

    csv_file = BytesIO(decrypted_bytes)
    try:
        # Specifica dtype=str per evitare conversioni automatiche
        data = pd.read_csv(csv_file, delimiter=';', dtype=str, skipinitialspace=True)
    except Exception as e:
        st.error(f"Error reading CSV data: {e}. Ensure it's semicolon-delimited UTF-8.")
        return None, None, None, None

    required_columns = {'sku', 'pzns_in_set'}
    actual_columns = {col.strip().lower() for col in data.columns} # Normalizza colonne lette

    # Trova i nomi esatti delle colonne (case-insensitive)
    sku_col_name = next((col for col in data.columns if col.strip().lower() == 'sku'), None)
    pzns_col_name = next((col for col in data.columns if col.strip().lower() == 'pzns_in_set'), None)

    missing_req_cols = []
    if not sku_col_name: missing_req_cols.append('sku')
    if not pzns_col_name: missing_req_cols.append('pzns_in_set')

    if missing_req_cols:
        st.error(f"Missing required columns (case-insensitive): {', '.join(missing_req_cols)}")
        return None, None, None, None

    if data.empty:
        st.error("The CSV file is empty or contains no valid data rows!")
        return None, None, None, None

    # Seleziona e pulisci i dati usando i nomi colonna trovati
    data = data[[sku_col_name, pzns_col_name]].copy() # Usa i nomi corretti
    data.rename(columns={sku_col_name: 'sku', pzns_col_name: 'pzns_in_set'}, inplace=True) # Rinomina a standard
    data['sku'] = data['sku'].astype(str).str.strip()
    data['pzns_in_set'] = data['pzns_in_set'].astype(str).str.strip()
    # Rimuovi righe con SKU o PZN vuoti DOPO lo strip
    data.dropna(subset=['sku', 'pzns_in_set'], inplace=True)
    data = data[data['sku'] != '']
    data = data[data['pzns_in_set'] != '']

    if data.empty:
        st.error("No valid rows found after cleaning (empty SKU or PZN list).")
        return None, None, None, None

    st.write(f"File validated: {len(data)} potential bundles to process.")
    os.makedirs(base_folder, exist_ok=True)

    mixed_folder = os.path.join(base_folder, "mixed_sets")
    cross_country_folder = os.path.join(base_folder, "cross-country") # Cartella unica per tutti i cross-country

    error_list = []      # Lista di tuple: (bundle_code, product_code, reason)
    bundle_list = []     # Dettagli: [bundle_code, pzn_string, bundle_type, cross_country_flag]

    total = len(data)
    processed_bundles_count = 0

    connector = aiohttp.TCPConnector(limit=50) # Limita connessioni
    timeout = aiohttp.ClientTimeout(total=60) # Timeout globale per richiesta
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for i, row in data.iterrows():
            bundle_code = row['sku']
            pzns_in_set_raw = row['pzns_in_set']
            progress_text = f"Processing bundle {i+1}/{total}: {bundle_code}"
            if progress_bar: progress_bar.progress((i + 1) / total, text=progress_text)

            product_codes = [code.strip() for code in pzns_in_set_raw.split(',') if code.strip()]

            if not product_codes:
                 st.warning(f"Skipping bundle {bundle_code}: 'pzns_in_set' is empty or invalid.")
                 error_list.append((bundle_code, '', 'Empty PZN list'))
                 continue

            num_products = len(product_codes)
            unique_product_codes = set(product_codes)
            is_uniform = (len(unique_product_codes) == 1)
            bundle_type = f"bundle of {num_products}" if is_uniform else "mixed set"
            bundle_cross_country = False # Flag per indicare se *almeno una* img nel bundle è cross-country

            if is_uniform:
                product_code = product_codes[0]
                # Determina cartella base per bundle uniformi
                output_folder = os.path.join(base_folder, f"bundle_{num_products}")

                result, used_ext = await async_get_image_with_fallback(product_code, session)

                if result is None:
                    error_list.append((bundle_code, product_code, 'Image not found'))
                    continue # Passa al prossimo bundle

                # Gestione risultato
                if used_ext == "NL FR":
                    # Gestisce NL FR per bundle uniformi
                    bundle_cross_country = True # NL/FR è sempre cross-country
                    output_folder = cross_country_folder # Salva in cartella cross-country
                    os.makedirs(output_folder, exist_ok=True)
                    processed_nl_fr = False
                    for lang, image_data in result.items(): # result è un dict
                        suffix = "-p1-fr.jpg" if lang == "1-fr" else "-p1-nl.jpg"
                        try:
                            processed_image_buffer = await asyncio.to_thread(process_image_bundle, image_data, num_products, layout)
                            save_path = os.path.join(output_folder, f"{bundle_code}{suffix}")
                            await asyncio.to_thread(save_binary_file, save_path, processed_image_buffer.read())
                            processed_nl_fr = True
                        except (ValueError, RuntimeError, Exception) as e:
                            error_list.append((bundle_code, f"{product_code} ({lang})", f'Processing error: {e}'))
                    if not processed_nl_fr: # Se entrambe le processazioni falliscono
                         error_list.append((bundle_code, product_code, 'NL/FR processing failed'))
                         continue # Non registrare il bundle se nessuna immagine è stata salvata

                else: # Immagine singola trovata (standard o fallback specifico)
                    # Controlla se l'estensione usata è cross-country
                    if used_ext in ["1-fr", "1-de", "1-nl"]:
                        bundle_cross_country = True
                        output_folder = cross_country_folder # Salva in cartella cross-country
                        suffix = f"-p{used_ext}.jpg"
                    else:
                        # Se non è cross-country, usa la cartella bundle_N
                        os.makedirs(output_folder, exist_ok=True)
                        suffix = "-h1.jpg" # Suffisso standard

                    try:
                        processed_image_buffer = await asyncio.to_thread(process_image_bundle, result, num_products, layout) # result sono i bytes
                        save_path = os.path.join(output_folder, f"{bundle_code}{suffix}")
                        await asyncio.to_thread(save_binary_file, save_path, processed_image_buffer.read())
                    except (ValueError, RuntimeError, Exception) as e:
                         error_list.append((bundle_code, f"{product_code} ({used_ext})", f'Processing error: {e}'))
                         continue # Non registrare il bundle se l'immagine non è stata salvata

            else: # Mixed set
                output_folder = os.path.join(mixed_folder, bundle_code) # Cartella specifica per il set misto
                os.makedirs(output_folder, exist_ok=True)
                # Potrebbe contenere una sottocartella "cross-country" se necessario
                mixed_set_saved_at_least_one = False

                for p_code in unique_product_codes: # Processa ogni PZN unico nel set
                    result, used_ext = await async_get_image_with_fallback(p_code, session)

                    if result is None:
                        error_list.append((bundle_code, p_code, 'Image not found for mixed set'))
                        continue # Prova il prossimo PZN nel set

                    if used_ext == "NL FR":
                         bundle_cross_country = True # Segna tutto il bundle come cross-country
                         mixed_cross_folder = os.path.join(output_folder, "cross-country")
                         os.makedirs(mixed_cross_folder, exist_ok=True)
                         for lang, image_data in result.items():
                            suffix = "-p1-fr.jpg" if lang == "1-fr" else "-p1-nl.jpg"
                            save_path = os.path.join(mixed_cross_folder, f"{p_code}{suffix}")
                            # Nota: Non riprocessiamo/ridimensioniamo le immagini dei set misti
                            if await asyncio.to_thread(save_binary_file, save_path, image_data):
                                mixed_set_saved_at_least_one = True

                    else: # Immagine singola per set misto
                        if used_ext in ["1-fr", "1-de", "1-nl"]:
                             bundle_cross_country = True
                             current_save_folder = os.path.join(output_folder, "cross-country")
                             os.makedirs(current_save_folder, exist_ok=True)
                             suffix = f"-p{used_ext}.jpg"
                        else:
                             current_save_folder = output_folder # Salva nella cartella principale del set misto
                             suffix = f"-p{used_ext}.jpg" # Usa l'estensione trovata (es. -p1.jpg, -p10.jpg)

                        save_path = os.path.join(current_save_folder, f"{p_code}{suffix}")
                        # Nota: Non riprocessiamo/ridimensioniamo le immagini dei set misti
                        if await asyncio.to_thread(save_binary_file, save_path, result):
                           mixed_set_saved_at_least_one = True

                if not mixed_set_saved_at_least_one:
                    st.warning(f"No images could be saved for mixed set {bundle_code}.")
                    # Potresti voler rimuovere la cartella vuota del set misto qui
                    try: shutil.rmtree(output_folder)
                    except Exception: pass
                    continue # Non registrare il bundle se nessuna immagine è stata salvata

            # Se siamo arrivati qui, almeno un'immagine è stata processata/salvata per il bundle
            processed_bundles_count += 1
            bundle_list.append([
                bundle_code,
                ', '.join(product_codes), # Lista originale dei PZN (con duplicati se c'erano)
                bundle_type,
                "Yes" if bundle_cross_country else "No"
            ])

    if progress_bar: progress_bar.empty() # Rimuovi barra alla fine
    st.info(f"Finished processing. Successfully processed {processed_bundles_count} out of {total} bundles.")

    # --- Gestione Output CSV e ZIP ---
    missing_images_data = None
    missing_images_df = pd.DataFrame() # Inizializza vuoto
    if error_list:
        missing_images_df = pd.DataFrame(error_list, columns=["Bundle SKU", "Product PZN", "Reason"])
        # Aggrega ragioni per PZN, poi per Bundle
        missing_agg = missing_images_df.groupby(["Bundle SKU", "Product PZN"])['Reason'].apply(lambda x: '; '.join(sorted(list(set(x))))).reset_index()
        missing_final_agg = missing_agg.groupby("Bundle SKU").agg(
             Missing_Details= ('Product PZN', lambda x: ', '.join(sorted(list(set(x))))),
             Reasons = ('Reason', lambda x: ' | '.join(sorted(list(set(x))))) # Concatena ragioni diverse
        ).reset_index()
        missing_images_df = missing_final_agg # Sovrascrivi con il df aggregato finale

        try:
            missing_images_df.to_csv(missing_images_csv_path, index=False, sep=';', encoding='utf-8-sig') # Usa utf-8-sig per Excel
            with open(missing_images_csv_path, "rb") as f_csv:
                missing_images_data = f_csv.read()
        except Exception as e:
            st.error(f"Error saving missing images CSV: {e}")
            missing_images_df = pd.DataFrame() # Resetta se errore
    # else: # missing_images_df resta vuoto se error_list era vuota

    bundle_list_data = None
    bundle_list_df = pd.DataFrame() # Inizializza vuoto
    if bundle_list:
        bundle_list_df = pd.DataFrame(bundle_list, columns=["Bundle SKU", "PZNs in Set", "Bundle Type", "Cross-Country"])
        try:
            bundle_list_df.to_csv(bundle_list_csv_path, index=False, sep=';', encoding='utf-8-sig')
            with open(bundle_list_csv_path, "rb") as f_csv:
                bundle_list_data = f_csv.read()
        except Exception as e:
             st.error(f"Error saving bundle list CSV: {e}")
             bundle_list_df = pd.DataFrame() # Resetta se errore
    # else: # bundle_list_df resta vuoto se bundle_list era vuota

    # Creazione del file ZIP
    zip_bytes = None
    zip_path = f"BundleSetImages_{session_id}.zip" # Nome file download
    if os.path.exists(base_folder) and any(os.scandir(base_folder)): # Controlla se la cartella non è vuota
        # Crea archivio direttamente dalla cartella base
        temp_zip_name = f"temp_bundle_zip_{session_id}"
        try:
            shutil.make_archive(temp_zip_name, 'zip', base_folder)
            # Rinomina l'archivio creato
            final_zip_path = f"{temp_zip_name}.zip"
            if os.path.exists(final_zip_path):
                 os.rename(final_zip_path, zip_path)
                 with open(zip_path, "rb") as zip_file:
                     zip_bytes = zip_file.read()
                 # Pulisci zip originale temporaneo se esiste ancora (dopo rename potrebbe non esserci)
                 # if os.path.exists(final_zip_path): os.remove(final_zip_path) # Già rinominato
            else:
                 st.error("Failed to create the final ZIP archive.")

        except Exception as e:
            st.error(f"Error creating ZIP file: {e}")
            # Pulisci eventuali file temporanei
            if os.path.exists(f"{temp_zip_name}.zip"): os.remove(f"{temp_zip_name}.zip")

    else:
        st.warning("Output folder is empty or does not exist. No ZIP file created.")
        if os.path.exists(zip_path): os.remove(zip_path) # Rimuovi zip vecchio/vuoto

    # Ritorna i dati (bytes o None) e i DataFrame per visualizzazione
    return zip_bytes, missing_images_data, missing_images_df, bundle_list_data, bundle_list_df

# ---------------------- End of Function Definitions ----------------------

# Main UI
st.title("📦 PDM Bundle Image Creator")

st.markdown(
    """
    **How to use:**

    1.  Prepare a CSV file using **semicolon (`;`)** as delimiter and **UTF-8** encoding.
    2.  The CSV must contain columns named `sku` (for the bundle/set PZN) and `pzns_in_set` (comma-separated list of PZN included). Column names are case-insensitive.
    3.  Choose **language/country specific photo handling** (e.g., 'NL FR', 'FR', 'DE', or 'None').
    4.  Choose **layout** for bundles of 2 or 3 identical items ('Automatic', 'Horizontal', 'Vertical').
    5.  Upload your CSV file.
    6.  Click **Process CSV** to start.
    7.  Download the results: ZIP file with images, CSV of processed bundles, CSV of missing/failed images.
    8.  Click **Clear Cache and Reset Data** before starting a new batch.
    """
)

# Reset Button
if st.button("🧹 Clear Cache and Reset Data"):
    # Chiavi specifiche di questa app da resettare
    keys_to_remove = [
        "bundle_fallback_ext", "bundle_encryption_key",
        "bundle_zip_data", "bundle_bundle_list_data", "bundle_missing_images_data",
        "bundle_missing_df", "bundle_list_df", "bundle_processing_complete",
        "file_uploader" # Resetta anche lo stato dell'uploader
        ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]

    # Pulisce cache dati e risorse di Streamlit
    st.cache_data.clear()
    st.cache_resource.clear()

    # Chiama la funzione di pulizia file con l'ID di sessione corrente
    clear_old_data()
    st.success("Session data and temporary files cleared.")
    st.rerun()


# Sidebar Content
st.sidebar.header("App Details")
st.sidebar.markdown(
    """
    - **Function:** Creates bundle/set images from individual product images.
    - **Input:** CSV file (`;` delimited) with `sku` and `pzns_in_set` columns.
    - **Image Source:** `cdn.shop-apotheke.com`
    - **Processing (Uniform Bundles of 2/3):**
        - Downloads base image.
        - Trims whitespace.
        - Combines images based on selected layout.
        - Resizes to fit 1000x1000.
        - Places on a white 1000x1000 canvas.
        - Saves as JPEG (Quality 100).
    - **Processing (Mixed Sets):**
        - Downloads individual PZN images.
        - Saves original images (no processing/resizing).
    - **Naming:**
        - Uniform bundles: `{bundle_sku}-{suffix}.jpg` (e.g., `-h1.jpg`, `-p1-fr.jpg`).
        - Mixed set items: `{pzn}-{suffix}.jpg`.
    - **Output:** ZIP file with organized folders (`bundle_2`, `bundle_3`, `cross-country`, `mixed_sets`), plus CSV reports.
    """, unsafe_allow_html=True
)

st.sidebar.header("Individual Image Preview")
product_code_preview = st.sidebar.text_input("Enter Product Code (PZN):", key="preview_pzn")
# Metti un range più ampio se necessario, o una lista specifica
preview_extensions = ["1", "10"] + [f"1-{lang}" for lang in ["fr", "de", "nl"]]
selected_extension_preview = st.sidebar.selectbox(
    "Select Image Extension:",
     preview_extensions,
     index=0,
     key="preview_ext",
     help="Select the image suffix to preview (e.g., -p1.jpg, -p1-fr.jpg)"
     )

if st.sidebar.button("Show Preview", key="preview_button"):
    if product_code_preview:
        with st.sidebar:
            with st.spinner("Loading preview..."):
                # Usa la stessa logica di download asincrono
                async def fetch_preview():
                    async with aiohttp.ClientSession() as session:
                        # Non usare fallback qui, solo l'estensione selezionata
                        content, url = await async_download_image(product_code_preview, selected_extension_preview, session)
                        return content, url

                image_data_preview, preview_url = asyncio.run(fetch_preview())

                if image_data_preview:
                    try:
                        image_preview = Image.open(BytesIO(image_data_preview))
                        st.image(image_preview, caption=f"Preview: {product_code_preview} (-p{selected_extension_preview})", use_container_width=True)
                        st.download_button(
                            label="Download Preview",
                            data=image_data_preview,
                            file_name=f"{product_code_preview}-p{selected_extension_preview}.jpg",
                            mime="image/jpeg",
                            key="download_preview"
                        )
                    except Exception as e:
                         st.error(f"Could not display image. Error: {e}")
                else:
                    st.error(f"No image found for PZN {product_code_preview} with extension -p{selected_extension_preview}.")
                    st.caption(f"Attempted URL: {preview_url}")
    else:
        st.sidebar.warning("Please enter a Product Code (PZN) to preview.")


# --- Main Area for Upload and Processing ---
uploaded_file = st.file_uploader(
    "**Upload CSV File (semicolon delimited, UTF-8)**",
    type=["csv"],
    key="file_uploader",
    help="Ensure the file has 'sku' and 'pzns_in_set' columns."
    )

if uploaded_file:
    col1, col2 = st.columns(2)
    with col1:
        fallback_language = st.selectbox(
            "**Language/Country Handling:**",
            options=["None", "NL FR", "FR", "DE"],
            index=0,
            key="fallback_select",
            help="Choose how to handle language-specific images ('NL FR' is special)."
            )
    with col2:
        layout_choice = st.selectbox(
            "**Layout (Bundles of 2/3):**",
            options=["Automatic", "Horizontal", "Vertical"],
            index=0,
            key="layout_select",
            help="Arrangement for combined images in uniform bundles."
            )

    # Imposta lo stato della sessione per fallback
    # Usa una chiave specifica per questa app per evitare conflitti
    if fallback_language == "NL FR":
        st.session_state["bundle_fallback_ext"] = "NL FR"
    elif fallback_language == "FR":
        st.session_state["bundle_fallback_ext"] = "1-fr"
    elif fallback_language == "DE":
        st.session_state["bundle_fallback_ext"] = "1-de"
    else: # "None"
        st.session_state["bundle_fallback_ext"] = None

    if st.button("Process CSV"):
        start_time = time.time()
        progress_bar = st.progress(0, text="Starting processing...")
        try:
             zip_data, missing_data, missing_df, bundle_data, bundle_df = asyncio.run(
                 process_file_async(uploaded_file, progress_bar, layout=layout_choice.lower())
             )
             elapsed_time = time.time() - start_time
             minutes = int(elapsed_time // 60)
             seconds = int(elapsed_time % 60)
             st.info(f"Processing finished in {minutes}m {seconds}s.")

             # Salva risultati nello stato della sessione con nomi univoci
             st.session_state["bundle_zip_data"] = zip_data
             st.session_state["bundle_bundle_list_data"] = bundle_data
             st.session_state["bundle_missing_images_data"] = missing_data
             st.session_state["bundle_missing_df"] = missing_df # Per display
             st.session_state["bundle_list_df"] = bundle_df # Per display
             st.session_state["bundle_processing_complete"] = True

        except Exception as e:
             st.error(f"An unexpected error occurred during processing: {e}")
             st.exception(e)
             st.session_state["bundle_processing_complete"] = False
             # Pulisci stato parziale in caso di errore critico
             keys_to_clear_on_error = ["bundle_zip_data", "bundle_bundle_list_data", "bundle_missing_images_data", "bundle_missing_df", "bundle_list_df"]
             for key in keys_to_clear_on_error:
                 if key in st.session_state: del st.session_state[key]


# --- Sezione Risultati e Download ---
if st.session_state.get("bundle_processing_complete", False):
    st.markdown("---")
    st.header("Processing Results")

    tab1, tab2, tab3 = st.tabs(["Downloads", "Processed Bundles", "Missing/Failed Images"])

    with tab1:
        st.subheader("Download Files")
        dl_col1, dl_col2, dl_col3 = st.columns(3)
        with dl_col1:
            if st.session_state.get("bundle_zip_data"):
                st.download_button(
                    label="Download Images (ZIP)",
                    data=st.session_state["bundle_zip_data"],
                    file_name=f"BundleSetImages_{session_id}.zip",
                    mime="application/zip",
                    key="dl_zip"
                )
            else:
                st.info("No ZIP file generated (likely no images processed).")
        with dl_col2:
            if st.session_state.get("bundle_bundle_list_data"):
                st.download_button(
                    label="Download Bundle List (CSV)",
                    data=st.session_state["bundle_bundle_list_data"],
                    file_name=f"bundle_list_{session_id}.csv",
                    mime="text/csv",
                    key="dl_bundle_list"
                )
            else:
                st.info("No bundle list generated.")
        with dl_col3:
            if st.session_state.get("bundle_missing_images_data"):
                st.download_button(
                    label="Download Missing/Failed (CSV)",
                    data=st.session_state["bundle_missing_images_data"],
                    file_name=f"missing_images_{session_id}.csv",
                    mime="text/csv",
                    key="dl_missing"
                )
            else:
                st.info("No missing/failed images reported.")

    with tab2:
        st.subheader("Processed Bundles Summary")
        processed_df = st.session_state.get("bundle_list_df")
        if processed_df is not None and not processed_df.empty:
             st.dataframe(processed_df, use_container_width=True)
        elif processed_df is not None:
             st.info("No bundles were successfully processed.")
        else:
             st.warning("Processed bundle list not available.")

    with tab3:
        st.subheader("Missing Images / Processing Errors")
        missing_display_df = st.session_state.get("bundle_missing_df")
        if missing_display_df is not None and not missing_display_df.empty:
             st.warning(f"Found {len(missing_display_df)} bundles with missing images or errors:")
             st.dataframe(missing_display_df, use_container_width=True)
        elif missing_display_df is not None:
             st.success("🎉 No missing images or processing errors reported!")
        else:
             st.info("Missing images report is not available.") # Potrebbe essere che non ci fossero errori o che il report non sia stato generato
