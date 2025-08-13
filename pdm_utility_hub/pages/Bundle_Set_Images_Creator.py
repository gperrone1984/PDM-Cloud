import streamlit as st
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
import zipfile
import pathlib

# =========================
# Page configuration
# =========================
st.set_page_config(
    page_title="Bundle Creator",
    page_icon="📦",
    layout="centered"
)

# =========================
# Authentication check
# =========================
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# =========================
# Global CSS
# =========================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] > div:first-child {
        width: 540px !important;
        min-width: 540px !important;
        max-width: 540px !important;
    }
    [data-testid="stSidebarNav"] { display: none; }

    div[data-testid="stAppViewContainer"] > section > div.block-container,
    .main .block-container {
         background-color: transparent !important;
         padding: 2rem 1rem 1rem 1rem !important;
         border-radius: 0.5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# Sidebar hub link
# =========================
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")

# =========================
# Session state management
# =========================
if "bundle_creator_session_id" not in st.session_state:
    st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())

session_id = st.session_state["bundle_creator_session_id"]
base_folder = f"Bundle&Set_{session_id}"
zip_final_path = f"Bundle&Set_{session_id}.zip"
missing_images_excel_path = f"missing_images_{session_id}.xlsx"
bundle_list_excel_path = f"bundle_list_{session_id}.xlsx"

# =========================
# Config: chunk mode & static serving
# =========================
CHUNK_SIZE = 1000            # ~1000 bundles per chunk
STATIC_DIR = pathlib.Path("static")
STATIC_DIR.mkdir(exist_ok=True)

# =========================
# Utility functions
# =========================
def clear_old_data():
    """Remove previous output folders and files for the current session."""
    for p in os.listdir("."):
        if p.startswith(f"Bundle&Set_{session_id}_part") and os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    if os.path.exists(base_folder):
        shutil.rmtree(base_folder, ignore_errors=True)

    for p in os.listdir("."):
        if p.startswith(f"Bundle&Set_{session_id}") and p.endswith(".zip"):
            try: os.remove(p)
            except Exception: pass

    for p in [missing_images_excel_path, bundle_list_excel_path, zip_final_path]:
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass

    for p in STATIC_DIR.glob(f"Bundle&Set_{session_id}*.zip"):
        try: p.unlink()
        except Exception: pass

def has_enough_space(path=".", required_bytes=200*1024*1024):
    """Check free disk space (default: require 200MB free)."""
    try:
        total, used, free = shutil.disk_usage(os.path.dirname(path) or ".")
        return free > required_bytes
    except Exception:
        return True

def move_to_static(file_path: str) -> str:
    """
    Move/copy a ZIP into ./static and return the public URL path './app/static/<filename>'.
    Requires [server] enableStaticServing = true (config or ENV).
    """
    src = pathlib.Path(file_path)
    dst = STATIC_DIR / src.name
    try:
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), str(dst))
    except Exception:
        shutil.copy2(str(src), str(dst))
    return f"./app/static/{dst.name}"

async def async_download_image(product_code, extension, session: aiohttp.ClientSession):
    if product_code.startswith(('1', '0')):
        product_code = f"D{product_code}"
    url = f"https://cdn.shop-apotheke.com/images/{product_code}-p{extension}.jpg"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                return content, url
            else:
                return None, None
    except Exception:
        return None, None

def trim(im):
    bg = Image.new(im.mode, im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

def process_double_bundle_image(image, layout="horizontal"):
    image = trim(image)
    width, height = image.size
    chosen_layout = "vertical" if (layout.lower() == "automatic" and height < width) else layout.lower()
    if chosen_layout == "horizontal":
        merged_width = width * 2; merged_height = height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0)); merged_image.paste(image, (width, 0))
    elif chosen_layout == "vertical":
        merged_width = width; merged_height = height * 2
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0)); merged_image.paste(image, (0, height))
    else:
        merged_width = width * 2; merged_height = height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0)); merged_image.paste(image, (width, 0))
    scale_factor = 1 if (merged_width == 0 or merged_height == 0) else min(1000/merged_width, 1000/merged_height)
    new_size = (int(merged_width * scale_factor), int(merged_height * scale_factor))
    resized_image = image.resize(new_size, Image.LANCZOS) if new_size != (width, height) else image
    final_image = Image.new("RGB", (1000, 1000), (255, 255, 255))
    x_offset = (1000 - new_size[0]) // 2; y_offset = (1000 - new_size[1]) // 2
    final_image.paste(resized_image, (x_offset, y_offset))
    return final_image

def process_triple_bundle_image(image, layout="horizontal"):
    image = trim(image)
    width, height = image.size
    chosen_layout = "vertical" if (layout.lower() == "automatic" and height < width) else layout.lower()
    if chosen_layout == "horizontal":
        merged_width = width * 3; merged_height = height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0)); merged_image.paste(image, (width, 0)); merged_image.paste(image, (width*2, 0))
    elif chosen_layout == "vertical":
        merged_width = width; merged_height = height * 3
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0)); merged_image.paste(image, (0, height)); merged_image.paste(image, (0, height*2))
    else:
        merged_width = width * 3; merged_height = height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0)); merged_image.paste(image, (width, 0)); merged_image.paste(image, (width*2, 0))
    scale_factor = 1 if (merged_width == 0 or merged_height == 0) else min(1000/merged_width, 1000/merged_height)
    new_size = (int(merged_width * scale_factor), int(merged_height * scale_factor))
    resized_image = image.resize(new_size, Image.LANCZOS) if new_size != (width, height) else image
    final_image = Image.new("RGB", (1000, 1000), (255, 255, 255))
    x_offset = (1000 - new_size[0]) // 2; y_offset = (1000 - new_size[1]) // 2
    final_image.paste(resized_image, (x_offset, y_offset))
    return final_image

def save_binary_file(path, data):
    with open(path, 'wb') as f:
        f.write(data)

async def async_get_nl_fr_images(product_code, session: aiohttp.ClientSession):
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

async def async_get_image_with_fallback(product_code, session: aiohttp.ClientSession):
    fallback_ext = st.session_state.get("fallback_ext", None)
    if fallback_ext == "NL FR":
        images_dict = await async_get_nl_fr_images(product_code, session)
        if images_dict:
            return images_dict, "NL FR"
    tasks = [async_download_image(product_code, ext, session) for ext in ["1", "10"]]
    results = await asyncio.gather(*tasks)
    for ext, result in zip(["1", "10"], results):
        content, _ = result
        if content:
            return content, ext
    if fallback_ext and fallback_ext != "NL FR":
        content, _ = await async_download_image(product_code, fallback_ext, session)
        if content:
            return content, fallback_ext
    return None, None

def zip_folder_no_copy(folder_path, zip_path, root_name="Bundle&Set"):
    """
    Create a ZIP without copying the folder / loading into RAM.
    Returns number of files added to the ZIP.
    """
    count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, folder_path)
                arcname = os.path.join(root_name, rel_path)
                zf.write(abs_path, arcname)
                count += 1
    return count

# =========================
# Main processing (single ZIP)
# =========================
async def process_file_async(uploaded_file, progress_bar=None, layout="horizontal"):
    """
    Process the entire file and produce a single ZIP.
    Returns: zip_ref (local path or ./app/static/ URL), missing_images_bytes, missing_df, bundle_list_bytes
    """
    session_id = st.session_state["bundle_creator_session_id"]
    base_folder = f"Bundle&Set_{session_id}"
    missing_images_excel_path = f"missing_images_{session_id}.xlsx"
    bundle_list_excel_path = f"bundle_list_{session_id}.xlsx"
    zip_final_path = f"Bundle&Set_{session_id}.zip"

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

    st.write(f"File loaded: {len(data)} bundles found.")
    os.makedirs(base_folder, exist_ok=True)

    mixed_sets_needed = False
    mixed_folder = os.path.join(base_folder, "mixed_sets")
    error_list = []
    bundle_list = []
    total = len(data)

    connector = aiohttp.TCPConnector(limit=60, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=30)
    default_headers = {"User-Agent": "Mozilla/5.0 BundleCreator"}
    async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=default_headers) as session:
        for i, (_, row) in enumerate(data.iterrows()):
            bundle_code = str(row['sku']).strip()
            pzns_in_set_str = str(row['pzns_in_set']).strip()
            product_codes = [code.strip() for code in pzns_in_set_str.split(',') if code.strip()]

            if not product_codes:
                st.warning(f"Skipping bundle {bundle_code}: No valid product codes found.")
                error_list.append((bundle_code, "No valid PZNs listed"))
                continue

            num_products = len(product_codes)
            is_uniform = (len(set(product_codes)) == 1)
            bundle_type = f"bundle of {num_products}" if is_uniform else "mixed"
            bundle_cross_country = False

            if is_uniform:
                product_code = product_codes[0]
                folder_name_base = f"bundle_{num_products}"
                if st.session_state.get("fallback_ext") in ["NL FR", "1-fr", "1-de", "1-nl"]:
                    folder_name_base = "cross-country"
                folder_name = os.path.join(base_folder, folder_name_base)
                os.makedirs(folder_name, exist_ok=True)

                result, used_ext = await async_get_image_with_fallback(product_code, session)

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
                        try:
                            img = await asyncio.to_thread(Image.open, BytesIO(image_data))
                            if num_products == 2:
                                final_img = await asyncio.to_thread(process_double_bundle_image, img, layout)
                            elif num_products == 3:
                                final_img = await asyncio.to_thread(process_triple_bundle_image, img, layout)
                            else:
                                final_img = img
                            save_path = os.path.join(folder_name, f"{bundle_code}{suffix}.jpg")
                            await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=90, optimize=True)
                            processed_lang = True
                            processed_keys.append(lang)
                        except Exception as e:
                            st.warning(f"Error processing {lang} image for bundle {bundle_code} (PZN: {product_code}): {e}")
                            error_list.append((bundle_code, f"{product_code} ({lang} processing error)"))
                    if processed_lang:
                        if "1-fr" not in processed_keys and "1-nl" in processed_keys:
                            try:
                                img_dup = await asyncio.to_thread(Image.open, BytesIO(result["1-nl"]))
                                if num_products == 2:
                                    final_img_dup = await asyncio.to_thread(process_double_bundle_image, img_dup, layout)
                                elif num_products == 3:
                                    final_img_dup = await asyncio.to_thread(process_triple_bundle_image, img_dup, layout)
                                else:
                                    final_img_dup = img_dup
                                dup_save_path = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                                await asyncio.to_thread(final_img_dup.save, dup_save_path, "JPEG", quality=90, optimize=True)
                            except Exception as e:
                                st.warning(f"Error duplicating image for missing 1-fr for bundle {bundle_code} (PZN: {product_code}): {e}")
                                error_list.append((bundle_code, f"{product_code} (dup 1-fr processing error)"))
                        elif "1-nl" not in processed_keys and "1-fr" in processed_keys:
                            try:
                                img_dup = await asyncio.to_thread(Image.open, BytesIO(result["1-fr"]))
                                if num_products == 2:
                                    final_img_dup = await asyncio.to_thread(process_double_bundle_image, img_dup, layout)
                                elif num_products == 3:
                                    final_img_dup = await asyncio.to_thread(process_triple_bundle_image, img_dup, layout)
                                else:
                                    final_img_dup = img_dup
                                dup_save_path = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                                await asyncio.to_thread(final_img_dup.save, dup_save_path, "JPEG", quality=90, optimize=True)
                            except Exception as e:
                                st.warning(f"Error duplicating image for missing 1-nl for bundle {bundle_code} (PZN: {product_code}): {e}")
                                error_list.append((bundle_code, f"{product_code} (dup 1-nl processing error)"))
                    if not processed_lang:
                        error_list.append((bundle_code, f"{product_code} (NL/FR found but failed processing)"))

                elif result:
                    if used_ext in ["1-fr", "1-de", "1-nl"]:
                        bundle_cross_country = True
                        folder_name = os.path.join(base_folder, "cross-country")
                        os.makedirs(folder_name, exist_ok=True)
                    try:
                        img = await asyncio.to_thread(Image.open, BytesIO(result))
                        if num_products == 2:
                            final_img = await asyncio.to_thread(process_double_bundle_image, img, layout)
                        elif num_products == 3:
                            final_img = await asyncio.to_thread(process_triple_bundle_image, img, layout)
                        else:
                            final_img = img
                        if st.session_state.get("fallback_ext") == "NL FR":
                            save_path_nl = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                            save_path_fr = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                            await asyncio.to_thread(final_img.save, save_path_nl, "JPEG", quality=90, optimize=True)
                            await asyncio.to_thread(final_img.save, save_path_fr, "JPEG", quality=90, optimize=True)
                        else:
                            save_path = os.path.join(folder_name, f"{bundle_code}-h1.jpg")
                            await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=90, optimize=True)
                    except Exception as e:
                        st.warning(f"Error processing image for bundle {bundle_code} (PZN: {product_code}, Ext: {used_ext}): {e}")
                        error_list.append((bundle_code, f"{product_code} (Ext: {used_ext} processing error)"))
                else:
                    error_list.append((bundle_code, product_code))

            else:  # Mixed set
                mixed_sets_needed = True
                bundle_folder = os.path.join(mixed_folder, bundle_code)
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
                            if lang == "1-fr":
                                suffix = "-fr-h1"
                            elif lang == "1-nl":
                                suffix = "-nl-h1"
                            else:
                                suffix = f"-p{lang}"
                            file_path = os.path.join(prod_folder, f"{p_code}{suffix}.jpg")
                            await asyncio.to_thread(save_binary_file, file_path, image_data)
                            processed_keys.append(lang)
                        if "1-fr" not in processed_keys and "1-nl" in processed_keys:
                            file_path_dup = os.path.join(prod_folder, f"{p_code}-fr-h1.jpg")
                            await asyncio.to_thread(save_binary_file, file_path_dup, result["1-nl"])
                        elif "1-nl" not in processed_keys and "1-fr" in processed_keys:
                            file_path_dup = os.path.join(prod_folder, f"{p_code}-nl-h1.jpg")
                            await asyncio.to_thread(save_binary_file, file_path_dup, result["1-fr"])
                    elif result:
                        prod_folder = bundle_folder
                        if used_ext in ["1-fr", "1-de", "1-nl"]:
                            item_is_cross_country = True
                            prod_folder = os.path.join(bundle_folder, "cross-country")
                            os.makedirs(prod_folder, exist_ok=True)
                        if st.session_state.get("fallback_ext") == "NL FR":
                            file_path_nl = os.path.join(prod_folder, f"{p_code}-nl-h1.jpg")
                            file_path_fr = os.path.join(prod_folder, f"{p_code}-fr-h1.jpg")
                            await asyncio.to_thread(save_binary_file, file_path_nl, result)
                            await asyncio.to_thread(save_binary_file, file_path_fr, result)
                        else:
                            suffix = f"-p{used_ext}" if used_ext else "-h1"
                            file_path = os.path.join(prod_folder, f"{p_code}{suffix}.jpg")
                            await asyncio.to_thread(save_binary_file, file_path, result)
                    else:
                        error_list.append((bundle_code, p_code))
                if item_is_cross_country:
                    bundle_cross_country = True

            if progress_bar is not None:
                progress_bar.progress((i + 1) / total, text=f"Processing {bundle_code} ({i+1}/{total})")
            bundle_list.append([bundle_code, ', '.join(product_codes), bundle_type, "Yes" if bundle_cross_country else "No"])

    if not mixed_sets_needed and os.path.exists(mixed_folder):
        try:
            shutil.rmtree(mixed_folder)
        except Exception as e:
            st.warning(f"Could not remove unused mixed folder: {e}")

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
    if bundle_list:
        try:
            pd.DataFrame(bundle_list, columns=["sku", "pzns_in_set", "bundle type", "cross-country"]).to_excel(bundle_list_excel_path, index=False)
            with open(bundle_list_excel_path, "rb") as f_csv:
                bundle_list_data = f_csv.read()
        except Exception as e:
            st.error(f"Failed to save or read bundle list Excel file: {e}")

    # Create single ZIP
    zip_ref = None
    if os.path.exists(base_folder) and any(os.scandir(base_folder)):
        if not has_enough_space("."):
            st.error("Insufficient disk space to create the ZIP on the server. Try reducing the batch size.")
            return None, missing_images_data, missing_images_df, bundle_list_data

        try:
            if os.path.exists(zip_final_path):
                try: os.remove(zip_final_path)
                except Exception: pass
            files_in_zip = zip_folder_no_copy(base_folder, zip_final_path, root_name="Bundle&Set")
            if files_in_zip == 0:
                st.error("ZIP creation resulted in 0 files. Likely no images were downloaded (check CDN access or headers).")
                return None, missing_images_data, missing_images_df, bundle_list_data

            size_mb = os.path.getsize(zip_final_path) / 1024 / 1024
            zip_ref = move_to_static(zip_final_path) if size_mb >= 80 else zip_final_path
        except OSError as e:
            if "No space left" in str(e):
                st.error("No space left on device during zipping. Reduce the batch size.")
            else:
                st.error(f"OS error during zipping: {e}")
            return None, missing_images_data, missing_images_df, bundle_list_data
        except Exception as e:
            st.error(f"Error during zipping process: {e}")
            return None, missing_images_data, missing_images_df, bundle_list_data
    else:
        st.info("Processing complete, but no images were saved to create a ZIP file.")
        try:
            os.rmdir(base_folder)
        except OSError:
            try:
                shutil.rmtree(base_folder)
            except Exception as e:
                st.warning(f"Could not remove base folder {base_folder}: {e}")
        return None, missing_images_data, missing_images_df, bundle_list_data

    return zip_ref, missing_images_data, missing_images_df, bundle_list_data

# =========================
# Chunk processing (all chunks via static links; no inline links)
# =========================
async def process_chunks_async(uploaded_file, progress_bar=None, layout="horizontal", chunk_size=CHUNK_SIZE):
    """
    Read the file once, then process in chunks of `chunk_size`.
    For each chunk:
      - create dedicated output folders (suffix _part{n})
      - download/process images
      - create a ZIP for that chunk
      - ALWAYS move to ./app/static and return the link (no UI inside this function)
      - remove the chunk folder to free space
    Returns:
      - zip_refs: list of static links (./app/static/filename.zip)
      - missing_images_bytes (global report)
      - missing_df (for on-screen table)
      - bundle_list_bytes (global report)
    """
    if "encryption_key" not in st.session_state:
        st.session_state["encryption_key"] = Fernet.generate_key()
    fernet = Fernet(st.session_state["encryption_key"])

    file_bytes = uploaded_file.read()
    decrypted_bytes = fernet.decrypt(fernet.encrypt(file_bytes))
    buf = BytesIO(decrypted_bytes)
    try:
        if uploaded_file.name.lower().endswith('.xlsx'):
            full_df = pd.read_excel(buf, dtype=str)
        else:
            full_df = pd.read_csv(buf, delimiter=';', dtype=str)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return [], None, pd.DataFrame(), None

    required = {'sku', 'pzns_in_set'}
    if not required.issubset(full_df.columns):
        st.error(f"Missing required columns: {', '.join(required - set(full_df.columns))}")
        return [], None, pd.DataFrame(), None

    full_df.dropna(subset=['sku','pzns_in_set'], inplace=True)
    if full_df.empty:
        st.error("The file is empty or contains no valid rows after cleaning!")
        return [], None, pd.DataFrame(), None

    total_rows = len(full_df)
    st.write(f"File loaded: {total_rows} bundles found. Processing in chunks of {chunk_size}…")

    all_missing = []
    all_bundle_rows = []
    zip_refs = []

    connector = aiohttp.TCPConnector(limit=60, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=30)
    default_headers = {"User-Agent": "Mozilla/5.0 BundleCreator"}
    async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=default_headers) as session:
        num_parts = (total_rows + chunk_size - 1) // chunk_size
        for part_idx in range(num_parts):
            start = part_idx * chunk_size
            end   = min(start + chunk_size, total_rows)
            data  = full_df.iloc[start:end].copy()

            base_folder_part = f"Bundle&Set_{session_id}_part{part_idx+1}"
            mixed_folder = os.path.join(base_folder_part, "mixed_sets")
            os.makedirs(base_folder_part, exist_ok=True)

            error_list = []
            bundle_list_rows = []
            mixed_sets_needed = False
            saved_files_counter = 0

            for i, (_, row) in enumerate(data.iterrows(), start=1):
                bundle_code = str(row['sku']).strip()
                pzns_in_set_str = str(row['pzns_in_set']).strip()
                product_codes = [c.strip() for c in pzns_in_set_str.split(',') if c.strip()]
                if not product_codes:
                    error_list.append((bundle_code, "No valid PZNs listed"))
                    continue

                num_products = len(product_codes)
                is_uniform = (len(set(product_codes)) == 1)
                bundle_type = f"bundle of {num_products}" if is_uniform else "mixed"
                bundle_cross_country = False

                if is_uniform:
                    product_code = product_codes[0]
                    folder_name_base = f"bundle_{num_products}"
                    if st.session_state.get("fallback_ext") in ["NL FR", "1-fr", "1-de", "1-nl"]:
                        folder_name_base = "cross-country"
                    folder_name = os.path.join(base_folder_part, folder_name_base)
                    os.makedirs(folder_name, exist_ok=True)

                    result, used_ext = await async_get_image_with_fallback(product_code, session)

                    if used_ext == "NL FR" and isinstance(result, dict):
                        bundle_cross_country = True
                        folder_name = os.path.join(base_folder_part, "cross-country")
                        os.makedirs(folder_name, exist_ok=True)
                        processed = []
                        for lang, img_bytes in result.items():
                            suffix = "-fr-h1" if lang=="1-fr" else "-nl-h1" if lang=="1-nl" else f"-p{lang}"
                            try:
                                img = await asyncio.to_thread(Image.open, BytesIO(img_bytes))
                                if num_products == 2:
                                    final_img = await asyncio.to_thread(process_double_bundle_image, img, layout)
                                elif num_products == 3:
                                    final_img = await asyncio.to_thread(process_triple_bundle_image, img, layout)
                                else:
                                    final_img = img
                                save_path = os.path.join(folder_name, f"{bundle_code}{suffix}.jpg")
                                await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=90, optimize=True)
                                processed.append(lang)
                                saved_files_counter += 1
                            except Exception:
                                error_list.append((bundle_code, f"{product_code} ({lang} processing error)"))
                        if "1-fr" not in processed and "1-nl" in processed:
                            p = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                            await asyncio.to_thread(save_binary_file, p, result["1-nl"]); saved_files_counter += 1
                        elif "1-nl" not in processed and "1-fr" in processed:
                            p = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                            await asyncio.to_thread(save_binary_file, p, result["1-fr"]); saved_files_counter += 1
                        if not processed:
                            error_list.append((bundle_code, f"{product_code} (NL/FR found but failed processing)"))
                    elif result:
                        if used_ext in ["1-fr","1-de","1-nl"]:
                            bundle_cross_country = True
                            folder_name = os.path.join(base_folder_part, "cross-country")
                            os.makedirs(folder_name, exist_ok=True)
                        try:
                            img = await asyncio.to_thread(Image.open, BytesIO(result))
                            if num_products == 2:
                                final_img = await asyncio.to_thread(process_double_bundle_image, img, layout)
                            elif num_products == 3:
                                final_img = await asyncio.to_thread(process_triple_bundle_image, img, layout)
                            else:
                                final_img = img
                            if st.session_state.get("fallback_ext") == "NL FR":
                                p_nl = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                                p_fr = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                                await asyncio.to_thread(final_img.save, p_nl, "JPEG", quality=90, optimize=True); saved_files_counter += 1
                                await asyncio.to_thread(final_img.save, p_fr, "JPEG", quality=90, optimize=True); saved_files_counter += 1
                            else:
                                p = os.path.join(folder_name, f"{bundle_code}-h1.jpg")
                                await asyncio.to_thread(final_img.save, p, "JPEG", quality=90, optimize=True); saved_files_counter += 1
                        except Exception:
                            error_list.append((bundle_code, f"{product_code} (Ext: {used_ext} processing error)"))
                    else:
                        error_list.append((bundle_code, product_code))
                else:
                    mixed_sets_needed = True
                    bundle_folder = os.path.join(mixed_folder, bundle_code)
                    os.makedirs(bundle_folder, exist_ok=True)
                    item_is_cross_country = False
                    for p_code in product_codes:
                        result, used_ext = await async_get_image_with_fallback(p_code, session)
                        if used_ext == "NL FR" and isinstance(result, dict):
                            item_is_cross_country = True
                            prod_folder = os.path.join(bundle_folder, "cross-country")
                            os.makedirs(prod_folder, exist_ok=True)
                            processed = []
                            for lang, img_bytes in result.items():
                                suffix = "-fr-h1" if lang=="1-fr" else "-nl-h1" if lang=="1-nl" else f"-p{lang}"
                                file_path = os.path.join(prod_folder, f"{p_code}{suffix}.jpg")
                                await asyncio.to_thread(save_binary_file, file_path, img_bytes); saved_files_counter += 1
                                processed.append(lang)
                            if "1-fr" not in processed and "1-nl" in processed:
                                await asyncio.to_thread(save_binary_file, os.path.join(prod_folder, f"{p_code}-fr-h1.jpg"), result["1-nl"]); saved_files_counter += 1
                            elif "1-nl" not in processed and "1-fr" in processed:
                                await asyncio.to_thread(save_binary_file, os.path.join(prod_folder, f"{p_code}-nl-h1.jpg"), result["1-fr"]); saved_files_counter += 1
                        elif result:
                            prod_folder = bundle_folder
                            if used_ext in ["1-fr","1-de","1-nl"]:
                                item_is_cross_country = True
                                prod_folder = os.path.join(bundle_folder, "cross-country")
                                os.makedirs(prod_folder, exist_ok=True)
                            if st.session_state.get("fallback_ext") == "NL FR":
                                await asyncio.to_thread(save_binary_file, os.path.join(prod_folder, f"{p_code}-nl-h1.jpg"), result); saved_files_counter += 1
                                await asyncio.to_thread(save_binary_file, os.path.join(prod_folder, f"{p_code}-fr-h1.jpg"), result); saved_files_counter += 1
                            else:
                                suffix = f"-p{used_ext}" if used_ext else "-h1"
                                await asyncio.to_thread(save_binary_file, os.path.join(prod_folder, f"{p_code}{suffix}.jpg"), result); saved_files_counter += 1
                        else:
                            error_list.append((bundle_code, p_code))
                    if item_is_cross_country:
                        bundle_cross_country = True

                if progress_bar is not None:
                    frac = (start + i) / total_rows
                    progress_bar.progress(frac, text=f"Processing part {part_idx+1}/{num_parts} • {bundle_code} ({start+i}/{total_rows})")

                bundle_list_rows.append([bundle_code, ', '.join(product_codes), bundle_type, "Yes" if bundle_cross_country else "No"])

            if not mixed_sets_needed and os.path.exists(mixed_folder):
                shutil.rmtree(mixed_folder, ignore_errors=True)

            all_missing.extend(error_list)
            all_bundle_rows.extend(bundle_list_rows)

            # Create ZIP for this chunk -> ALWAYS return link, do not render here
            if os.path.exists(base_folder_part) and any(os.scandir(base_folder_part)):
                if not has_enough_space("."):
                    st.error("Insufficient disk space while creating a ZIP chunk.")
                    shutil.rmtree(base_folder_part, ignore_errors=True)
                    continue
                zip_path_part = f"Bundle&Set_{session_id}_part{part_idx+1}.zip"
                try:
                    if os.path.exists(zip_path_part):
                        os.remove(zip_path_part)
                    files_in_zip = zip_folder_no_copy(base_folder_part, zip_path_part, root_name=f"Bundle&Set_part{part_idx+1}")
                    if files_in_zip == 0:
                        st.warning(f"Part {part_idx+1}: ZIP would be empty (no images downloaded).")
                        shutil.rmtree(base_folder_part, ignore_errors=True)
                        continue
                except Exception as e:
                    st.error(f"Error zipping chunk {part_idx+1}: {e}")
                    shutil.rmtree(base_folder_part, ignore_errors=True)
                    continue

                url = move_to_static(zip_path_part)  # ./app/static/...
                zip_refs.append(url)
                shutil.rmtree(base_folder_part, ignore_errors=True)
                st.info(f"Part {part_idx+1}/{num_parts} ready • files saved: {saved_files_counter}")
            else:
                st.info(f"Part {part_idx+1}: no images produced.")

    # Build global reports
    missing_images_data = None
    missing_df = pd.DataFrame(columns=["PZN Bundle","PZN with image missing"])
    if all_missing:
        missing_df = pd.DataFrame(all_missing, columns=["PZN Bundle","PZN with image missing"])
        missing_df = missing_df.groupby("PZN Bundle", as_index=False).agg({
            "PZN with image missing": lambda x: ', '.join(sorted(list(set(map(str, x)))))
        })
        try:
            path_miss = f"missing_images_{session_id}.xlsx"
            missing_df.to_excel(path_miss, index=False)
            with open(path_miss, "rb") as f:
                missing_images_data = f.read()
        except Exception as e:
            st.error(f"Failed to build global missing report: {e}")

    bundle_list_data = None
    if all_bundle_rows:
        try:
            path_list = f"bundle_list_{session_id}.xlsx"
            pd.DataFrame(all_bundle_rows, columns=["sku","pzns_in_set","bundle type","cross-country"]).to_excel(path_list, index=False)
            with open(path_list, "rb") as f:
                bundle_list_data = f.read()
        except Exception as e:
            st.error(f"Failed to build global bundle list report: {e}")

    return zip_refs, missing_images_data, missing_df, bundle_list_data

# =========================
# UI
# =========================
st.title("PDM Bundle&Set Image Creator")

st.markdown(
    """
    **How to use:**

    1. Create a **Quick Report** in **Akeneo** containing the list of products.
    2. Select: **CSV** or **Excel** – All Attributes or Grid Context (ID + PZN included in the set) – **With Codes** – **Without Media**.
    3. **Pick language** for language-specific photos (optional).
    4. **Pick bundle layout** (Horizontal, Vertical, or Automatic).
    5. Click **Process CSV**.
    6. Download results.
    7. Before a new run, click **Clear Cache and Reset Data**.
    """
)

if st.button("🧹 Clear Cache and Reset Data"):
    for k in ["bundle_creator_session_id", "encryption_key", "fallback_ext",
              "zip_path", "zip_refs", "bundle_list_data", "missing_images_data",
              "missing_images_df", "processing_complete_bundle",
              "file_uploader", "preview_pzn_bundle", "sidebar_ext_bundle"]:
        st.session_state.pop(k, None)
    st.cache_data.clear()
    st.cache_resource.clear()
    try:
        clear_old_data()
    except Exception as e:
        st.warning(f"Error during clear_old_data: {e}")
    st.success("Cache and session data cleared. Ready for a new task.")
    if "bundle_creator_session_id" not in st.session_state:
        st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())
    time.sleep(1)
    st.rerun()

# Sidebar info (English)
st.sidebar.header("What This App Does")
st.sidebar.markdown(
    """
    - **Automated Bundle&Set Creation** (bundles & mixed sets).
    - **Language Selection** (NL-FR, DE, FR).
    - **Double/Triple layout** (Automatic, Horizontal, Vertical).
    - **Dynamic image composition** with proper resizing.
    - **Renaming** (e.g. -h1, -p1-fr, -p1-nl).
    - **Error Logging** (missing images report).
    - **Download** as ZIP(s).
    - **Preview** an individual product in the sidebar.
    """, unsafe_allow_html=True
)

# Sidebar preview
st.sidebar.header("Product Image Preview")
product_code_preview = st.sidebar.text_input("Enter Product Code:", key="preview_pzn_bundle")
selected_extension = st.sidebar.selectbox(
    "Select Image Extension (p…)",
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
            fetch_status_code = None
            try:
                import requests
                response = requests.get(preview_url, stream=True, timeout=10, headers={"User-Agent":"Mozilla/5.0 BundleCreator"})
                if response.status_code == 200:
                    image_data = response.content
                else:
                    fetch_status_code = response.status_code
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

    if image_data:
        try:
            from PIL import Image as PILImage
            image = PILImage.open(BytesIO(image_data))
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

# Main uploader & processing
uploaded_file = st.file_uploader("**Upload CSV File**", type=["csv", "xlsx"], key="file_uploader")
if uploaded_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        fallback_language = st.selectbox("**Choose the language for language specific photos:**", options=["None", "FR", "DE", "NL FR"], index=0, key="lang_select_bundle")
    with col2:
        layout_choice = st.selectbox("**Choose bundle layout:**", options=["Automatic", "Horizontal", "Vertical"], index=0, key="layout_select_bundle")

    # Chunk mode toggle (recommended for large jobs)
    chunk_mode = st.checkbox("Process in chunks of 1000 (recommended for large jobs)", value=True)

    # Set fallback extension in session state
    if fallback_language == "NL FR":
        st.session_state["fallback_ext"] = "NL FR"
    elif fallback_language != "None":
        st.session_state["fallback_ext"] = f"1-{fallback_language.lower()}"
    else:
        st.session_state.pop("fallback_ext", None)

    if st.button("Process CSV", key="process_csv_bundle"):
        start_time = time.time()
        progress_bar = st.progress(0, text="Starting processing...")

        # Reset state (avoid stale links / duplicate sections)
        for k in ["zip_path", "zip_refs", "bundle_list_data", "missing_images_data", "missing_images_df", "processing_complete_bundle"]:
            st.session_state.pop(k, None)

        try:
            if chunk_mode:
                zip_refs, missing_images_data, missing_images_df, bundle_list_data = asyncio.run(
                    process_chunks_async(uploaded_file, progress_bar, layout=layout_choice, chunk_size=CHUNK_SIZE)
                )
                st.session_state["zip_refs"] = zip_refs
            else:
                zip_path, missing_images_data, missing_images_df, bundle_list_data = asyncio.run(
                    process_file_async(uploaded_file, progress_bar, layout=layout_choice)
                )
                st.session_state["zip_path"] = zip_path

            progress_bar.progress(1.0, text="Processing Complete!")
            elapsed_time = time.time() - start_time
            minutes = int(elapsed_time // 60); seconds = int(elapsed_time % 60)
            st.success(f"Processing finished in {minutes}m {seconds}s.")
            st.session_state["bundle_list_data"] = bundle_list_data
            st.session_state["missing_images_data"] = missing_images_data
            st.session_state["missing_images_df"] = missing_images_df
            st.session_state["processing_complete_bundle"] = True
            time.sleep(0.5)
            progress_bar.empty()
        except Exception as e:
            progress_bar.empty()
            st.error(f"An error occurred during processing: {e}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            st.session_state["processing_complete_bundle"] = False

# =========================
# Downloads & reports
# =========================
if st.session_state.get("processing_complete_bundle", False):
    st.markdown("---")

    # CHUNKS: single section, once
    if st.session_state.get("zip_refs"):
        st.subheader("Chunk downloads")
        for idx, url in enumerate(st.session_state["zip_refs"], start=1):
            st.markdown(
                f'<a href="{url}" download target="_blank" rel="noopener">✅ Part {idx}: Download ZIP</a>',
                unsafe_allow_html=True
            )

    # SINGLE ZIP
    elif st.session_state.get("zip_path"):
        zip_ref = st.session_state["zip_path"]
        if isinstance(zip_ref, str) and zip_ref.startswith("./app/static/"):
            st.markdown(
                f'<a href="{zip_ref}" download target="_blank" rel="noopener">⬇️ Download Bundle Images (ZIP)</a>',
                unsafe_allow_html=True
            )
        elif isinstance(zip_ref, str) and os.path.exists(zip_ref):
            with open(zip_ref, "rb") as f:
                st.download_button(
                    label="Download Bundle Images (ZIP)",
                    data=f,
                    file_name=os.path.basename(zip_ref),
                    mime="application/zip",
                    key="dl_zip_bundle_v"
                )
        else:
            st.info("Processing complete, but no ZIP file was generated (likely no images saved).")

    # Reports
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

    st.markdown("---")
    if st.button("🗑️ Delete generated ZIPs (free up server space)"):
        deleted = 0
        for p in os.listdir("."):
            if p.startswith(f"Bundle&Set_{session_id}") and p.endswith(".zip"):
                try:
                    os.remove(p); deleted += 1
                except Exception:
                    pass
        for p in STATIC_DIR.glob(f"Bundle&Set_{session_id}*.zip"):
            try:
                p.unlink(); deleted += 1
            except Exception:
                pass
        st.success(f"Deleted {deleted} ZIP file(s).")
