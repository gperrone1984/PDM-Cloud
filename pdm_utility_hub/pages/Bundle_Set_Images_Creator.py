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

# Page configuration (MUST be the first operation)
st.set_page_config(
    page_title="Bundle Creator",
    page_icon="📦",
    layout="centered"
)

# Authentication check
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# Page content

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

def clear_old_data():
    if os.path.exists(base_folder):
        shutil.rmtree(base_folder)
    # Removed old zip_path cleanup as multiple zips will be created
    missing_images_excel_path = f"missing_images_{session_id}.xlsx"
    bundle_list_excel_path = f"bundle_list_{session_id}.xlsx"
    if os.path.exists(missing_images_excel_path):
        os.remove(missing_images_excel_path)
    if os.path.exists(bundle_list_excel_path):
        os.remove(bundle_list_excel_path)
    # Clean up all generated zip files
    for f_name in os.listdir("."):
        if f_name.startswith(f"Bundle&Set_archive_{session_id}_") and f_name.endswith(".zip"):
            os.remove(f_name)

# ---------------------- Helper Functions ----------------------
async def async_download_image(product_code, extension, session):
    if product_code.startswith(("1", "0")):
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

# ---------------------- Main Processing Function ----------------------
async def process_file_async(uploaded_file, progress_bar=None, layout="horizontal"):
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
    
    # Removed os.makedirs(base_folder, exist_ok=True) from here

    mixed_sets_needed = False
    # mixed_folder will be created inside the batch folder
    error_list = []
    bundle_list = []
    total = len(data)
    zip_file_paths = [] # To store paths of all generated zip files

    BATCH_SIZE = 1000
    batch_num = 0

    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        for i in range(0, total, BATCH_SIZE):
            batch_num += 1
            batch_data = data.iloc[i:i + BATCH_SIZE]
            current_batch_folder = os.path.join(base_folder, f"batch_{batch_num}")
            os.makedirs(current_batch_folder, exist_ok=True)
            current_mixed_folder = os.path.join(current_batch_folder, "mixed_sets")

            st.info(f"Processing batch {batch_num} (bundles {i+1} to {min(i+BATCH_SIZE, total)})")

            for j, (_, row) in enumerate(batch_data.iterrows()):
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
                    folder_name = os.path.join(current_batch_folder, folder_name_base)
                    os.makedirs(folder_name, exist_ok=True)

                    result, used_ext = await async_get_image_with_fallback(product_code, session)

                    # --- Uniform Bundle: NL FR dictionary result with duplicate creation if only one exists ---
                    if used_ext == "NL FR" and isinstance(result, dict):
                        bundle_cross_country = True
                        folder_name = os.path.join(current_batch_folder, "cross-country")
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
                                await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=100)
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
                                    await asyncio.to_thread(final_img_dup.save, dup_save_path, "JPEG", quality=100)
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
                                    await asyncio.to_thread(final_img_dup.save, dup_save_path, "JPEG", quality=100)
                                except Exception as e:
                                    st.warning(f"Error duplicating image for missing 1-nl for bundle {bundle_code} (PZN: {product_code}): {e}")
                                    error_list.append((bundle_code, f"{product_code} (dup 1-nl processing error)"))
                        if not processed_lang:
                            error_list.append((bundle_code, f"{product_code} (NL/FR found but failed processing)"))

                    # --- Uniform Bundle: Fallback Single Image ---
                    elif result:
                        if used_ext in ["1-fr", "1-de", "1-nl"]:
                            bundle_cross_country = True
                            folder_name = os.path.join(current_batch_folder, "cross-country")
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
                                suffix_nl = "-nl-h1"
                                suffix_fr = "-fr-h1"
                                save_path_nl = os.path.join(folder_name, f"{bundle_code}{suffix_nl}.jpg")
                                save_path_fr = os.path.join(folder_name, f"{bundle_code}{suffix_fr}.jpg")
                                await asyncio.to_thread(final_img.save, save_path_nl, "JPEG", quality=100)
                                await asyncio.to_thread(final_img.save, save_path_fr, "JPEG", quality=100)
                            else:
                                suffix = "-h1"
                                save_path = os.path.join(folder_name, f"{bundle_code}{suffix}.jpg")
                                await asyncio.to_thread(final_img.save, save_path, "JPEG", quality=100)
                        except Exception as e:
                            st.warning(f"Error processing image for bundle {bundle_code} (PZN: {product_code}, Ext: {used_ext}): {e}")
                            error_list.append((bundle_code, f"{product_code} (Ext: {used_ext} processing error)"))
                    else:
                        error_list.append((bundle_code, product_code))

                else:  # Mixed set
                    mixed_sets_needed = True
                    bundle_folder = os.path.join(current_mixed_folder, bundle_code)
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
                    progress_bar.progress((i + j + 1) / total, text=f"Processing {bundle_code} ({i+j+1}/{total})")
                bundle_list.append([bundle_code, ', '.join(product_codes), bundle_type, "Yes" if bundle_cross_country else "No"])
            
            # After processing each batch, create a zip file for it
            if os.path.exists(current_batch_folder) and any(os.scandir(current_batch_folder)):
                temp_parent_batch = f"Bundle&Set_temp_{session_id}_batch_{batch_num}"
                if os.path.exists(temp_parent_batch): shutil.rmtree(temp_parent_batch)
                os.makedirs(temp_parent_batch, exist_ok=True)
                zip_content_folder_batch = os.path.join(temp_parent_batch, f"Bundle&Set_batch_{batch_num}")
                try:
                    shutil.copytree(current_batch_folder, zip_content_folder_batch)
                except Exception as e:
                    st.error(f"Error copying files for zipping batch {batch_num}: {e}")
                    if os.path.exists(temp_parent_batch): shutil.rmtree(temp_parent_batch)
                    continue # Skip zipping this batch
                
                zip_base_name_batch = f"Bundle&Set_archive_{session_id}_batch_{batch_num}"
                final_zip_path_batch = f"{zip_base_name_batch}.zip"
                try:
                    shutil.make_archive(base_name=zip_base_name_batch, format='zip', root_dir=temp_parent_batch)
                    if os.path.exists(final_zip_path_batch):
                        zip_file_paths.append(final_zip_path_batch) # Store the path
                    else:
                        st.error(f"Failed to create ZIP archive for batch {batch_num} (file not found after creation attempt).")
                except Exception as e:
                    st.error(f"Error during zipping process for batch {batch_num}: {e}")
                finally:
                    if os.path.exists(temp_parent_batch):
                        try:
                            shutil.rmtree(temp_parent_batch)
                        except Exception as e:
                            st.warning(f"Could not remove temporary zip folder {temp_parent_batch}: {e}")
            else:
                st.info(f"No images were saved for batch {batch_num}. Skipping ZIP creation for this batch.")
            
            # Clean up the batch folder after zipping
            if os.path.exists(current_batch_folder):
                try:
                    shutil.rmtree(current_batch_folder)
                except Exception as e:
                    st.warning(f"Could not remove batch folder {current_batch_folder}: {e}")

    # Removed the single zip creation at the end of the function
    # The zip_bytes return will now be a list of paths to the zip files

    if not mixed_sets_needed and os.path.exists(os.path.join(base_folder, "mixed_sets")):
        try:
            shutil.rmtree(os.path.join(base_folder, "mixed_sets"))
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

    # The function now returns a list of zip file paths
    return zip_file_paths, missing_images_data, missing_images_df, bundle_list_data

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
    5. Click **Process CSV** to start the process.
    6. Download the files.
    7. **Before starting a new process, click on Clear Cache and Reset Data.**
    """
)

if st.button("🧹 Clear Cache and Reset Data"):
    keys_to_remove = [
        "bundle_creator_session_id", "encryption_key", "fallback_ext",
        "zip_data", "bundle_list_data", "missing_images_data",
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

# File Uploader
uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx"], key="file_uploader")

# Fallback Extension Selection
fallback_options = ["None", "NL FR", "1-fr", "1-de", "1-nl"]
selected_fallback = st.selectbox("Select Fallback Extension (optional)", fallback_options, key="sidebar_ext_bundle")
st.session_state["fallback_ext"] = selected_fallback if selected_fallback != "None" else None

# Layout Selection
layout_options = ["horizontal", "vertical", "automatic"]
selected_layout = st.selectbox("Select Bundle Image Layout", layout_options)

if uploaded_file is not None:
    if st.button("Process File"):
        st.session_state["processing_complete_bundle"] = False
        st.session_state["zip_file_paths"] = [] # Initialize list to store multiple zip paths
        st.session_state["missing_images_data"] = None
        st.session_state["bundle_list_data"] = None
        st.session_state["missing_images_df"] = None

        progress_text = "Operation in progress. Please wait."
        progress_bar = st.progress(0, text=progress_text)

        zip_file_paths, missing_images_data, missing_images_df, bundle_list_data = asyncio.run(process_file_async(uploaded_file, progress_bar, selected_layout))

        st.session_state["zip_file_paths"] = zip_file_paths # Store the list of paths
        st.session_state["missing_images_data"] = missing_images_data
        st.session_state["bundle_list_data"] = bundle_list_data
        st.session_state["missing_images_df"] = missing_images_df
        st.session_state["processing_complete_bundle"] = True
        progress_bar.empty()
        st.success("Processing complete!")

if st.session_state.get("processing_complete_bundle", False):
    st.subheader("Download Results")

    # Download all generated zip files
    if st.session_state.get("zip_file_paths"):
        for zip_path in st.session_state["zip_file_paths"]:
            try:
                with open(zip_path, "rb") as f_zip:
                    st.download_button(
                        label=f"Download {os.path.basename(zip_path)}",
                        data=f_zip.read(),
                        file_name=os.path.basename(zip_path),
                        mime="application/zip"
                    )
            except Exception as e:
                st.error(f"Error reading zip file {os.path.basename(zip_path)}: {e}")
    else:
        st.info("No zip files were generated.")

    if st.session_state.get("missing_images_data"):
        st.download_button(
            label="Download Missing Images Report",
            data=st.session_state["missing_images_data"],
            file_name=f"missing_images_{session_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if st.session_state.get("bundle_list_data"):
        st.download_button(
            label="Download Bundle List",
            data=st.session_state["bundle_list_data"],
            file_name=f"bundle_list_{session_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if st.session_state.get("missing_images_df") is not None and not st.session_state["missing_images_df"].empty:
        st.subheader("Missing Images Summary")
        st.dataframe(st.session_state["missing_images_df"])

# Placeholder for other app links
st.markdown(
    """
    <div class="app-container">
        <a href="#" class="app-button-placeholder">
            <span class="icon">📊</span>
            <div>
                <div>**Product Data Analyzer**</div>
                <div class="app-description">Analyze product data for consistency and completeness.</div>
            </div>
        </a>
        <a href="#" class="app-button-placeholder">
            <span class="icon">🔗</span>
            <div>
                <div>**URL Checker**</div>
                <div class="app-description">Verify the validity and accessibility of product image URLs.</div>
            </div>
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

# Footer
st.markdown("""---
<div style="text-align: center; font-size: small; color: grey;">
    PDM Utility Hub v1.0.0
</div>
""", unsafe_allow_html=True)




