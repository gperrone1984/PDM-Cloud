import streamlit as st
import streamlit.components.v1 as components
import os
import aiohttp
import asyncio
import pandas as pd
import shutil
import uuid
import time
import random
from io import BytesIO
from PIL import Image, ImageChops, ImageFile
from cryptography.fernet import Fernet
from aiohttp import ClientTimeout

# =========================================
# Page configuration (MUST be the first op)
# =========================================
st.set_page_config(
    page_title="Bundle Creator",
    page_icon="📦",
    layout="centered"
)

# ======================
# Authentication check
# ======================
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# ======================
# Global PIL settings
# ======================
ImageFile.LOAD_TRUNCATED_IMAGES = True

# ======================
# --- Global CSS ---
# ======================
st.markdown(
    """
    <style>
  /* Sidebar: grigio pieno, altezza schermo, larghezza fissa */
  aside[data-testid="stSidebar"] {
    background-color: #f2f3f5 !important;
    width: 540px !important;
    min-width: 540px !important;
    max-width: 540px !important;
    height: 100vh !important;
    position: sticky !important;
    top: 0 !important;
    overflow-y: auto !important;
    border-right: 1px solid rgba(0,0,0,0.06);
    transition: all 0.5s ease-in-out !important;
    z-index: 9999 !important;
  }

  [data-testid="stSidebar"] > div:first-child {
    background-color: #f2f3f5 !important;
    height: 100vh !important;
    overflow-y: auto !important;
    position: sticky !important;
    top: 0 !important;
  }

  [data-testid="stSidebar"] .block-container {
    background: transparent !important;
  }

  [data-testid="stSidebarNav"] { display: none !important; }

  div[data-testid="stAppViewContainer"] > section > div.block-container,
  .main .block-container {
       background-color: transparent !important;
       padding: 2rem 1rem 1rem 1rem !important;
       border-radius: 0.5rem !important;
  }

  .app-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 1.5rem; }
  .app-button-link, .app-button-placeholder {
      display: flex; align-items: center; justify-content: center;
      padding: 1.2rem 1.5rem; border-radius: 0.5rem; text-decoration: none;
      font-weight: bold; font-size: 1.05rem; width: 90%; min-height: 100px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.04); margin-bottom: 0.75rem; text-align: center;
      line-height: 1.4; transition: background-color 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
      border: 1px solid var(--border-color, #cccccc);
  }
  .app-button-link:hover { box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
  .app-button-placeholder { opacity: 0.7; cursor: default; box-shadow: none; border-style: dashed; }
  .app-description { font-size: 0.9em; padding: 0 15px; text-align: justify; width: 90%; margin: 0 auto; }

  /* =============== Sidebar Hide / Show Styles =============== */
  aside[data-testid="stSidebar"].sidebar-closed {
      margin-left: -600px !important;
      transform: translateX(-100%) !important;
      opacity: 0 !important;
      visibility: hidden !important;
      width: 0 !important; min-width: 0 !important; max-width: 0 !important;
      padding: 0 !important; border: none !important; box-shadow: none !important;
  }
  .hidden-toggle { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Button to go back to the Hub in the Sidebar ---
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")  # Separator

# --- Script: Chiudi completamente la sidebar ---
st.markdown("""
<script>
const wait = setInterval(() => {
  const sidebar = window.parent.document.querySelector('aside[data-testid="stSidebar"]');
  const toggleBtn = window.parent.document.querySelector('[data-testid="collapsedControl"]');
  if (sidebar && toggleBtn) {
    clearInterval(wait);
    toggleBtn.addEventListener("click", () => {
      if (!sidebar.classList.contains("sidebar-closed")) {
        sidebar.classList.add("sidebar-closed");
        toggleBtn.classList.add("hidden-toggle");
      } else {
        sidebar.classList.remove("sidebar-closed");
        setTimeout(() => { toggleBtn.classList.remove("hidden-toggle"); }, 400);
      }
    });
  }
}, 500);
</script>
""", unsafe_allow_html=True)

# ---------------------- Session State Management ----------------------
if "bundle_creator_session_id" not in st.session_state:
    st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())

session_id = st.session_state["bundle_creator_session_id"]
base_folder = f"Bundle&Set_{session_id}"

# ---------------------- Helpers for cleanup ----------------------
def clear_old_data():
    if os.path.exists(base_folder):
        shutil.rmtree(base_folder)
    # possibili nomi zip
    for name in [f"BundleSet_{session_id}.zip", f"Bundle&Set_{session_id}.zip", f"Bundle&Set_archive_{session_id}.zip"]:
        if os.path.exists(name):
            os.remove(name)
    for path in [f"missing_images_{session_id}.xlsx", f"bundle_list_{session_id}.xlsx"]:
        if os.path.exists(path):
            os.remove(path)

#-------------- Quality image-----------------------------------
JPEG_QUALITY = 75

# ======================
# Networking & Imaging
# ======================
async def async_download_image(product_code, extension, session, retries=3, base_backoff=0.5):
    """
    Scarica l'immagine da CDN con retry/backoff.
    Non riprova sui 404.
    """
    if product_code.startswith(('1', '0')):
        product_code = f"D{product_code}"
    url = f"https://cdn.shop-apotheke.com/images/{product_code}-p{extension}.jpg"

    for attempt in range(retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read(), url
                elif response.status == 404:
                    return None, None
        except Exception:
            pass
        await asyncio.sleep(base_backoff * (2 ** attempt) + random.random() * 0.2)

    return None, None

def trim(im: Image.Image) -> Image.Image:
    bg = Image.new(im.mode, im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

def _center_into_square(im: Image.Image, target=1000) -> Image.Image:
    # Mantiene proporzioni e centra in 1000x1000 con sfondo bianco
    w, h = im.size
    if w == 0 or h == 0:
        return Image.new("RGB", (target, target), (255, 255, 255))
    scale = min(target / w, target / h)
    new_size = (int(w * scale), int(h * scale))
    resized = im.resize(new_size, Image.LANCZOS)
    final_img = Image.new("RGB", (target, target), (255, 255, 255))
    x_off = (target - new_size[0]) // 2
    y_off = (target - new_size[1]) // 2
    final_img.paste(resized, (x_off, y_off))
    return final_img

def process_double_bundle_image(image: Image.Image, layout="horizontal") -> Image.Image:
    image = trim(image)
    width, height = image.size
    chosen_layout = "vertical" if (layout.lower() == "automatic" and height < width) else layout.lower()
    if chosen_layout == "horizontal":
        merged = Image.new("RGB", (width * 2, height), (255, 255, 255))
        merged.paste(image, (0, 0)); merged.paste(image, (width, 0))
    elif chosen_layout == "vertical":
        merged = Image.new("RGB", (width, height * 2), (255, 255, 255))
        merged.paste(image, (0, 0)); merged.paste(image, (0, height))
    else:
        merged = Image.new("RGB", (width * 2, height), (255, 255, 255))
        merged.paste(image, (0, 0)); merged.paste(image, (width, 0))
    return _center_into_square(merged, 1000)

def process_triple_bundle_image(image: Image.Image, layout="horizontal") -> Image.Image:
    image = trim(image)
    width, height = image.size
    chosen_layout = "vertical" if (layout.lower() == "automatic" and height < width) else layout.lower()
    if chosen_layout == "horizontal":
        merged = Image.new("RGB", (width * 3, height), (255, 255, 255))
        merged.paste(image, (0, 0)); merged.paste(image, (width, 0)); merged.paste(image, (width * 2, 0))
    elif chosen_layout == "vertical":
        merged = Image.new("RGB", (width, height * 3), (255, 255, 255))
        merged.paste(image, (0, 0)); merged.paste(image, (0, height)); merged.paste(image, (0, height * 2))
    else:
        merged = Image.new("RGB", (width * 3, height), (255, 255, 255))
        merged.paste(image, (0, 0)); merged.paste(image, (width, 0)); merged.paste(image, (width * 2, 0))
    return _center_into_square(merged, 1000)

def process_and_save_trimmed_image(image_bytes: bytes, dest_path: str):
    """
    Trimma i bordi bianchi e salva come JPEG ottimizzato.
    """
    with Image.open(BytesIO(image_bytes)) as img:
        img = trim(img).convert("RGB")
        img.save(dest_path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)

async def async_get_nl_fr_images(product_code: str, session):
    tasks = [
        async_download_image(product_code, "1-fr", session),
        async_download_image(product_code, "1-nl", session)
    ]
    results = await asyncio.gather(*tasks)
    images = {}
    if results[0][0]:
        images["1-fr"] = results[0][0]
    if results[1][0]:
        images["1-nl"] = results[1][0]
    return images

async def async_get_image_with_fallback(product_code: str, session):
    """
    Ordine:
    - se fallback=NL FR: prova a prendere entrambe (1-fr, 1-nl)
    - altrimenti: prova p1, poi p10
    - in coda: fallback esplicito (1-fr/1-de/1-nl) se selezionato
    """
    fallback_ext = st.session_state.get("fallback_ext", None)

    if fallback_ext == "NL FR":
        images_dict = await async_get_nl_fr_images(product_code, session)
        if images_dict:
            return images_dict, "NL FR"

    # p1 / p10
    for ext in ["1", "10"]:
        content, _ = await async_download_image(product_code, ext, session)
        if content:
            return content, ext

    # fallback singolo linguistico
    if fallback_ext and fallback_ext != "NL FR":
        content, _ = await async_download_image(product_code, fallback_ext, session)
        if content:
            return content, fallback_ext

    return None, None

def create_zip_on_disk(base_folder_path: str, session_id: str) -> str:
    """
    Crea lo ZIP direttamente dalla cartella base, senza copie intermedie.
    Ritorna il percorso completo dello zip.
    """
    zip_base_name = f"BundleSet_{session_id}"  # senza estensione
    # make_archive restituisce il path completo con estensione
    zip_path = shutil.make_archive(
        base_name=zip_base_name,
        format='zip',
        root_dir=os.path.dirname(base_folder_path) or ".",
        base_dir=os.path.basename(base_folder_path)
    )
    return zip_path

# ===========================
# Main Processing (Batched)
# ===========================
async def process_file_async(
    uploaded_file,
    progress_bar=None,
    layout="horizontal",
    start_row=0,
    max_rows=None,
    zip_after=False,
    concurrency=32
):
    """
    Esegue il processamento del batch corrente.
    - Legge il file (CSV/XLSX), ne prende solo la finestra [start_row : start_row+max_rows]
    - Scarica/processa immagini (con dedup su disco)
    - Salva report su disco
    - Facoltativamente crea lo ZIP a fine batch
    """
    session_id = st.session_state["bundle_creator_session_id"]
    base_folder = f"Bundle&Set_{session_id}"
    missing_images_excel_path = f"missing_images_{session_id}.xlsx"
    bundle_list_excel_path = f"bundle_list_{session_id}.xlsx"

    # Chiave crittografia per buffering sicuro in memoria
    if "encryption_key" not in st.session_state:
        st.session_state["encryption_key"] = Fernet.generate_key()
    key = st.session_state["encryption_key"]
    fernet = Fernet(key)

    # Leggi il file in memoria, cifra/decifra (come già facevi)
    file_bytes = uploaded_file.read()
    encrypted_bytes = fernet.encrypt(file_bytes)
    decrypted_bytes = fernet.decrypt(encrypted_bytes)
    file_buffer = BytesIO(decrypted_bytes)

    # Parsing
    try:
        if uploaded_file.name.lower().endswith('.xlsx'):
            data = pd.read_excel(file_buffer, dtype=str)
        else:
            data = pd.read_csv(file_buffer, delimiter=';', dtype=str)
    except pd.errors.EmptyDataError:
        st.error("Il file caricato è vuoto o non leggibile.")
        return None, None, None
    except Exception as e:
        st.error(f"Errore lettura file: {e}")
        return None, None, None

    required_columns = {'sku', 'pzns_in_set'}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        st.error(f"Mancano colonne obbligatorie: {', '.join(missing_columns)}")
        return None, None, None

    data.dropna(subset=['sku', 'pzns_in_set'], inplace=True)
    if data.empty:
        st.error("File vuoto o senza righe valide dopo la pulizia.")
        return None, None, None

    # Applica batch window
    end_row = (start_row + max_rows) if max_rows else None
    data = data.iloc[start_row:end_row].copy()
    total = len(data)
    if total == 0:
        st.warning("Batch vuoto: controlla Start row e Rows per batch.")
        return None, None, None

    st.write(f"File caricato: {len(data)} bundle nel batch corrente.")
    os.makedirs(base_folder, exist_ok=True)

    mixed_sets_needed = False
    mixed_folder = os.path.join(base_folder, "mixed_sets")
    error_list = []
    bundle_list = []

    # AIOHTTP Session con timeout e concorrenza
    connector = aiohttp.TCPConnector(limit=int(concurrency))
    timeout = ClientTimeout(total=30, connect=10)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for i, (_, row) in enumerate(data.iterrows()):
            bundle_code = str(row['sku']).strip()
            pzns_in_set_str = str(row['pzns_in_set']).strip()
            product_codes = [code.strip() for code in pzns_in_set_str.split(',') if code.strip()]

            if not product_codes:
                st.warning(f"Salto bundle {bundle_code}: nessun PZN valido.")
                error_list.append((bundle_code, "Nessun PZN valido"))
                continue

            num_products = len(product_codes)
            is_uniform = (len(set(product_codes)) == 1)
            bundle_type = f"bundle of {num_products}" if is_uniform else "mixed"
            bundle_cross_country = False

            # --------- UNIFORM BUNDLE ---------
            if is_uniform:
                product_code = product_codes[0]
                folder_name_base = f"bundle_{num_products}"
                if st.session_state.get("fallback_ext") in ["NL FR", "1-fr", "1-de", "1-nl"]:
                    folder_name_base = "cross-country"
                folder_name = os.path.join(base_folder, folder_name_base)
                os.makedirs(folder_name, exist_ok=True)

                # Dedup su disco (pre-check): se fallback = "NL FR" e num_products in [2,3] -> produrremo -nl-h1 e -fr-h1
                if st.session_state.get("fallback_ext") == "NL FR":
                    expected_paths = [
                        os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg"),
                        os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg"),
                    ]
                    if all(os.path.exists(p) for p in expected_paths):
                        # già presenti -> salta
                        bundle_cross_country = True
                        bundle_list.append([bundle_code, ', '.join(product_codes), bundle_type, "Yes"])
                        if progress_bar is not None:
                            progress_bar.progress((i + 1) / total, text=f"{bundle_code} (skip: già presenti)")
                        continue

                result, used_ext = await async_get_image_with_fallback(product_code, session)

                # NL/FR dictionary
                if used_ext == "NL FR" and isinstance(result, dict):
                    bundle_cross_country = True
                    folder_name = os.path.join(base_folder, "cross-country")
                    os.makedirs(folder_name, exist_ok=True)
                    processed_lang = False
                    processed_keys = []

                    for lang, image_data in result.items():
                        if lang == "1-fr":
                            suffix = "-fr-h1"
                        elif lang == "1-nl":
                            suffix = "-nl-h1"
                        else:
                            suffix = f"-p{lang}"
                        save_path = os.path.join(folder_name, f"{bundle_code}{suffix}.jpg")

                        # Dedup: se esiste, salta
                        if os.path.exists(save_path):
                            processed_lang = True
                            processed_keys.append(lang)
                            continue

                        try:
                            img = Image.open(BytesIO(image_data))
                            if num_products == 2:
                                final_img = process_double_bundle_image(img, layout)
                            elif num_products == 3:
                                final_img = process_triple_bundle_image(img, layout)
                            else:
                                final_img = _center_into_square(trim(img), 1000)
                            final_img.save(save_path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
                            processed_lang = True
                            processed_keys.append(lang)
                        except Exception as e:
                            st.warning(f"Errore processing {lang} per bundle {bundle_code} (PZN: {product_code}): {e}")
                            error_list.append((bundle_code, f"{product_code} ({lang} processing error)"))

                    # Duplica lingua mancante se solo una disponibile
                    try:
                        if processed_lang:
                            if "1-fr" not in processed_keys and "1-nl" in processed_keys:
                                src = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                                dst = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                                if os.path.exists(src) and not os.path.exists(dst):
                                    shutil.copyfile(src, dst)
                            elif "1-nl" not in processed_keys and "1-fr" in processed_keys:
                                src = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                                dst = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                                if os.path.exists(src) and not os.path.exists(dst):
                                    shutil.copyfile(src, dst)
                        else:
                            error_list.append((bundle_code, f"{product_code} (NL/FR trovate ma fallita elaborazione)"))
                    except Exception as e:
                        st.warning(f"Errore duplicazione lingua per bundle {bundle_code}: {e}")
                        error_list.append((bundle_code, f"{product_code} (dup lingua error)"))

                # Fallback singolo o p1/p10
                elif result:
                    if used_ext in ["1-fr", "1-de", "1-nl"]:
                        bundle_cross_country = True
                        folder_name = os.path.join(base_folder, "cross-country")
                        os.makedirs(folder_name, exist_ok=True)

                    try:
                        img = Image.open(BytesIO(result))
                        if num_products == 2:
                            final_img = process_double_bundle_image(img, layout)
                        elif num_products == 3:
                            final_img = process_triple_bundle_image(img, layout)
                        else:
                            final_img = _center_into_square(trim(img), 1000)

                        if st.session_state.get("fallback_ext") == "NL FR":
                            save_path_nl = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                            save_path_fr = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                            # Dedup
                            if not os.path.exists(save_path_nl):
                                final_img.save(save_path_nl, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
                            if not os.path.exists(save_path_fr):
                                final_img.save(save_path_fr, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
                        else:
                            save_path = os.path.join(folder_name, f"{bundle_code}-h1.jpg")
                            if not os.path.exists(save_path):
                                final_img.save(save_path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
                    except Exception as e:
                        st.warning(f"Errore processing per bundle {bundle_code} (PZN: {product_code}, Ext: {used_ext}): {e}")
                        error_list.append((bundle_code, f"{product_code} (Ext: {used_ext} processing error)"))
                else:
                    # nessuna immagine trovata
                    error_list.append((bundle_code, product_code))

            # --------- MIXED SET ---------
            else:
                mixed_sets_needed = True
                bundle_folder = os.path.join(mixed_folder, bundle_code)
                os.makedirs(bundle_folder, exist_ok=True)
                item_is_cross_country = False

                for p_code in product_codes:
                    # Pre-dedup: se fallback NL FR, controlleremo due file destinazione
                    if st.session_state.get("fallback_ext") == "NL FR":
                        prod_folder = os.path.join(bundle_folder, "cross-country")
                        os.makedirs(prod_folder, exist_ok=True)
                        paths = [
                            os.path.join(prod_folder, f"{p_code}-nl-h1.jpg"),
                            os.path.join(prod_folder, f"{p_code}-fr-h1.jpg"),
                        ]
                        if all(os.path.exists(p) for p in paths):
                            item_is_cross_country = True
                            continue

                    result, used_ext = await async_get_image_with_fallback(p_code, session)

                    if used_ext == "NL FR" and isinstance(result, dict):
                        item_is_cross_country = True
                        prod_folder = os.path.join(bundle_folder, "cross-country")
                        os.makedirs(prod_folder, exist_ok=True)
                        processed_keys = []
                        for lang, image_data in result.items():
                            if lang == "1-fr":
                                suffix = "-fr-h1"
                            elif lang == "1-nl":
                                suffix = "-nl-h1"
                            else:
                                suffix = f"-p{lang}"
                            file_path = os.path.join(prod_folder, f"{p_code}{suffix}.jpg")
                            if os.path.exists(file_path):
                                processed_keys.append(lang)
                                continue
                            process_and_save_trimmed_image(image_data, file_path)
                            processed_keys.append(lang)

                        # Duplica lingua mancante
                        if "1-fr" not in processed_keys and "1-nl" in processed_keys:
                            src = os.path.join(prod_folder, f"{p_code}-nl-h1.jpg")
                            dst = os.path.join(prod_folder, f"{p_code}-fr-h1.jpg")
                            if os.path.exists(src) and not os.path.exists(dst):
                                shutil.copyfile(src, dst)
                        elif "1-nl" not in processed_keys and "1-fr" in processed_keys:
                            src = os.path.join(prod_folder, f"{p_code}-fr-h1.jpg")
                            dst = os.path.join(prod_folder, f"{p_code}-nl-h1.jpg")
                            if os.path.exists(src) and not os.path.exists(dst):
                                shutil.copyfile(src, dst)

                    elif result:
                        prod_folder = bundle_folder
                        if used_ext in ["1-fr", "1-de", "1-nl"]:
                            item_is_cross_country = True
                            prod_folder = os.path.join(bundle_folder, "cross-country")
                            os.makedirs(prod_folder, exist_ok=True)

                        if st.session_state.get("fallback_ext") == "NL FR":
                            file_path_nl = os.path.join(prod_folder, f"{p_code}-nl-h1.jpg")
                            file_path_fr = os.path.join(prod_folder, f"{p_code}-fr-h1.jpg")
                            if not os.path.exists(file_path_nl):
                                process_and_save_trimmed_image(result, file_path_nl)
                            if not os.path.exists(file_path_fr):
                                process_and_save_trimmed_image(result, file_path_fr)
                        else:
                            suffix = f"-p{used_ext}" if used_ext else "-h1"
                            file_path = os.path.join(prod_folder, f"{p_code}{suffix}.jpg")
                            if not os.path.exists(file_path):
                                process_and_save_trimmed_image(result, file_path)
                    else:
                        error_list.append((bundle_code, p_code))

                if item_is_cross_country:
                    bundle_cross_country = True

            # Progress
            if progress_bar is not None:
                progress_bar.progress((i + 1) / total, text=f"Elaborazione {bundle_code} ({i+1}/{total})")

            bundle_list.append([bundle_code, ', '.join(product_codes), bundle_type, "Yes" if bundle_cross_country else "No"])

            # cede controllo ogni 200 righe
            if (i + 1) % 200 == 0:
                await asyncio.sleep(0)

    # Rimuovi mixed_folder se creato ma inutilizzato
    if not mixed_sets_needed and os.path.exists(mixed_folder):
        try:
            shutil.rmtree(mixed_folder)
        except Exception as e:
            st.warning(f"Impossibile rimuovere la cartella mixed: {e}")

    # ---- Report su disco ----
    missing_images_path = None
    if error_list:
        missing_images_df = pd.DataFrame(error_list, columns=["PZN Bundle", "PZN with image missing"])
        missing_images_df = missing_images_df.groupby("PZN Bundle", as_index=False).agg({
            "PZN with image missing": lambda x: ', '.join(sorted(list(set(map(str, x)))))
        })
        try:
            missing_images_df.to_excel(missing_images_excel_path, index=False)
            missing_images_path = missing_images_excel_path
            # tieni DF in session per la visualizzazione
            st.session_state["missing_images_df"] = missing_images_df
        except Exception as e:
            st.error(f"Impossibile salvare missing_images Excel: {e}")
    else:
        # se non ci sono errori, svuota eventuale df vecchio
        st.session_state["missing_images_df"] = pd.DataFrame(columns=["PZN Bundle", "PZN with image missing"])

    bundle_list_path = None
    if bundle_list:
        try:
            bundle_list_df = pd.DataFrame(bundle_list, columns=["sku", "pzns_in_set", "bundle type", "cross-country"])
            bundle_list_df.to_excel(bundle_list_excel_path, index=False)
            bundle_list_path = bundle_list_excel_path
        except Exception as e:
            st.error(f"Impossibile salvare bundle_list Excel: {e}")

    # Facoltativo: crea ZIP ora
    created_zip_path = None
    if zip_after:
        # zip solo se ci sono file in base_folder
        if os.path.exists(base_folder) and any(os.scandir(base_folder)):
            try:
                created_zip_path = create_zip_on_disk(base_folder, session_id)
            except Exception as e:
                st.error(f"Errore creazione ZIP: {e}")
        else:
            st.info("Nessun file da zippare in questo batch.")

    return missing_images_path, bundle_list_path, created_zip_path

# =========================
# ========   UI   =========
# =========================
st.title("PDM Bundle&Set Image Creator")

st.markdown(
    """
    **Come usare:**
    1. Crea un **Quick Report** in **Akeneo** con la lista prodotti.
    2. Esporta **CSV o Excel** (Grid Context: includi ID e PZN nel set) – **With Codes** – **Without Media**.
    3. **Lingua foto specifica:** scegli se necessario.
    4. **Layout bundle:** Orizzontale, Verticale o Automatico.
    5. Imposta **Batch** (Start row & Rows per batch) e **Concorrenza**.
    6. Clicca **Process File**.
    7. Alla fine, scarica i file/report. Puoi **creare lo ZIP** a fine batch o on‑demand.
    """
)

# ========== Clear cache ==========
if st.button("🧹 Clear Cache and Reset Data"):
    keys_to_remove = [
        "bundle_creator_session_id", "encryption_key", "fallback_ext",
        "missing_images_df", "processing_complete_bundle",
        "file_uploader", "preview_pzn_bundle", "sidebar_ext_bundle",
        "start_row_bundle", "zip_path", "bundle_list_path", "missing_images_path"
    ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    # svuota cache
    try:
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception:
        pass
    # pulizia disco
    try:
        clear_old_data()
    except Exception as e:
        st.warning(f"Errore durante clear_old_data: {e}")
    st.success("Cache e sessione pulite. Pronto per un nuovo task.")
    if "bundle_creator_session_id" not in st.session_state:
        st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())
    time.sleep(1)
    st.rerun()

# ===== Sidebar: Info =====
st.sidebar.header("What This App Does")
st.sidebar.markdown(
    """
    - ❓ **Automated Bundle&Set Creation**: download, composizione e organizzazione immagini;
    - 🔎 **Language Selection**: NL-FR, DE, FR;
    - 🧩 **Layout doppio/triplo**: Automatic, Horizontal, Vertical;
    - ✏️ **Rinomina** coerente (-h1, -p1-fr, -p1-nl, ...);
    - ❌ **Log errori** in Excel;
    - 📥 **Download** ZIP e report;
    - 🌐 **Preview** e download singolo da sidebar.
    """, unsafe_allow_html=True
)

# ===== Sidebar: Preview =====
st.sidebar.header("Product Image Preview")
product_code_preview = st.sidebar.text_input("Enter Product Code:", key="preview_pzn_bundle")
selected_extension = st.sidebar.selectbox(
    "Select Image Extension: **p**",
    ["1-fr", "1-nl", "1-de", "1"] + [str(i) for i in range(2, 19)],
    key="sidebar_ext_bundle"
)
with st.sidebar:
    col_button, col_spinner = st.columns([2, 1])
    show_image = col_button.button("Show Image", key="show_preview_bundle")
    spinner_placeholder = col_spinner.empty()

if show_image and product_code_preview:
    with spinner_placeholder:
        with st.spinner("Processing..."):
            pzn_url = product_code_preview.strip()
            if pzn_url.startswith(('1', '0')):
                pzn_url = f"D{pzn_url}"
            preview_url = f"https://cdn.shop-apotheke.com/images/{pzn_url}-p{selected_extension}.jpg"
            image_data = None
            try:
                import requests
                response = requests.get(preview_url, stream=True, timeout=10)
                if response.status_code == 200:
                    image_data = response.content
                else:
                    fetch_status_code = response.status_code
            except requests.exceptions.RequestException as e:
                st.sidebar.error(f"Network error: {e}")
                fetch_status_code = None
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
                fetch_status_code = None

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
        except Exception as e:
            st.sidebar.error(f"Could not display preview image: {e}")
    elif 'fetch_status_code' in locals() and fetch_status_code == 404:
        st.sidebar.warning(f"No image found (404) for {product_code_preview} with -p{selected_extension}.jpg")
    elif 'fetch_status_code' in locals() and fetch_status_code is not None:
        st.sidebar.error(f"Failed to fetch image (Status: {fetch_status_code}) for {product_code_preview} with -p{selected_extension}.jpg")

# ===== Sidebar: Batching & Concurrency =====
st.sidebar.header("Batch processing")
batch_size = st.sidebar.number_input(
    "Rows per batch", min_value=100, max_value=2000, value=500, step=50, key="batch_size_bundle"
)
start_row = st.sidebar.number_input(
    "Start row (0-based)", min_value=0, value=int(st.session_state.get("start_row_bundle", 0)), step=batch_size
)
zip_after = st.sidebar.checkbox("Crea ZIP al termine di questo batch", value=False, key="zip_after_bundle")
concurrency = st.sidebar.number_input(
    "Max concurrent downloads", min_value=8, max_value=64, value=32, step=4, help="Valori tipici su Streamlit Community: 24–48."
)

# ====== File uploader & main controls ======
uploaded_file = st.file_uploader("**Upload CSV o XLSX**", type=["csv", "xlsx"], key="file_uploader")
if uploaded_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        fallback_language = st.selectbox("**Lingua foto specifica (opzionale):**", options=["None", "FR", "DE", "NL FR"], index=0, key="lang_select_bundle")
    with col2:
        layout_choice = st.selectbox("**Layout bundle:**", options=["Automatic", "Horizontal", "Vertical"], index=0, key="layout_select_bundle")

    # Imposta fallback in sessione
    if fallback_language == "NL FR":
        st.session_state["fallback_ext"] = "NL FR"
    elif fallback_language != "None":
        st.session_state["fallback_ext"] = f"1-{fallback_language.lower()}"
    else:
        if "fallback_ext" in st.session_state:
            del st.session_state["fallback_ext"]

    if st.button("Process File", key="process_csv_bundle"):
        start_time = time.time()
        progress_bar = st.progress(0, text="Starting processing...")
        st.session_state["processing_complete_bundle"] = False
        try:
            if 'process_file_async' not in globals():
                st.error("Errore critico: funzione di processamento non definita.")
                st.stop()

            missing_images_path, bundle_list_path, created_zip_path = asyncio.run(
                process_file_async(
                    uploaded_file=uploaded_file,
                    progress_bar=progress_bar,
                    layout=layout_choice,
                    start_row=int(start_row),
                    max_rows=int(batch_size),
                    zip_after=bool(zip_after),
                    concurrency=int(concurrency)
                )
            )
            progress_bar.progress(1.0, text="Processing Complete!")
            elapsed_time = time.time() - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            st.success(f"Processing finished in {minutes}m {seconds}s.")

            # Salva percorsi in sessione
            st.session_state["missing_images_path"] = missing_images_path
            st.session_state["bundle_list_path"] = bundle_list_path
            st.session_state["zip_path"] = created_zip_path

            # Aggiorna start row per batch successivo
            st.session_state["start_row_bundle"] = int(start_row) + int(batch_size)

            time.sleep(1.0)
            progress_bar.empty()
            st.session_state["processing_complete_bundle"] = True
        except Exception as e:
            progress_bar.empty()
            st.error(f"Errore durante il processamento: {e}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            st.session_state["processing_complete_bundle"] = False

# ======= Post-processing UI =======
if st.session_state.get("processing_complete_bundle", False):
    st.markdown("---")

    # ZIP creato automaticamente (se zip_after=True)
    if st.session_state.get("zip_path") and os.path.exists(st.session_state["zip_path"]):
        with open(st.session_state["zip_path"], "rb") as fzip:
            st.download_button(
                label="Download Bundle Images (ZIP)",
                data=fzip,
                file_name=os.path.basename(st.session_state["zip_path"]),
                mime="application/zip",
                key="dl_zip_bundle_on_demand_auto"
            )
    else:
        # Se non è stato creato, offri pulsante per creare ZIP ora
        if os.path.exists(base_folder) and any(os.scandir(base_folder)):
            if st.button("📦 Crea ZIP adesso"):
                try:
                    zip_path_now = create_zip_on_disk(base_folder, session_id)
                    st.session_state["zip_path"] = zip_path_now
                    with open(zip_path_now, "rb") as fzip:
                        st.download_button(
                            label="Download Bundle Images (ZIP)",
                            data=fzip,
                            file_name=os.path.basename(zip_path_now),
                            mime="application/zip",
                            key="dl_zip_bundle_on_demand_now"
                        )
                except Exception as e:
                    st.error(f"Errore creazione ZIP: {e}")
        else:
            st.info("Nessun file da zippare al momento.")

    # Bundle list
    if st.session_state.get("bundle_list_path") and os.path.exists(st.session_state["bundle_list_path"]):
        with open(st.session_state["bundle_list_path"], "rb") as f_list:
            st.download_button(
                label="Download Bundle List",
                data=f_list,
                file_name=os.path.basename(st.session_state["bundle_list_path"]),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_list_bundle_v2"
            )
    else:
        st.info("Nessun report bundle list generato per questo batch.")

    # Missing images
    missing_df = st.session_state.get("missing_images_df")
    if missing_df is not None and not missing_df.empty:
        st.markdown("---")
        st.warning(f"{len(missing_df)} bundle con immagini mancanti:")
        st.dataframe(missing_df, use_container_width=True)
        if st.session_state.get("missing_images_path") and os.path.exists(st.session_state["missing_images_path"]):
            with open(st.session_state["missing_images_path"], "rb") as f_missing:
                st.download_button(
                    label="Download Missing List",
                    data=f_missing,
                    file_name=os.path.basename(st.session_state["missing_images_path"]),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_missing_bundle_v2"
                )
    else:
        st.success("Nessuna immagine mancante nel batch.")
