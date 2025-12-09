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

    # --- RESET BUTTON ---
    if st.button("🧹 Clear Cache and Reset Data"):
        keys_to_remove = [
            k for k in st.session_state.keys()
            if k.startswith("renaming_") or k in [
                "uploader_key", "session_id",
                "processing_done", "zip_path", "error_path",
                "farmadati_zip", "farmadati_errors", "farmadati_ready",
                "process_images_switzerland", "process_images_farmadati"
            ]
        ]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.renaming_uploader_key = str(uuid.uuid4())
        st.info("Cache cleared. Please re-upload your file.")
        st.rerun()

    # INPUTS
    manual_input = st.text_area("Or paste your SKUs here (one per line):", key="manual_input_switzerland")
    uploaded_file = st.file_uploader("Upload file (Excel or CSV)", type=["xlsx", "csv"], key=st.session_state.renaming_uploader_key)

    if st.button("Search Images", key="process_switzerland"):
        st.session_state.renaming_start_processing_ch = True
        st.session_state.renaming_processing_done_ch = False
        st.session_state.pop("renaming_zip_path_ch", None)
        st.session_state.pop("renaming_error_path_ch", None)

    # ======================================================
    # ASYNC PROCESSING
    # ======================================================
    if st.session_state.get("renaming_start_processing_ch") and not st.session_state.get("renaming_processing_done_ch", False):
        sku_list = get_sku_list(uploaded_file, manual_input)

        if not sku_list:
            st.warning("Please upload a file or paste some SKUs to process.")
            st.session_state.renaming_start_processing_ch = False

        else:
            st.info(f"Processing {len(sku_list)} SKUs for Switzerland...")
            progress_bar = st.progress(0, text="Starting processing...")

            # ======================================================
            # URL BUILDER
            # ======================================================
            def get_image_url(product_code):
                pharmacode = str(product_code).strip()
                if pharmacode.upper().startswith("CH"):
                    pharmacode = pharmacode[2:]
                return f"https://documedis.hcisolutions.ch/2020-01/api/products/image/PICFRONT3D/Pharmacode/{pharmacode}/F"

            # ======================================================
            # PROCESS IMAGE (CONTROLLO NERO + SAVE)
            # ======================================================
            def process_and_save(original_sku, content, download_folder):
                """Process image and save only if original isn't fully black."""
                try:
                    img = Image.open(BytesIO(content))
                    img = ImageOps.exif_transpose(img)

                    # --- CONTROLLO UNICO: immagine originale nera ---
                    extrema = img.convert("L").getextrema()
                    if extrema == (0, 0):  # completamente nera
                        return False

                    # Resize
                    img.thumbnail((1000, 1000), Image.LANCZOS)

                    # Canvas bianco centrato
                    canvas = Image.new("RGB", (1000, 1000), (255, 255, 255))
                    offset_x = (1000 - img.width) // 2
                    offset_y = (1000 - img.height) // 2
                    canvas.paste(img, (offset_x, offset_y))

                    # Save (quality 75 richiesto)
                    new_filename = f"{original_sku}-h1.jpg"
                    img_path = os.path.join(download_folder, new_filename)
                    canvas.save(img_path, "JPEG", quality=75)

                    return True

                except Exception:
                    return False

            # ======================================================
            # ASYNC FETCH WITH RETRY
            # ======================================================
            async def fetch_with_retry(session, url, retries=3):
                for attempt in range(retries):
                    try:
                        async with session.get(url, timeout=30) as resp:
                            if resp.status == 200:
                                content = await resp.read()
                                if content:
                                    return content
                            await asyncio.sleep(0.5 * (attempt + 1))
                    except:
                        await asyncio.sleep(0.5 * (attempt + 1))
                return None

            async def fetch_and_process_image(session, semaphore, sku, download_folder, error_codes):
                url = get_image_url(sku)

                async with semaphore:
                    content = await fetch_with_retry(session, url, retries=3)
                    if content is None:
                        error_codes.append(sku)
                        return

                    success = await asyncio.to_thread(process_and_save, sku, content, download_folder)
                    if not success:
                        error_codes.append(sku)

            async def run_processing(sku_list, download_folder, progress_bar):
                connector = aiohttp.TCPConnector(limit=20)
                semaphore = asyncio.Semaphore(10)
                error_codes = []

                async with aiohttp.ClientSession(connector=connector) as session:
                    tasks = [
                        fetch_and_process_image(session, semaphore, sku, download_folder, error_codes)
                        for sku in sku_list
                    ]

                    total = len(tasks)
                    completed = 0

                    for f in asyncio.as_completed(tasks):
                        await f
                        completed += 1
                        progress_bar.progress(completed / total)

                progress_bar.progress(1.0)
                return error_codes

            # ======================================================
            # RUN + ZIP + ERROR CSV
            # ======================================================
            with st.spinner("Processing images, please wait..."):
                with tempfile.TemporaryDirectory() as download_folder:

                    error_codes = asyncio.run(
                        run_processing(sku_list, download_folder, progress_bar)
                    )

                    # ZIP
                    if any(os.scandir(download_folder)):
                        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                            zip_path = tmp_zip.name
                        shutil.make_archive(zip_path[:-4], "zip", download_folder)
                        st.session_state["renaming_zip_path_ch"] = zip_path
                    else:
                        st.session_state["renaming_zip_path_ch"] = None

                    # CSV ERROR LIST
                    if error_codes:
                        error_df = pd.DataFrame(sorted(set(error_codes)), columns=["sku"])
                        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8-sig") as tmp_err:
                            error_df.to_csv(tmp_err, index=False, sep=";")
                            st.session_state["renaming_error_path_ch"] = tmp_err.name
                    else:
                        st.session_state["renaming_error_path_ch"] = None

            st.session_state["renaming_processing_done_ch"] = True
            st.session_state.renaming_start_processing_ch = False

    # ======================================================
    # DOWNLOAD OUTPUTS
    # ======================================================
    if st.session_state.get("renaming_processing_done_ch", False):
        st.markdown("---")
        col1, col2 = st.columns(2)

        # ZIP
        with col1:
            zip_path = st.session_state.get("renaming_zip_path_ch")
            if zip_path and os.path.exists(zip_path):
                with open(zip_path, "rb") as f:
                    st.download_button(
                        label="Download Images",
                        data=f,
                        file_name="switzerland_images.zip",
                        mime="application/zip"
                    )
            else:
                st.info("No images processed.")

        # ERRORS CSV
        with col2:
            error_path = st.session_state.get("renaming_error_path_ch")
            if error_path and os.path.exists(error_path):
                with open(error_path, "rb") as f:
                    st.download_button(
                        label="Download Missing Image List",
                        data=f,
                        file_name="errors_switzerland.csv",
                        mime="text/csv"
                    )
            else:
                st.info("No errors found.")
