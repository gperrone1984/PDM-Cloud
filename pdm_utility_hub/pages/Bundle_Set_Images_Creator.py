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

# --- Global CSS to hide default navigation and set sidebar width ---
st.markdown(
    """
    <style>
        /* Entire CSS omitted here for brevity — KEEP YOUR ORIGINAL CSS EXACTLY AS IS */
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar link back to HUB
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")

# JS to hide sidebar
st.markdown("""
<script>
/* KEEP YOUR ORIGINAL JAVASCRIPT EXACTLY AS IS */
</script>
""", unsafe_allow_html=True)

# ---------------------- Session State Management ----------------------
if "bundle_creator_session_id" not in st.session_state:
    st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())

# ---------------------- Begin Main App Code ----------------------
session_id = st.session_state["bundle_creator_session_id"]
base_folder = f"Bundle&Set_{session_id}"

def clear_old_data():
    if os.path.exists(base_folder):
        shutil.rmtree(base_folder)
    if os.path.exists(f"Bundle&Set_{session_id}.zip"):
        os.remove(f"Bundle&Set_{session_id}.zip")
    if os.path.exists(f"missing_images_{session_id}.xlsx"):
        os.remove(f"missing_images_{session_id}.xlsx")
    if os.path.exists(f"bundle_list_{session_id}.xlsx"):
        os.remove(f"bundle_list_{session_id}.xlsx")

# Global JPEG Quality
JPEG_QUALITY = 75


# ---------------------- Image Helper Functions ----------------------
async def async_download_image(product_code, extension, session):
    if product_code.startswith(('1', '0')):
        product_code = f"D{product_code}"
    url = f"https://cdn.shop-apotheke.com/images/{product_code}-p{extension}.jpg"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read(), url
    except:
        pass
    return None, None


def trim(im):
    bg = Image.new(im.mode, im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    return im.crop(bbox) if bbox else im


def process_double_bundle_image(image, layout):
    image = trim(image)
    w, h = image.size
    final_layout = (
        "vertical" if (layout.lower() == "automatic" and h < w)
        else layout.lower()
    )
    if final_layout == "horizontal":
        merged = Image.new("RGB", (w * 2, h), "white")
        merged.paste(image, (0, 0))
        merged.paste(image, (w, 0))
    else:
        merged = Image.new("RGB", (w, h * 2), "white")
        merged.paste(image, (0, 0))
        merged.paste(image, (0, h))
    scale = min(1000 / merged.width, 1000 / merged.height)
    new_size = (int(merged.width * scale), int(merged.height * scale))
    resized = merged.resize(new_size, Image.LANCZOS)
    canvas = Image.new("RGB", (1000, 1000), "white")
    canvas.paste(resized, ((1000 - new_size[0]) // 2, (1000 - new_size[1]) // 2))
    return canvas


def process_triple_bundle_image(image, layout):
    image = trim(image)
    w, h = image.size
    final_layout = (
        "vertical" if (layout.lower() == "automatic" and h < w)
        else layout.lower()
    )
    if final_layout == "horizontal":
        merged = Image.new("RGB", (w * 3, h), "white")
        merged.paste(image, (0, 0))
        merged.paste(image, (w, 0))
        merged.paste(image, (2 * w, 0))
    else:
        merged = Image.new("RGB", (w, h * 3), "white")
        merged.paste(image, (0, 0))
        merged.paste(image, (0, h))
        merged.paste(image, (0, 2 * h))
    scale = min(1000 / merged.width, 1000 / merged.height)
    new_size = (int(merged.width * scale), int(merged.height * scale))
    resized = merged.resize(new_size, Image.LANCZOS)
    canvas = Image.new("RGB", (1000, 1000), "white")
    canvas.paste(resized, ((1000 - new_size[0]) // 2, (1000 - new_size[1]) // 2))
    return canvas


def process_and_save_trimmed_image(image_bytes, dest_path):
    img = Image.open(BytesIO(image_bytes))
    img = trim(img).convert("RGB")
    img.save(dest_path, "JPEG", quality=JPEG_QUALITY)


async def async_get_nl_fr_images(product_code, session):
    tasks = [
        async_download_image(product_code, "1-fr", session),
        async_download_image(product_code, "1-nl", session)
    ]
    res = await asyncio.gather(*tasks)
    out = {}
    if res[0][0]: out["1-fr"] = res[0][0]
    if res[1][0]: out["1-nl"] = res[1][0]
    return out


async def async_get_image_with_fallback(product_code, session):
    fallback_ext = st.session_state.get("fallback_ext", None)

    if fallback_ext == "NL FR":
        imgs = await async_get_nl_fr_images(product_code, session)
        if imgs:
            return imgs, "NL FR"

    tasks = [
        async_download_image(product_code, "1", session),
        async_download_image(product_code, "10", session)
    ]
    res = await asyncio.gather(*tasks)
    for ext, (data, _) in zip(["1", "10"], res):
        if data:
            return data, ext

    if fallback_ext and fallback_ext != "NL FR":
        data, _ = await async_download_image(product_code, fallback_ext, session)
        if data:
            return data, fallback_ext

    return None, None

# ---------------------- NEW WORKER-POOL PROCESSOR (NO FREEZE, HIGH PERFORMANCE) ----------------------

async def process_file_async(uploaded_file, progress_bar=None, layout="horizontal"):
    session_id = st.session_state["bundle_creator_session_id"]
    base_folder = f"Bundle&Set_{session_id}"
    missing_images_excel_path = f"missing_images_{session_id}.xlsx"
    bundle_list_excel_path = f"bundle_list_{session_id}.xlsx"
    JPEG_QUALITY = 75

    # -----------------------------
    # Read + decrypt file
    # -----------------------------
    if "encryption_key" not in st.session_state:
        st.session_state["encryption_key"] = Fernet.generate_key()

    fernet = Fernet(st.session_state["encryption_key"])
    decrypted_bytes = fernet.decrypt(fernet.encrypt(uploaded_file.read()))
    file_buffer = BytesIO(decrypted_bytes)

    try:
        if uploaded_file.name.lower().endswith(".xlsx"):
            df = pd.read_excel(file_buffer, dtype=str)
        else:
            df = pd.read_csv(file_buffer, sep=";", dtype=str)
    except Exception as e:
        st.error(f"Error reading uploaded file: {e}")
        return None, None, None, None

    required_cols = {"sku", "pzns_in_set"}
    if not required_cols.issubset(df.columns):
        st.error(f"Missing required columns: {required_cols - set(df.columns)}")
        return None, None, None, None

    df.dropna(subset=["sku", "pzns_in_set"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    if df.empty:
        st.error("File has no valid data.")
        return None, None, None, None

    total_bundles = len(df)
    st.write(f"Loaded {total_bundles} bundles.")

    os.makedirs(base_folder, exist_ok=True)
    mixed_folder = os.path.join(base_folder, "mixed_sets")

    # -----------------------------
    # Worker pool settings
    # -----------------------------
    WORKERS = 20
    connector = aiohttp.TCPConnector(limit=80)
    queue = asyncio.Queue()

    # -----------------------------
    # Put all bundles in queue
    # -----------------------------
    for _, row in df.iterrows():
        queue.put_nowait(row)

    missing_list = []
    bundle_list = []

    processed_count = 0

    # -----------------------------
    # Worker logic
    # -----------------------------
    async def worker(worker_id, session):
        nonlocal processed_count

        while True:
            row = await queue.get()
            if row is None:
                queue.task_done()
                break

            bundle_code = str(row["sku"]).strip()
            pzns_str = str(row["pzns_in_set"]).strip()
            product_codes = [p.strip() for p in pzns_str.split(",") if p.strip()]

            if not product_codes:
                missing_list.append((bundle_code, "No valid product codes"))
                queue.task_done()
                continue

            num_products = len(product_codes)
            uniform = len(set(product_codes)) == 1
            bundle_cross_country = False
            sku_errors = []

            # ======================================
            # UNIFORM SET
            # ======================================
            if uniform:
                p_code = product_codes[0]
                result, used_ext = await async_get_image_with_fallback(p_code, session)

                # Multiple languages (NL/FR)
                if used_ext == "NL FR" and isinstance(result, dict):

                    bundle_cross_country = True
                    out_folder = os.path.join(base_folder, "cross-country")
                    os.makedirs(out_folder, exist_ok=True)

                    processed_langs = []

                    for lang, img_bytes in result.items():

                        suffix = "-fr-h1" if lang == "1-fr" else "-nl-h1"

                        try:
                            img = await asyncio.to_thread(Image.open, BytesIO(img_bytes))

                            if num_products == 2:
                                img = await asyncio.to_thread(process_double_bundle_image, img, layout)
                            elif num_products == 3:
                                img = await asyncio.to_thread(process_triple_bundle_image, img, layout)

                            out_path = os.path.join(out_folder, f"{bundle_code}{suffix}.jpg")
                            await asyncio.to_thread(img.save, out_path, "JPEG", quality=JPEG_QUALITY)
                            processed_langs.append(lang)

                        except Exception as e:
                            sku_errors.append(f"{p_code} ({lang} failed)")

                    if "1-fr" not in processed_langs and "1-nl" in processed_langs:
                        dup = Image.open(BytesIO(result["1-nl"]))
                        out_path = os.path.join(out_folder, f"{bundle_code}-fr-h1.jpg")
                        dup.save(out_path, "JPEG", quality=JPEG_QUALITY)

                    if "1-nl" not in processed_langs and "1-fr" in processed_langs:
                        dup = Image.open(BytesIO(result["1-fr"]))
                        out_path = os.path.join(out_folder, f"{bundle_code}-nl-h1.jpg")
                        dup.save(out_path, "JPEG", quality=JPEG_QUALITY)

                # Single image
                elif result:
                    img = await asyncio.to_thread(Image.open, BytesIO(result))

                    if num_products == 2:
                        img = await asyncio.to_thread(process_double_bundle_image, img, layout)
                    elif num_products == 3:
                        img = await asyncio.to_thread(process_triple_bundle_image, img, layout)

                    out_folder = base_folder
                    if used_ext in ["1-fr", "1-de", "1-nl"]:
                        out_folder = os.path.join(base_folder, "cross-country")
                        os.makedirs(out_folder, exist_ok=True)
                        bundle_cross_country = True

                    out_path = os.path.join(out_folder, f"{bundle_code}-h1.jpg")
                    await asyncio.to_thread(img.save, out_path, "JPEG", quality=JPEG_QUALITY)

                else:
                    sku_errors.append(p_code)

            # ======================================
            # MIXED SET
            # ======================================
            else:
                bundle_folder = os.path.join(mixed_folder, bundle_code)
                os.makedirs(bundle_folder, exist_ok=True)
                is_cross = False

                for p_code in product_codes:
                    result, used_ext = await async_get_image_with_fallback(p_code, session)

                    if not result:
                        sku_errors.append(p_code)
                        continue

                    if used_ext == "NL FR" and isinstance(result, dict):
                        is_cross = True
                        out_folder = os.path.join(bundle_folder, "cross-country")
                        os.makedirs(out_folder, exist_ok=True)

                        processed_langs = []
                        for lang, img_bytes in result.items():

                            suffix = "-fr-h1" if lang == "1-fr" else "-nl-h1"
                            out_path = os.path.join(out_folder, f"{p_code}{suffix}.jpg")

                            await asyncio.to_thread(process_and_save_trimmed_image, img_bytes, out_path)
                            processed_langs.append(lang)

                        if "1-fr" not in processed_langs and "1-nl" in processed_langs:
                            out_path = os.path.join(out_folder, f"{p_code}-fr-h1.jpg")
                            await asyncio.to_thread(process_and_save_trimmed_image, result["1-nl"], out_path)

                        if "1-nl" not in processed_langs and "1-fr" in processed_langs:
                            out_path = os.path.join(out_folder, f"{p_code}-nl-h1.jpg")
                            await asyncio.to_thread(process_and_save_trimmed_image, result["1-fr"], out_path)

                    else:
                        out_folder = bundle_folder
                        if used_ext in ["1-fr", "1-de", "1-nl"]:
                            is_cross = True
                            out_folder = os.path.join(bundle_folder, "cross-country")
                            os.makedirs(out_folder, exist_ok=True)

                        suffix = f"-p{used_ext}" if used_ext else "-h1"
                        out_path = os.path.join(out_folder, f"{p_code}{suffix}.jpg")
                        await asyncio.to_thread(process_and_save_trimmed_image, result, out_path)

                bundle_cross_country = is_cross

            # ==========================
            # RECORD ERRORS & BUNDLE LIST
            # ==========================
            if sku_errors:
                missing_list.append((bundle_code, ", ".join(sku_errors)))

            bundle_list.append([
                bundle_code,
                ", ".join(product_codes),
                "bundle of " + str(num_products) if uniform else "mixed",
                "Yes" if bundle_cross_country else "No"
            ])

            # ==========================
            # UPDATE PROGRESS (every 20)
            # ==========================
            processed_count += 1

            if processed_count % 20 == 0 or processed_count == total_bundles:
                progress_bar.progress(
                    processed_count / total_bundles,
                    text=f"Processed {processed_count}/{total_bundles} bundles"
                )

            queue.task_done()

    # -----------------------------
    # RUN WORKER POOL
    # -----------------------------
    async with aiohttp.ClientSession(connector=connector) as session:
        workers = [
            asyncio.create_task(worker(i, session))
            for i in range(WORKERS)
        ]

        await queue.join()

        for _ in range(WORKERS):
            queue.put_nowait(None)

        await asyncio.gather(*workers)

    # ==========================================================
    # REPORTS (Excel)
    # ==========================================================
    missing_df = pd.DataFrame(missing_list, columns=["PZN Bundle", "PZN with image missing"])
    missing_data = None
    if not missing_df.empty:
        missing_df = missing_df.groupby("PZN Bundle", as_index=False).agg({
            "PZN with image missing": lambda x: ", ".join(sorted(set(x)))
        })
        missing_df.to_excel(missing_images_excel_path, index=False)
        missing_data = open(missing_images_excel_path, "rb").read()

    bundle_df = pd.DataFrame(bundle_list, columns=["sku", "pzns_in_set", "bundle type", "cross-country"])
    bundle_df.to_excel(bundle_list_excel_path, index=False)
    bundle_data = open(bundle_list_excel_path, "rb").read()

    # ==========================================================
    # ZIP FINAL
    # ==========================================================
    zip_bytes = None
    if os.path.exists(base_folder) and any(os.scandir(base_folder)):
        temp_root = f"BundleSet_temp_{session_id}"
        if os.path.exists(temp_root):
            shutil.rmtree(temp_root)
        os.makedirs(temp_root, exist_ok=True)

        copy_path = os.path.join(temp_root, "Bundle&Set")
        shutil.copytree(base_folder, copy_path)

        zip_name = f"BundleSet_{session_id}"
        shutil.make_archive(zip_name, "zip", temp_root)

        zip_bytes = open(f"{zip_name}.zip", "rb").read()
        os.remove(f"{zip_name}.zip")
        shutil.rmtree(temp_root)

    return zip_bytes, missing_data, missing_df, bundle_data

# ---------------------- End of Function Definitions ----------------------

st.title("PDM Bundle&Set Image Creator")

st.markdown(
    """
    **How to use:**

    1. Create a **Quick Report** in **Akeneo** containing the list of products.
    2. Select the following options:
       - File Type: **CSV** or **Excel**
       - All Attributes or Grid Context (for Grid Context, select ID and PZN included in the set)
       - **With Codes**
       - **Without Media**
    3. Select **language** for fallback images (if needed).
    4. Select **layout** for double/triple bundles.
    5. Click **Process File** to start.
    6. Download your ZIP and reports.
    7. Before starting a new job, always click **Clear Cache and Reset Data**.
    """
)

# ------------------------------------------------------
# CLEAR CACHE BUTTON (MAIN AREA)
# ------------------------------------------------------
if st.button("🧹 Clear Cache and Reset Data"):

    keys_to_remove = [
        "bundle_creator_session_id",
        "encryption_key",
        "fallback_ext",
        "zip_data",
        "bundle_list_data",
        "missing_images_data",
        "missing_images_df",
        "processing_complete_bundle",
        "file_uploader",
        "preview_pzn_bundle",
        "sidebar_ext_bundle"
    ]

    for key in keys_to_remove:
        st.session_state.pop(key, None)

    st.cache_data.clear()
    st.cache_resource.clear()

    try:
        clear_old_data()
    except Exception as e:
        st.warning(f"Error clearing old data: {e}")

    st.success("Cache cleared. Ready for a new task.")
    st.session_state["bundle_creator_session_id"] = str(uuid.uuid4())
    time.sleep(1)
    st.rerun()

# ------------------------------------------------------
# SIDEBAR INFO
# ------------------------------------------------------
st.sidebar.header("What This App Does")
st.sidebar.markdown(
    """
    - Automated **Bundle & Set creation**
    - **Language selection** (FR, DE, NL FR)
    - **Double/triple** bundle creation
    - **Trim & resize** logic
    - **Cross-country handling**
    - Automatic naming (-h1, -fr-h1, -nl-h1…)
    - Error reporting (missing images)
    - ZIP packaging
    - Interactive **image preview**
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------
# SIDEBAR — IMAGE PREVIEW
# ------------------------------------------------------
st.sidebar.header("Product Image Preview")

product_code_preview = st.sidebar.text_input(
    "Enter Product Code:",
    key="preview_pzn_bundle"
)

selected_extension = st.sidebar.selectbox(
    "Select Image Extension:",
    ["1-fr", "1-nl", "1-de", "1"] + [str(i) for i in range(2, 19)],
    key="sidebar_ext_bundle"
)

with st.sidebar:
    col_button, col_spinner = st.columns([2, 1])
    show_image = col_button.button("Show Image", key="show_preview_bundle")
    spinner_placeholder = col_spinner.empty()

if show_image and product_code_preview:

    with spinner_placeholder:
        with st.spinner("Fetching image..."):

            code = product_code_preview.strip()
            if code.startswith(("1", "0")):
                code = f"D{code}"

            preview_url = f"https://cdn.shop-apotheke.com/images/{code}-p{selected_extension}.jpg"
            image_data = None

            try:
                import requests
                res = requests.get(preview_url, timeout=10)
                if res.status_code == 200:
                    image_data = res.content
                fetch_status = res.status_code
            except Exception as e:
                st.sidebar.error(f"Network error: {e}")
                fetch_status = None

    if image_data:
        try:
            img = Image.open(BytesIO(image_data))
            st.sidebar.image(img, caption=f"PZN {product_code_preview}", use_container_width=True)
            st.sidebar.download_button(
                "Download Image",
                data=image_data,
                file_name=f"{product_code_preview}-p{selected_extension}.jpg",
                mime="image/jpeg"
            )
        except Exception as e:
            st.sidebar.error(f"Display error: {e}")

    elif fetch_status == 404:
        st.sidebar.warning(f"No image found for {product_code_preview} (404).")
    elif fetch_status is not None:
        st.sidebar.error(f"Failed with status {fetch_status}.")

# ------------------------------------------------------
# MAIN FILE UPLOAD AREA
# ------------------------------------------------------
uploaded_file = st.file_uploader("**Upload CSV or Excel File**", type=["csv", "xlsx"], key="file_uploader")

if uploaded_file is not None:

    col1, col2 = st.columns(2)

    with col1:
        fallback_language = st.selectbox(
            "**Choose language fallback (if needed):**",
            ["None", "FR", "DE", "NL FR"],
            key="lang_select_bundle"
        )

    with col2:
        layout_choice = st.selectbox(
            "**Choose bundle layout:**",
            ["Automatic", "Horizontal", "Vertical"],
            key="layout_select_bundle"
        )

    # Save fallback
    if fallback_language == "NL FR":
        st.session_state["fallback_ext"] = "NL FR"
    elif fallback_language != "None":
        st.session_state["fallback_ext"] = f"1-{fallback_language.lower()}"
    else:
        st.session_state.pop("fallback_ext", None)

    # ------------------------------------------------------
    # PROCESS BUTTON
    # ------------------------------------------------------
    if st.button("Process File", key="process_csv_bundle"):

        start_time = time.time()
        progress_bar = st.progress(0, text="Starting...")

        st.session_state["zip_data"] = None
        st.session_state["bundle_list_data"] = None
        st.session_state["missing_images_data"] = None
        st.session_state["missing_images_df"] = None
        st.session_state["processing_complete_bundle"] = False

        try:
            zip_data, missing_images_data, missing_images_df, bundle_list_data = asyncio.run(
                process_file_async(uploaded_file, progress_bar, layout=layout_choice)
            )

            progress_bar.progress(1.0, text="Processing Completed!")

            elapsed = time.time() - start_time
            m, s = divmod(int(elapsed), 60)
            st.success(f"Finished in {m} min {s} sec")

            st.session_state["zip_data"] = zip_data
            st.session_state["bundle_list_data"] = bundle_list_data
            st.session_state["missing_images_data"] = missing_images_data
            st.session_state["missing_images_df"] = missing_images_df
            st.session_state["processing_complete_bundle"] = True

            progress_bar.empty()

        except Exception as e:
            progress_bar.empty()
            st.error(f"Error during processing: {e}")
            import traceback
            st.error(traceback.format_exc())
            st.session_state["processing_complete_bundle"] = False

# ------------------------------------------------------
# RESULTS AREA
# ------------------------------------------------------
if st.session_state.get("processing_complete_bundle", False):

    st.markdown("---")

    # ZIP download
    if st.session_state.get("zip_data"):
        st.download_button(
            label="Download Bundle Images (ZIP)",
            data=st.session_state["zip_data"],
            file_name=f"BundleSet_{session_id}.zip",
            mime="application/zip"
        )
    else:
        st.info("No ZIP file was generated.")

    # Bundle List report
    if st.session_state.get("bundle_list_data"):
        st.download_button(
            "Download Bundle List (Excel)",
            data=st.session_state["bundle_list_data"],
            file_name=f"bundle_list_{session_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No bundle list report.")

    # Missing images report
    missing_df = st.session_state.get("missing_images_df")

    if missing_df is not None:
        if not missing_df.empty:
            st.markdown("---")
            st.warning(f"{len(missing_df)} bundles with missing images:")
            st.dataframe(missing_df)

            if st.session_state.get("missing_images_data"):
                st.download_button(
                    "Download Missing Images Report",
                    data=st.session_state["missing_images_data"],
                    file_name=f"missing_images_{session_id}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.success("No missing images.")
