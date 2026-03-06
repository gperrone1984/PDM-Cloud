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
from typing import Optional, Dict
from PIL import Image, ImageChops
from cryptography.fernet import Fernet

# Page configuration (MUST be the first operation)
st.set_page_config(
    page_title="Bundle Creator",
    page_icon="📦",
    layout="centered"
)

# Authentication check
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# --- Global CSS to hide default navigation and set sidebar width ---
st.markdown(
    """
    <style>
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

  [data-testid="stSidebarNav"] {
      display: none !important;
  }

  div[data-testid="stAppViewContainer"] > section > div.block-container {
       background-color: transparent !important;
       padding: 2rem 1rem 1rem 1rem !important;
       border-radius: 0.5rem !important;
  }
  .main .block-container {
       background-color: transparent !important;
       padding: 2rem 1rem 1rem 1rem !important;
       border-radius: 0.5rem !important;
  }

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
      border: 1px solid var(--border-color, #cccccc);
  }
  .app-button-link:hover {
      box-shadow: 0 2px 4px rgba(0,0,0,0.08);
  }
  .app-button-placeholder {
      opacity: 0.7;
      cursor: default;
      box-shadow: none;
      border-style: dashed;
  }
  .app-description {
      font-size: 0.9em;
      padding: 0 15px;
      text-align: justify;
      width: 90%;
      margin: 0 auto;
  }

  aside[data-testid="stSidebar"].sidebar-closed {
      margin-left: -600px !important;
      transform: translateX(-100%) !important;
      opacity: 0 !important;
      visibility: hidden !important;
      width: 0 !important;
      min-width: 0 !important;
      max-width: 0 !important;
      padding: 0 !important;
      border: none !important;
      box-shadow: none !important;
  }
  .hidden-toggle {
      display: none !important;
  }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Button to go back to the Hub in the Sidebar ---
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")

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
      }
      else {
        sidebar.classList.remove("sidebar-closed");
        setTimeout(() => {
          toggleBtn.classList.remove("hidden-toggle");
        }, 400);
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

def clear_old_data():
    if os.path.exists(base_folder):
        shutil.rmtree(base_folder)
    zip_path = f"Bundle&Set_{session_id}.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
    missing_images_excel_path = f"missing_images_{session_id}.xlsx"
    bundle_list_excel_path = f"bundle_list_{session_id}.xlsx"
    if os.path.exists(missing_images_excel_path):
        os.remove(missing_images_excel_path)
    if os.path.exists(bundle_list_excel_path):
        os.remove(bundle_list_excel_path)

# ---------------------- Helper Functions ----------------------
async def async_download_image(product_code: str, extension: str, session: aiohttp.ClientSession):
    if product_code.startswith(('1', '0')):
        product_code = f"D{product_code}"
    url = f"https://cdn.shop-apotheke.com/images/{product_code}-p{extension}.jpg"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                return content, url
            return None, None
    except Exception:
        return None, None

def save_binary_jpg(dest_path: str, image_bytes: bytes):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(image_bytes)

def trim(im: Image.Image) -> Image.Image:
    bg = Image.new(im.mode, im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

# ---------------------- FIXED AUTO LAYOUT (IMPORTANT) ----------------------
def _resolve_layout(layout: str, width: int, height: int) -> str:
    layout_l = (layout or "horizontal").lower()
    if layout_l == "automatic":
        # Choose horizontal for landscape/square, vertical for portrait
        return "horizontal" if width >= height else "vertical"
    if layout_l in ("horizontal", "vertical"):
        return layout_l
    return "horizontal"

def process_double_bundle_image(image: Image.Image, layout: str = "horizontal") -> Image.Image:
    image = trim(image)
    width, height = image.size
    chosen_layout = _resolve_layout(layout, width, height)

    if chosen_layout == "horizontal":
        merged_width, merged_height = width * 2, height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (width, 0))
    else:
        merged_width, merged_height = width, height * 2
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (0, height))

    scale_factor = min(1000 / merged_width, 1000 / merged_height) if merged_width and merged_height else 1
    new_size = (int(merged_width * scale_factor), int(merged_height * scale_factor))
    resized_image = merged_image.resize(new_size, Image.LANCZOS)

    final_image = Image.new("RGB", (1000, 1000), (255, 255, 255))
    x_offset = (1000 - new_size[0]) // 2
    y_offset = (1000 - new_size[1]) // 2
    final_image.paste(resized_image, (x_offset, y_offset))
    return final_image

def process_triple_bundle_image(image: Image.Image, layout: str = "horizontal") -> Image.Image:
    image = trim(image)
    width, height = image.size
    chosen_layout = _resolve_layout(layout, width, height)

    if chosen_layout == "horizontal":
        merged_width, merged_height = width * 3, height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (width, 0))
        merged_image.paste(image, (width * 2, 0))
    else:
        merged_width, merged_height = width, height * 3
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (0, height))
        merged_image.paste(image, (0, height * 2))

    scale_factor = min(1000 / merged_width, 1000 / merged_height) if merged_width and merged_height else 1
    new_size = (int(merged_width * scale_factor), int(merged_height * scale_factor))
    resized_image = merged_image.resize(new_size, Image.LANCZOS)

    final_image = Image.new("RGB", (1000, 1000), (255, 255, 255))
    x_offset = (1000 - new_size[0]) // 2
    y_offset = (1000 - new_size[1]) // 2
    final_image.paste(resized_image, (x_offset, y_offset))
    return final_image
# ------------------------------------------------------------------------

def process_and_save_trimmed_image(image_bytes: bytes, dest_path: str):
    img = Image.open(BytesIO(image_bytes))
    img = trim(img)
    img = img.convert("RGB")
    img.save(dest_path, "JPEG", quality=75)

# ---------- Cross-country folder routing ----------
def get_uniform_folder(base_folder: str, num_products: int, is_cross_country: bool) -> str:
    if is_cross_country:
        return os.path.join(base_folder, "cross-country", f"bundle_{num_products}")
    return os.path.join(base_folder, f"bundle_{num_products}")

def get_mixed_root(base_folder: str, is_cross_country: bool) -> str:
    if is_cross_country:
        return os.path.join(base_folder, "cross-country", "mixed_sets")
    return os.path.join(base_folder, "mixed_sets")

# ---------- Download extra p2..p9 (standard or language-specific) ----------
async def async_download_p2_to_p9(product_code: str, session: aiohttp.ClientSession, lang_suffix: Optional[str] = None) -> Dict[int, bytes]:
    if lang_suffix:
        exts = [f"{i}-{lang_suffix}" for i in range(2, 10)]
    else:
        exts = [str(i) for i in range(2, 10)]

    tasks = [async_download_image(product_code, ext, session) for ext in exts]
    results = await asyncio.gather(*tasks)

    out: Dict[int, bytes] = {}
    for ext, (content, _url) in zip(exts, results):
        if not content:
            continue
        p_num = int(str(ext).split("-")[0])
        out[p_num] = content
    return out

# ---------- NL/FR p1 lookup ----------
async def async_get_nl_fr_images(product_code: str, session: aiohttp.ClientSession) -> Dict[str, bytes]:
    tasks = [
        async_download_image(product_code, "1-fr", session),
        async_download_image(product_code, "1-nl", session)
    ]
    results = await asyncio.gather(*tasks)
    images: Dict[str, bytes] = {}
    if results[0][0]:
        images["1-fr"] = results[0][0]
    if results[1][0]:
        images["1-nl"] = results[1][0]
    return images

async def async_get_image_with_fallback(product_code: str, session: aiohttp.ClientSession):
    fallback_ext = st.session_state.get("fallback_ext", None)

    # NL FR: return dict if at least one exists
    if fallback_ext == "NL FR":
        images_dict = await async_get_nl_fr_images(product_code, session)
        if images_dict:
            return images_dict, "NL FR"

    # default: try p1 then p10
    tasks = [async_download_image(product_code, ext, session) for ext in ["1", "10"]]
    results = await asyncio.gather(*tasks)
    for ext, result in zip(["1", "10"], results):
        content, _url = result
        if content:
            return content, ext

    # fallback single language p1-fr/p1-de/p1-nl
    if fallback_ext and fallback_ext != "NL FR":
        content, _ = await async_download_image(product_code, fallback_ext, session)
        if content:
            return content, fallback_ext

    return None, None

# ---------------------- Main Processing Function ----------------------
async def process_file_async(uploaded_file, progress_bar=None, layout="horizontal"):
    session_id = st.session_state["bundle_creator_session_id"]
    base_folder = f"Bundle&Set_{session_id}"
    missing_images_excel_path = f"missing_images_{session_id}.xlsx"
    bundle_list_excel_path = f"bundle_list_{session_id}.xlsx"

    if "encryption_key" not in st.session_state:
        st.session_state["encryption_key"] = Fernet.generate_key()
    key = st.session_state["encryption_key"]
    fernet = Fernet(key)

    file_bytes = uploaded_file.read()
    decrypted_bytes = fernet.decrypt(fernet.encrypt(file_bytes))
    file_buffer = BytesIO(decrypted_bytes)

    try:
        if uploaded_file.name.lower().endswith('.xlsx'):
            data = pd.read_excel(file_buffer, dtype=str)
        else:
            data = pd.read_csv(file_buffer, delimiter=';', dtype=str)
    except pd.errors.EmptyDataError:
        st.error("The uploaded file is empty or could not be read.")
        return None, None, None, None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None, None, None, None

    required_columns = {'sku', 'pzns_in_set'}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        st.error(f"Missing required columns: {', '.join(missing_columns)}")
        return None, None, None, None

    data.dropna(subset=['sku', 'pzns_in_set'], inplace=True)
    if data.empty:
        st.error("The file is empty or contains no valid rows after cleaning!")
        return None, None, None, None

    total_rows = len(data)
    st.write(f"File loaded: {total_rows} bundles found.")
    os.makedirs(base_folder, exist_ok=True)

    # Batch
    chunk_size = 1000
    batches = []
    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        batches.append(data.iloc[start:end])

    total_batches = len(batches)
    st.info(f"Processing in {total_batches} batch(es) of up to {chunk_size} bundles each.")

    error_list = []
    bundle_list = []

    for batch_index, batch_df in enumerate(batches, start=1):
        batch_size = len(batch_df)
        if progress_bar is not None:
            progress_bar.progress(0.0, text=f"Processing batch {batch_index}/{total_batches} ({batch_size} bundles)")

        connector = aiohttp.TCPConnector(limit=100)
        async with aiohttp.ClientSession(connector=connector) as session:
            for j, (_, row) in enumerate(batch_df.iterrows()):
                bundle_code = str(row['sku']).strip()
                pzns_in_set_str = str(row['pzns_in_set']).strip()
                product_codes = [code.strip() for code in pzns_in_set_str.split(',') if code.strip()]

                if not product_codes:
                    st.warning(f"Skipping bundle {bundle_code}: No valid product codes found.")
                    error_list.append((bundle_code, "No valid PZNs listed"))
                    if progress_bar is not None:
                        progress_bar.progress(
                            (j + 1) / batch_size,
                            text=f"Batch {batch_index}/{total_batches} – {bundle_code} ({j+1}/{batch_size})"
                        )
                    continue

                num_products = len(product_codes)
                is_uniform = (len(set(product_codes)) == 1)
                bundle_type = f"bundle of {num_products}" if is_uniform else "mixed"
                bundle_cross_country = False

                fallback_ext = st.session_state.get("fallback_ext")

                # ---------------- UNIFORM BUNDLE ----------------
                if is_uniform:
                    product_code = product_codes[0]

                    is_cross_country_mode = fallback_ext in ["NL FR", "1-fr", "1-de", "1-nl"]
                    folder_name = get_uniform_folder(base_folder, num_products, is_cross_country_mode)
                    os.makedirs(folder_name, exist_ok=True)

                    result, used_ext = await async_get_image_with_fallback(product_code, session)

                    # --------- NL FR dict result (p1-fr and/or p1-nl exist) ----------
                    if used_ext == "NL FR" and isinstance(result, dict):
                        bundle_cross_country = True
                        folder_name = get_uniform_folder(base_folder, num_products, True)
                        os.makedirs(folder_name, exist_ok=True)

                        processed_keys = []
                        for lang, image_data in result.items():
                            suffix = "-fr-h1" if lang == "1-fr" else "-nl-h1"
                            try:
                                img = await asyncio.to_thread(Image.open, BytesIO(image_data))
                                if num_products == 2:
                                    final_img = await asyncio.to_thread(process_double_bundle_image, img, layout)
                                elif num_products == 3:
                                    final_img = await asyncio.to_thread(process_triple_bundle_image, img, layout)
                                else:
                                    final_img = img
                                save_path = os.path.join(folder_name, f"{bundle_code}{suffix}.jpg")
                                await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=75)
                                processed_keys.append(lang)
                            except Exception as e:
                                st.warning(f"Error processing {lang} image for bundle {bundle_code} (PZN: {product_code}): {e}")
                                error_list.append((bundle_code, f"{product_code} ({lang} processing error)"))

                        # duplicate missing lang for h1 (keep your behaviour)
                        if "1-fr" not in processed_keys and "1-nl" in processed_keys:
                            try:
                                img_dup = await asyncio.to_thread(Image.open, BytesIO(result["1-nl"]))
                                final_img_dup = img_dup
                                if num_products == 2:
                                    final_img_dup = await asyncio.to_thread(process_double_bundle_image, img_dup, layout)
                                elif num_products == 3:
                                    final_img_dup = await asyncio.to_thread(process_triple_bundle_image, img_dup, layout)
                                dup_save_path = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                                await asyncio.to_thread(final_img_dup.save, dup_save_path, "JPEG", quality=75)
                            except Exception as e:
                                st.warning(f"Error duplicating 1-fr for bundle {bundle_code} (PZN: {product_code}): {e}")
                                error_list.append((bundle_code, f"{product_code} (dup 1-fr processing error)"))

                        if "1-nl" not in processed_keys and "1-fr" in processed_keys:
                            try:
                                img_dup = await asyncio.to_thread(Image.open, BytesIO(result["1-fr"]))
                                final_img_dup = img_dup
                                if num_products == 2:
                                    final_img_dup = await asyncio.to_thread(process_double_bundle_image, img_dup, layout)
                                elif num_products == 3:
                                    final_img_dup = await asyncio.to_thread(process_triple_bundle_image, img_dup, layout)
                                dup_save_path = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                                await asyncio.to_thread(final_img_dup.save, dup_save_path, "JPEG", quality=75)
                            except Exception as e:
                                st.warning(f"Error duplicating 1-nl for bundle {bundle_code} (PZN: {product_code}): {e}")
                                error_list.append((bundle_code, f"{product_code} (dup 1-nl processing error)"))

                        # ===== extras p2..p9 ONLY if p1 exists for that language =====
                        try:
                            has_p1_fr = "1-fr" in result
                            has_p1_nl = "1-nl" in result

                            if has_p1_fr:
                                extra_fr = await async_download_p2_to_p9(product_code, session, lang_suffix="fr")
                                for p_num, img_bytes in extra_fr.items():
                                    extra_path = os.path.join(folder_name, f"{bundle_code}-fr-h{p_num}.jpg")
                                    await asyncio.to_thread(save_binary_jpg, extra_path, img_bytes)

                            if has_p1_nl:
                                extra_nl = await async_download_p2_to_p9(product_code, session, lang_suffix="nl")
                                for p_num, img_bytes in extra_nl.items():
                                    extra_path = os.path.join(folder_name, f"{bundle_code}-nl-h{p_num}.jpg")
                                    await asyncio.to_thread(save_binary_jpg, extra_path, img_bytes)

                        except Exception as e:
                            st.warning(f"Error downloading NL/FR extras p2..p9 for bundle {bundle_code} (PZN: {product_code}): {e}")
                            error_list.append((bundle_code, f"{product_code} (NL/FR p2..p9 download error)"))

                    # --------- Single image result (p1, p10, or 1-fr/1-de/1-nl) ----------
                    elif result:
                        used_is_lang = used_ext in ["1-fr", "1-de", "1-nl"]

                        # If actual used image is language-specific, put into cross-country folder tree
                        if used_is_lang:
                            bundle_cross_country = True
                            folder_name = get_uniform_folder(base_folder, num_products, True)
                            os.makedirs(folder_name, exist_ok=True)

                        try:
                            img = await asyncio.to_thread(Image.open, BytesIO(result))
                            if num_products == 2:
                                final_img = await asyncio.to_thread(process_double_bundle_image, img, layout)
                            elif num_products == 3:
                                final_img = await asyncio.to_thread(process_triple_bundle_image, img, layout)
                            else:
                                final_img = img

                            # If fallback_ext == "NL FR" but NOT dict, p1-fr/p1-nl do not exist -> NO extras
                            if fallback_ext == "NL FR" and used_ext != "NL FR":
                                folder_name = get_uniform_folder(base_folder, num_products, True)
                                os.makedirs(folder_name, exist_ok=True)
                                bundle_cross_country = True

                                save_path_nl = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                                save_path_fr = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                                await asyncio.to_thread(final_img.save, save_path_nl, "JPEG", quality=75)
                                await asyncio.to_thread(final_img.save, save_path_fr, "JPEG", quality=75)

                            else:
                                if used_ext == "1-fr":
                                    save_path = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                                    await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=75)
                                    try:
                                        extra = await async_download_p2_to_p9(product_code, session, lang_suffix="fr")
                                        for p_num, img_bytes in extra.items():
                                            extra_path = os.path.join(folder_name, f"{bundle_code}-fr-h{p_num}.jpg")
                                            await asyncio.to_thread(save_binary_jpg, extra_path, img_bytes)
                                    except Exception as e:
                                        st.warning(f"Error downloading FR extras p2..p9 for bundle {bundle_code} (PZN: {product_code}): {e}")
                                        error_list.append((bundle_code, f"{product_code} (FR p2..p9 download error)"))

                                elif used_ext == "1-de":
                                    save_path = os.path.join(folder_name, f"{bundle_code}-de-h1.jpg")
                                    await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=75)
                                    try:
                                        extra = await async_download_p2_to_p9(product_code, session, lang_suffix="de")
                                        for p_num, img_bytes in extra.items():
                                            extra_path = os.path.join(folder_name, f"{bundle_code}-de-h{p_num}.jpg")
                                            await asyncio.to_thread(save_binary_jpg, extra_path, img_bytes)
                                    except Exception as e:
                                        st.warning(f"Error downloading DE extras p2..p9 for bundle {bundle_code} (PZN: {product_code}): {e}")
                                        error_list.append((bundle_code, f"{product_code} (DE p2..p9 download error)"))

                                elif used_ext == "1-nl":
                                    save_path = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                                    await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=75)
                                    try:
                                        extra = await async_download_p2_to_p9(product_code, session, lang_suffix="nl")
                                        for p_num, img_bytes in extra.items():
                                            extra_path = os.path.join(folder_name, f"{bundle_code}-nl-h{p_num}.jpg")
                                            await asyncio.to_thread(save_binary_jpg, extra_path, img_bytes)
                                    except Exception as e:
                                        st.warning(f"Error downloading NL extras p2..p9 for bundle {bundle_code} (PZN: {product_code}): {e}")
                                        error_list.append((bundle_code, f"{product_code} (NL p2..p9 download error)"))

                                else:
                                    save_path = os.path.join(folder_name, f"{bundle_code}-h1.jpg")
                                    await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=75)

                                    # extras standard ONLY if p1 exists => used_ext == "1"
                                    if used_ext == "1":
                                        try:
                                            extra = await async_download_p2_to_p9(product_code, session, lang_suffix=None)
                                            for p_num, img_bytes in extra.items():
                                                extra_path = os.path.join(folder_name, f"{bundle_code}-h{p_num}.jpg")
                                                await asyncio.to_thread(save_binary_jpg, extra_path, img_bytes)
                                        except Exception as e:
                                            st.warning(f"Error downloading extras p2..p9 for bundle {bundle_code} (PZN: {product_code}): {e}")
                                            error_list.append((bundle_code, f"{product_code} (p2..p9 download error)"))

                        except Exception as e:
                            st.warning(f"Error processing image for bundle {bundle_code} (PZN: {product_code}, Ext: {used_ext}): {e}")
                            error_list.append((bundle_code, f"{product_code} (Ext: {used_ext} processing error)"))

                    else:
                        error_list.append((bundle_code, product_code))

                # ---------------- MIXED SET ----------------
                else:
                    is_cross_country_mode = fallback_ext in ["NL FR", "1-fr", "1-de", "1-nl"]
                    mixed_root = get_mixed_root(base_folder, is_cross_country_mode)
                    bundle_folder = os.path.join(mixed_root, bundle_code)
                    os.makedirs(bundle_folder, exist_ok=True)

                    item_is_cross_country = False

                    for p_code in product_codes:
                        result, used_ext = await async_get_image_with_fallback(p_code, session)

                        if used_ext == "NL FR" and isinstance(result, dict):
                            item_is_cross_country = True
                            prod_folder = os.path.join(bundle_folder, "cross-country")
                            os.makedirs(prod_folder, exist_ok=True)

                            processed_keys = []
                            for lang, image_data in result.items():
                                suffix = "-fr-h1" if lang == "1-fr" else "-nl-h1"
                                file_path = os.path.join(prod_folder, f"{p_code}{suffix}.jpg")
                                await asyncio.to_thread(process_and_save_trimmed_image, image_data, file_path)
                                processed_keys.append(lang)

                            if "1-fr" not in processed_keys and "1-nl" in processed_keys:
                                file_path_dup = os.path.join(prod_folder, f"{p_code}-fr-h1.jpg")
                                await asyncio.to_thread(process_and_save_trimmed_image, result["1-nl"], file_path_dup)
                            elif "1-nl" not in processed_keys and "1-fr" in processed_keys:
                                file_path_dup = os.path.join(prod_folder, f"{p_code}-nl-h1.jpg")
                                await asyncio.to_thread(process_and_save_trimmed_image, result["1-fr"], file_path_dup)

                        elif result:
                            prod_folder = bundle_folder
                            if used_ext in ["1-fr", "1-de", "1-nl"] or fallback_ext == "NL FR":
                                item_is_cross_country = True
                                prod_folder = os.path.join(bundle_folder, "cross-country")
                                os.makedirs(prod_folder, exist_ok=True)

                            if fallback_ext == "NL FR":
                                file_path_nl = os.path.join(prod_folder, f"{p_code}-nl-h1.jpg")
                                file_path_fr = os.path.join(prod_folder, f"{p_code}-fr-h1.jpg")
                                await asyncio.to_thread(process_and_save_trimmed_image, result, file_path_nl)
                                await asyncio.to_thread(process_and_save_trimmed_image, result, file_path_fr)
                            else:
                                suffix = f"-p{used_ext}" if used_ext else "-h1"
                                file_path = os.path.join(prod_folder, f"{p_code}{suffix}.jpg")
                                await asyncio.to_thread(process_and_save_trimmed_image, result, file_path)
                        else:
                            error_list.append((bundle_code, p_code))

                    if item_is_cross_country:
                        bundle_cross_country = True

                # Progress
                if progress_bar is not None:
                    progress_bar.progress(
                        (j + 1) / batch_size,
                        text=f"Batch {batch_index}/{total_batches} – {bundle_code} ({j+1}/{batch_size})"
                    )

                bundle_list.append([bundle_code, ', '.join(product_codes), bundle_type, "Yes" if bundle_cross_country else "No"])

        if progress_bar is not None:
            progress_bar.progress(1.0, text=f"Batch {batch_index}/{total_batches} completed")

    # Reports
    missing_images_data = None
    missing_images_df = pd.DataFrame(columns=["PZN Bundle", "PZN with image missing"])
    if error_list:
        missing_images_df = pd.DataFrame(error_list, columns=["PZN Bundle", "PZN with image missing"])
        missing_images_df = missing_images_df.groupby("PZN Bundle", as_index=False).agg({
            "PZN with image missing": lambda x: ', '.join(sorted(list(set(map(str, x)))))
        })
        try:
            missing_images_df.to_excel(missing_images_excel_path, index=False)
            with open(missing_images_excel_path, "rb") as f_csv:
                missing_images_data = f_csv.read()
        except Exception as e:
            st.error(f"Failed to save or read missing images Excel file: {e}")

    bundle_list_data = None
    bundle_list_df = pd.DataFrame(columns=["sku", "pzns_in_set", "bundle type", "cross-country"])
    if bundle_list:
        bundle_list_df = pd.DataFrame(bundle_list, columns=["sku", "pzns_in_set", "bundle type", "cross-country"])
        try:
            bundle_list_df.to_excel(bundle_list_excel_path, index=False)
            with open(bundle_list_excel_path, "rb") as f_csv:
                bundle_list_data = f_csv.read()
        except Exception as e:
            st.error(f"Failed to save or read bundle list Excel file: {e}")

    # ZIP
    zip_bytes = None
    if os.path.exists(base_folder) and any(os.scandir(base_folder)):
        temp_parent = f"Bundle&Set_temp_{session_id}"
        shutil.rmtree(temp_parent, ignore_errors=True)
        os.makedirs(temp_parent, exist_ok=True)

        zip_content_folder = os.path.join(temp_parent, "Bundle&Set")
        try:
            shutil.copytree(base_folder, zip_content_folder)
        except Exception as e:
            st.error(f"Error copying files for zipping: {e}")
            shutil.rmtree(temp_parent, ignore_errors=True)
            return None, missing_images_data, missing_images_df, bundle_list_data

        zip_base_name = f"Bundle&Set_archive_{session_id}"
        final_zip_path = f"{zip_base_name}.zip"
        try:
            shutil.make_archive(base_name=zip_base_name, format='zip', root_dir=temp_parent)
            if os.path.exists(final_zip_path):
                with open(final_zip_path, "rb") as zip_file:
                    zip_bytes = zip_file.read()
                os.remove(final_zip_path)
            else:
                st.error("Failed to create ZIP archive (file not found after creation attempt).")
        except Exception as e:
            st.error(f"Error during zipping process: {e}")
        finally:
            shutil.rmtree(temp_parent, ignore_errors=True)

    return zip_bytes, missing_images_data, missing_images_df, bundle_list_data

# ---------------------- UI ----------------------
st.title("PDM Bundle&Set Image Creator")

st.markdown(
    """
    **How to use:**

    1. Create a **Quick Report** in **Akeneo** containing the list of products.
    2. Select the following options:
       - File Type: **CSV** or **Excel** - All Attributes or Grid Context (for Grid Context, select ID and PZN included in the set) - **With Codes** - **Without Media**
    3. **Choose the language for language specific photos:** (if needed)
    4. **Choose bundle layout:** (Horizontal, Vertical, or Automatic)
    5. Click **Process File** to start the process.
    6. Download the files.
    7. **Before starting a new process, click on Clear Cache and Reset Data.**
    """
)

if st.button("🧹 Clear Cache and Reset Data"):
    keys_to_remove = [
        "bundle_creator_session_id", "encryption_key", "fallback_ext",
        "zip_data", "bundle_list_data", "missing_images_data",
        "missing_images_df", "processing_complete_bundle",
        "file_uploader", "preview_pzn_bundle", "sidebar_ext_bundle",
        "lang_select_bundle", "layout_select_bundle"
    ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    st.cache_data.clear()
    st.cache_resource.clear()
    try:
        clear_old_data()
    except Exception:
        pass
    st.success("Cache and session data cleared. Ready for a new task.")
    st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())
    time.sleep(1)
    st.rerun()

st.sidebar.header("What This App Does")
st.sidebar.markdown(
    """
    - ❓ **Automated Bundle&Set Creation:** Automatically create product bundles and mixed sets by downloading and organizing images;
    - 🔎 **Language Selection:** Choose the language if you have language-specific photos. NL-FR, DE, FR;
    - 🔎 **Choose the layout for double/triple bundles:** Automatic, Horizontal or Vertical;
    - ✏️ **Dynamic Processing:** Combine images (double/triple) with proper resizing;
    - ✏️ **Rename images** using the specific bundle&set code (e.g. -h1, -fr-h1, -nl-h2, etc);
    - ❌ **Error Logging:** Missing images are logged in an Excel;
    - 📥 **Download:** Get a ZIP with all processed images and reports;
    - 🌐 **Interactive Preview:** Preview and download individual product images from the sidebar.
    """,
    unsafe_allow_html=True
)

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
                fetch_status_code = response.status_code
                if fetch_status_code == 200:
                    image_data = response.content
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
    elif fetch_status_code == 404:
        st.sidebar.warning(f"No image found (404) for {product_code_preview} with -p{selected_extension}.jpg")
    elif fetch_status_code is not None:
        st.sidebar.error(f"Failed to fetch image (Status: {fetch_status_code}) for {product_code_preview} with -p{selected_extension}.jpg")

uploaded_file = st.file_uploader("**Upload CSV File**", type=["csv", "xlsx"], key="file_uploader")
if uploaded_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        fallback_language = st.selectbox(
            "**Choose the language for language specific photos:**",
            options=["None", "FR", "DE", "NL FR"],
            index=0,
            key="lang_select_bundle"
        )
    with col2:
        layout_choice = st.selectbox(
            "**Choose bundle layout:**",
            options=["Automatic", "Horizontal", "Vertical"],
            index=0,
            key="layout_select_bundle"
        )

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
        st.session_state["zip_data"] = None
        st.session_state["bundle_list_data"] = None
        st.session_state["missing_images_data"] = None
        st.session_state["missing_images_df"] = None
        st.session_state["processing_complete_bundle"] = False

        try:
            zip_data, missing_images_data, missing_images_df, bundle_list_data = asyncio.run(
                process_file_async(uploaded_file, progress_bar, layout=layout_choice)
            )
            progress_bar.progress(1.0, text="Processing Complete!")
            elapsed_time = time.time() - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)

            st.success(f"Processing finished in {minutes}m {seconds}s.")
            st.session_state["zip_data"] = zip_data
            st.session_state["bundle_list_data"] = bundle_list_data
            st.session_state["missing_images_data"] = missing_images_data
            st.session_state["missing_images_df"] = missing_images_df
            st.session_state["processing_complete_bundle"] = True
            time.sleep(1.5)
            progress_bar.empty()
        except Exception as e:
            progress_bar.empty()
            st.error(f"An error occurred during processing: {e}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            st.session_state["processing_complete_bundle"] = False

if st.session_state.get("processing_complete_bundle", False):
    st.markdown("---")
    if st.session_state.get("zip_data"):
        st.download_button(
            label="Download Bundle Images (ZIP)",
            data=st.session_state["zip_data"],
            file_name=f"BundleSet_{session_id}.zip",
            mime="application/zip",
            key="dl_zip_bundle_v"
        )
    else:
        st.info("Processing complete, but no ZIP file was generated (likely no images saved).")

    if st.session_state.get("bundle_list_data"):
        st.download_button(
            label="Download Bundle List",
            data=st.session_state["bundle_list_data"],
            file_name=f"bundle_list_{session_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_list_bundle_v"
        )
    else:
        st.info("Processing complete, but no bundle list report was generated.")

    missing_df = st.session_state.get("missing_images_df")
    if missing_df is not None:
        if not missing_df.empty:
            st.markdown("---")
            st.warning(f"{len(missing_df)} bundles with missing images:")
            st.dataframe(missing_df, use_container_width=True)
            if st.session_state.get("missing_images_data"):
                st.download_button(
                    label="Download Missing List",
                    data=st.session_state["missing_images_data"],
                    file_name=f"missing_images_{session_id}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_missing_bundle_v"
                )
        else:
            st.success("No missing images reported.")
