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
import zipfile

# =====================
# Global configuration
# =====================
JPEG_QUALITY = 100             # reduce size vs quality=100
ZIP_MAX_FILES = 1000           # max files per ZIP part
ZIP_COMPRESSLEVEL = 9         # strongest compression

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
    /* Set sidebar width to 540px and force it */
    [data-testid="stSidebar"] > div:first-child {
        width: 540px !important;
        min-width: 540px !important;
        max-width: 540px !important;
    }
    /* Hide the auto-generated Streamlit sidebar navigation */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    /* Make the internal container transparent while keeping padding/radius */
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
    /* Base style for app buttons/placeholder (from hub) - Adapted to the theme */
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
    .app-button-link svg, .app-button-placeholder svg,
    .app-button-link .icon, .app-button-placeholder .icon {
         margin-right: 0.6rem;
         flex-shrink: 0;
    }
    .app-button-link > div[data-testid="stText"] > span:before {
        content: "" !important; margin-right: 0 !important;
    }
    .app-button-link {
        cursor: pointer;
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
    .app-button-placeholder .icon {
         font-size: 1.5em;
    }
    .app-description {
        font-size: 0.9em;
        padding: 0 15px;
        text-align: justify;
        width: 90%;
        margin: 0 auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Button to go back to the Hub in the Sidebar ---
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")  # Separator

# ---------------------- Session State Management ----------------------
if "bundle_creator_session_id" not in st.session_state:
    st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())

# ---------------------- Begin Main App Code ----------------------
session_id = st.session_state["bundle_creator_session_id"]
base_folder = f"Bundle&Set_{session_id}"

# ---------------------- Helper: cleanup ----------------------
def clear_old_data():
    """Remove temp folders and any ZIP parts for the current session."""
    # remove working folder
    if os.path.exists(base_folder):
        shutil.rmtree(base_folder)

    # remove single zips (legacy & current)
    legacy_zip_amp = f"Bundle&Set_{session_id}.zip"
    single_zip = f"BundleSet_{session_id}.zip"
    for zp in (legacy_zip_amp, single_zip):
        if os.path.exists(zp):
            try:
                os.remove(zp)
            except Exception:
                pass

    # remove multi-part zips
    for fname in os.listdir("."):
        if fname.startswith(f"BundleSet_{session_id}_") and fname.endswith(".zip"):
            try:
                os.remove(fname)
            except Exception:
                pass

    # remove reports
    for p in (f"missing_images_{session_id}.xlsx", f"bundle_list_{session_id}.xlsx"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

# ---------------------- Image + Network Helpers ----------------------
async def async_download_image(product_code, extension, session):
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
        merged_width = width * 2
        merged_height = height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (width, 0))
    elif chosen_layout == "vertical":
        merged_width = width
        merged_height = height * 2
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (0, height))
    else:
        merged_width = width * 2
        merged_height = height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (width, 0))
    if merged_width == 0 or merged_height == 0:
        scale_factor = 1
    else:
        scale_factor = min(1000 / merged_width, 1000 / merged_height)
    new_size = (int(merged_width * scale_factor), int(merged_height * scale_factor))
    resized_image = merged_image.resize(new_size, Image.LANCZOS)
    final_image = Image.new("RGB", (1000, 1000), (255, 255, 255))
    x_offset = (1000 - new_size[0]) // 2
    y_offset = (1000 - new_size[1]) // 2
    final_image.paste(resized_image, (x_offset, y_offset))
    return final_image

def process_triple_bundle_image(image, layout="horizontal"):
    image = trim(image)
    width, height = image.size
    chosen_layout = "vertical" if (layout.lower() == "automatic" and height < width) else layout.lower()
    if chosen_layout == "horizontal":
        merged_width = width * 3
        merged_height = height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (width, 0))
        merged_image.paste(image, (width * 2, 0))
    elif chosen_layout == "vertical":
        merged_width = width
        merged_height = height * 3
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (0, height))
        merged_image.paste(image, (0, height * 2))
    else:
        merged_width = width * 3
        merged_height = height
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))
        merged_image.paste(image, (0, 0))
        merged_image.paste(image, (width, 0))
        merged_image.paste(image, (width * 2, 0))
    if merged_width == 0 or merged_height == 0:
        scale_factor = 1
    else:
        scale_factor = min(1000 / merged_width, 1000 / merged_height)
    new_size = (int(merged_width * scale_factor), int(merged_height * scale_factor))
    resized_image = merged_image.resize(new_size, Image.LANCZOS)
    final_image = Image.new("RGB", (1000, 1000), (255, 255, 255))
    x_offset = (1000 - new_size[0]) // 2
    y_offset = (1000 - new_size[1]) // 2
    final_image.paste(resized_image, (x_offset, y_offset))
    return final_image

def save_binary_file(path, data):
    with open(path, 'wb') as f:
        f.write(data)

async def async_get_nl_fr_images(product_code, session):
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

async def async_get_image_with_fallback(product_code, session):
    fallback_ext = st.session_state.get("fallback_ext", None)
    if fallback_ext == "NL FR":
        images_dict = await async_get_nl_fr_images(product_code, session)
        if images_dict:
            return images_dict, "NL FR"
    tasks = [async_download_image(product_code, ext, session) for ext in ["1", "10"]]
    results = await asyncio.gather(*tasks)
    for ext, result in zip(["1", "10"], results):
        content, url = result
        if content:
            return content, ext
    if fallback_ext and fallback_ext != "NL FR":
        content, _ = await async_download_image(product_code, fallback_ext, session)
        if content:
            return content, fallback_ext
    return None, None

# ---------------------- ZIP in parts ----------------------
def zip_folder_in_parts(folder: str, session_id: str, max_files_per_zip: int = ZIP_MAX_FILES) -> list[str]:
    """Create multiple ZIP archives from `folder` to avoid a single huge file.
    Returns list of created .zip file paths.
    """
    zip_paths: list[str] = []
    part = 1
    files_in_current = 0
    current_zip_path = f"BundleSet_{session_id}_part{part}.zip"
    zf = zipfile.ZipFile(
        current_zip_path, "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=ZIP_COMPRESSLEVEL,
    )

    try:
        for root, _, files in os.walk(folder):
            for name in files:
                full_path = os.path.join(root, name)
                # keep a stable root inside the zip
                arcname = os.path.join("Bundle&Set", os.path.relpath(full_path, folder))
                zf.write(full_path, arcname=arcname)
                files_in_current += 1

                if files_in_current >= max_files_per_zip:
                    zf.close()
                    zip_paths.append(current_zip_path)
                    part += 1
                    files_in_current = 0
                    current_zip_path = f"BundleSet_{session_id}_part{part}.zip"
                    zf = zipfile.ZipFile(
                        current_zip_path, "w",
                        compression=zipfile.ZIP_DEFLATED,
                        compresslevel=ZIP_COMPRESSLEVEL,
                    )
    finally:
        zf.close()
        # ensure last part is registered
        if not zip_paths or zip_paths[-1] != current_zip_path:
            zip_paths.append(current_zip_path)

    return zip_paths


def zip_folder_single(folder: str, session_id: str) -> str:
    """Create a single ZIP archive from `folder` and return its path."""
    zip_path = f"BundleSet_{session_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=ZIP_COMPRESSLEVEL) as zf:
        for root, _, files in os.walk(folder):
            for name in files:
                full_path = os.path.join(root, name)
                arcname = os.path.join("Bundle&Set", os.path.relpath(full_path, folder))
                zf.write(full_path, arcname=arcname)
    return zip_path

# ---------------------- Main Processing Function ----------------------
async def process_file_async(uploaded_file, progress_bar=None, layout="horizontal", split_every_1000=False):
    session_id = st.session_state["bundle_creator_session_id"]
    base_folder = f"Bundle&Set_{session_id}"
    missing_images_excel_path = f"missing_images_{session_id}.xlsx"
    bundle_list_excel_path = f"bundle_list_{session_id}.xlsx"

    if "encryption_key" not in st.session_state:
        st.session_state["encryption_key"] = Fernet.generate_key()
    key = st.session_state["encryption_key"]
    f = Fernet(key)

    file_bytes = uploaded_file.read()
    encrypted_bytes = f.encrypt(file_bytes)
    decrypted_bytes = f.decrypt(encrypted_bytes)

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

    # reduce concurrency to avoid resource spikes
    connector = aiohttp.TCPConnector(limit=40)
    async with aiohttp.ClientSession(connector=connector) as session:
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

                # --- Uniform Bundle: NL FR dictionary result with duplicate creation if only one exists ---
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
                            await asyncio.to_thread(
                                final_img.save, save_path, "JPEG",
                                quality=JPEG_QUALITY, optimize=True, progressive=True
                            )
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
                                await asyncio.to_thread(
                                    final_img_dup.save, dup_save_path, "JPEG",
                                    quality=JPEG_QUALITY, optimize=True, progressive=True
                                )
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
                                await asyncio.to_thread(
                                    final_img_dup.save, dup_save_path, "JPEG",
                                    quality=JPEG_QUALITY, optimize=True, progressive=True
                                )
                            except Exception as e:
                                st.warning(f"Error duplicating image for missing 1-nl for bundle {bundle_code} (PZN: {product_code}): {e}")
                                error_list.append((bundle_code, f"{product_code} (dup 1-nl processing error)"))
                    if not processed_lang:
                        error_list.append((bundle_code, f"{product_code} (NL/FR found but failed processing)"))

                # --- Uniform Bundle: Fallback Single Image ---
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
                        # When fallback_ext is NL FR, create only the -nl-h1 and -fr-h1 images.
                        if st.session_state.get("fallback_ext") == "NL FR":
                            save_path_nl = os.path.join(folder_name, f"{bundle_code}-nl-h1.jpg")
                            save_path_fr = os.path.join(folder_name, f"{bundle_code}-fr-h1.jpg")
                            await asyncio.to_thread(
                                final_img.save, save_path_nl, "JPEG",
                                quality=JPEG_QUALITY, optimize=True, progressive=True
                            )
                            await asyncio.to_thread(
                                final_img.save, save_path_fr, "JPEG",
                                quality=JPEG_QUALITY, optimize=True, progressive=True
                            )
                        else:
                            save_path = os.path.join(folder_name, f"{bundle_code}-h1.jpg")
                            await asyncio.to_thread(
                                final_img.save, save_path, "JPEG",
                                quality=JPEG_QUALITY, optimize=True, progressive=True
                            )
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

    # ---- ZIP creation (single or multi-part) on disk ----
    zip_paths = []
    if os.path.exists(base_folder) and any(os.scandir(base_folder)):
        try:
            if split_every_1000:
                # split into parts of 1000 files each
                zip_paths = zip_folder_in_parts(base_folder, session_id, 1000)
            else:
                # single zip
                zp = zip_folder_single(base_folder, session_id)
                zip_paths = [zp]
        except Exception as e:
            st.error(f"Error during zipping process: {e}")
    else:
        st.info("Processing complete, but no images were saved to create a ZIP file.")
        try:
            os.rmdir(base_folder)
        except OSError:
            try:
                shutil.rmtree(base_folder)
            except Exception as e:
                st.warning(f"Could not remove base folder {base_folder}: {e}")

    return zip_paths, missing_images_data, missing_images_df, bundle_list_data

# ---------------------- End of Function Definitions ----------------------

st.title("PDM Bundle&Set Image Creator")

st.markdown(
    """
    **How to use:**

    1. Create a **Quick Report** in **Akeneo** containing the list of products.
    2. Select the following options:
       - File Type: **CSV** or **Excel** - All Attributes or Grid Context (for Grid Context, select ID and PZN included in the set) - **With Codes** - **Without Media**
    3. **Choose the language for language specific photos:** (if needed)
    4. **Choose bundle layout:** (Horizontal, Vertical, or Automatic)
    5. Click **Process file** to start the process.
    6. Download the files.
    7. **Before starting a new process, click on Clear Cache and Reset Data.**
    """
)

if st.button("🧹 Clear Cache and Reset Data"):
    keys_to_remove = [
        "bundle_creator_session_id", "encryption_key", "fallback_ext",
        "zip_paths", "bundle_list_data", "missing_images_data",
        "missing_images_df", "processing_complete_bundle",
        "file_uploader", "preview_pzn_bundle", "sidebar_ext_bundle"
    ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    st.cache_data.clear()
    st.cache_resource.clear()
    try:
        clear_old_data()
    except NameError:
        st.warning("Could not execute clear_old_data function (might be expected after state clear).")
    except Exception as e:
        st.warning(f"Error during clear_old_data: {e}")
    st.success("Cache and session data cleared. Ready for a new task.")
    if "bundle_creator_session_id" not in st.session_state:
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
    - ✏️ **Rename images** using the specific bundle&set code (e.g. -h1, -p1-fr, -p1-nl, etc);
    - ❌ **Error Logging:** Missing images are logged in a CSV ;
    - 📥 **Download:** Get a ZIP with all processed images and reports;
    - 🌐 **Interactive Preview:** Preview and download individual product images from the sidebar.
    """, unsafe_allow_html=True
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

uploaded_file = st.file_uploader("**Upload CSV File**", type=["csv", "xlsx"], key="file_uploader")
if uploaded_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        fallback_language = st.selectbox("**Choose the language for language specific photos:**", options=["None", "FR", "DE", "NL FR"], index=0, key="lang_select_bundle")
    with col2:
        layout_choice = st.selectbox("**Choose bundle layout:**", options=["Automatic", "Horizontal", "Vertical"], index=0, key="layout_select_bundle")
    if fallback_language == "NL FR":
        st.session_state["fallback_ext"] = "NL FR"
    elif fallback_language != "None":
        st.session_state["fallback_ext"] = f"1-{fallback_language.lower()}"
    else:
        if "fallback_ext" in st.session_state:
            del st.session_state["fallback_ext"]
    col_btn, col_chk = st.columns([1, 3])
    with col_chk:
        split_zip_1000 = st.checkbox("Create a ZIP file every 1000 products (recommended for large jobs)", value=False, key="split_zip_1000")
    with col_btn:
        if st.button("Process file", key="process_csv_bundle"):
            start_time = time.time()
            progress_bar = st.progress(0, text="Starting processing...")
            st.session_state["zip_paths"] = None
            st.session_state["bundle_list_data"] = None
            st.session_state["missing_images_data"] = None
            st.session_state["missing_images_df"] = None
            st.session_state["processing_complete_bundle"] = False
            try:
                if 'process_file_async' not in globals():
                    st.error("Critical error: Processing function is not defined.")
                    st.stop()
                zip_paths, missing_images_data, missing_images_df, bundle_list_data = asyncio.run(
                    process_file_async(uploaded_file, progress_bar, layout=layout_choice, split_every_1000=split_zip_1000)
                )
                progress_bar.progress(1.0, text="Processing Complete!")
                elapsed_time = time.time() - start_time
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                st.success(f"Processing finished in {minutes}m {seconds}s.")
                st.session_state["zip_paths"] = zip_paths
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
    # Multi-part ZIP downloads
    if st.session_state.get("zip_paths"):
        st.subheader("Download bundle images")
        for idx, zp in enumerate(st.session_state["zip_paths"], start=1):
            try:
                with open(zp, "rb") as fh:
                    st.download_button(
                        label=f"Download ZIP (part {idx})",
                        data=fh,
                        file_name=os.path.basename(zp),
                        mime="application/zip",
                        key=f"dl_zip_bundle_part_{idx}"
                    )
            except Exception as e:
                st.error(f"Cannot open {zp}: {e}")
    else:
        if st.session_state.get("processing_complete_bundle", False):
             st.info("Processing complete, but no ZIP files were generated.")

    if st.session_state.get("bundle_list_data"):
        st.download_button(
            label="Download Bundle List",
            data=st.session_state["bundle_list_data"],
            file_name=f"bundle_list_{session_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_list_bundle_v"
        )
    else:
        if st.session_state.get("processing_complete_bundle", False):
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
