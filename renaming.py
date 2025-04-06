import streamlit as st
import pandas as pd
import csv
import os
import zipfile
from PIL import Image, ImageOps, ImageChops, UnidentifiedImageError
from io import BytesIO
import tempfile
import uuid
import asyncio
import aiohttp
import requests
import xml.etree.ElementTree as ET
from zeep import Client
from zeep.wsse.username import UsernameToken
from zeep.transports import Transport
from zeep.cache import InMemoryCache
from zeep.plugins import HistoryPlugin

# ---------------------- Custom CSS ----------------------
st.markdown(
    """
    <style>
        .main {background-color: #f9f9f9; }
        h1, h2, h3 {color: #2c3e50; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;}
        .sidebar-title {font-size: 32px; font-weight: bold; color: #2c3e50; margin-bottom: 0px;}
        .sidebar-subtitle {font-size: 18px; color: #2c3e50; margin-top: 10px; margin-bottom: 5px;}
        .sidebar-desc {font-size: 16px; color: #2c3e50; margin-top: 5px; margin-bottom: 20px;}
        .stDownloadButton>button {background-color: #3498db; color: black; font-weight: bold; border: none; padding: 10px 24px; font-size: 16px; border-radius: 4px;}
        .server-select-label {font-size: 20px; font-weight: bold; margin-bottom: 5px;}
        .sidebar .sidebar-content {background-color: #ecf0f1; padding: 10px;}
    </style>
    """,
    unsafe_allow_html=True
)

# Rimuoviamo il login – non è più necessario

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = str(uuid.uuid4())

def get_sku_list(df_sku, manual_text):
    sku_list = []
    if df_sku is not None:
        for col in df_sku.columns:
            if col.lower() == "sku":
                sku_list.extend(df_sku[col].astype(str).tolist())
                break
    if manual_text:
        manual_skus = [line.strip() for line in manual_text.splitlines() if line.strip()]
        sku_list.extend(manual_skus)
    return list(dict.fromkeys(sku_list))

def run():
    st.title("PDM Image Download and Renaming App")
    
    st.sidebar.markdown("<div class='sidebar-title'>PDM Image Download and Renaming App</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-subtitle'>What This App Does</div>", unsafe_allow_html=True)
    st.sidebar.markdown(
        """
        <div class='sidebar-desc'>
            - 📥 Downloads images<br>
            - 🔄 Resizes images to 1000x1000<br>
            - 🏷️ Renames images with a '-h1' suffix
        </div>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.markdown("<div class='server-select-label'>Select Server Country/Image Source</div>", unsafe_allow_html=True)
    server_country = st.sidebar.selectbox("", options=["Switzerland", "Farmadati", "coming soon"], index=0)
    
    if st.button("🧹 Clear Cache and Reset Data"):
        keys_to_remove = ["uploader_key", "session_id", "processing_done", "zip_path", "error_path",
                          "farmadati_zip", "farmadati_errors", "farmadati_ready",
                          "process_images_switzerland", "process_images_farmadati"]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.uploader_key = str(uuid.uuid4())
        st.info("Cache cleared. Please re-upload your file.")
    
    if server_country == "Switzerland":
        st.header("Switzerland Server Image Processing")
        st.markdown(
            """
            :information_source: **How to use:**
            - Create a list of products (CSV/Excel with column 'sku')
            """
        )
        manual_input = st.text_area("Or paste your SKUs here (one per line):", key="manual_input_switzerland")
        search_button = st.empty().button("Search Images", key="process_switzerland")
        if search_button:
            st.session_state.process_images_switzerland = True
        uploaded_file = st.file_uploader("Upload file (Excel or CSV)", type=["xlsx", "csv"], key="switzerland_file")
        
        if st.session_state.get("process_images_switzerland") and not st.session_state.get("processing_done", False):
            # Inserire qui la logica di processing per il server Switzerland (simile a quella implementata in precedenza)
            st.session_state["zip_path"] = "switzerland_images.zip"  # placeholder
            st.session_state["processing_done"] = True
        
        if st.session_state.get("processing_done", False):
            col1, col2 = st.columns(2)
            with col1:
                with open(st.session_state["zip_path"], "rb") as f:
                    st.download_button(
                        "Download Images (ZIP)",
                        data=f,
                        file_name="images.zip",
                        mime="application/zip"
                    )
            with col2:
                st.info("No errors found.")
                
    elif server_country == "Farmadati":
        st.header("Farmadati Server Image Processing")
        st.markdown(
            """
            :information_source: **How to use:**
            - Create a list of products (CSV/Excel with column 'sku')
            """
        )
        manual_input_fd = st.text_area("Or paste your SKUs here (one per line):", key="manual_input_farmadati")
        search_button_fd = st.empty().button("Search Images", key="process_farmadati")
        if search_button_fd:
            st.session_state.process_images_farmadati = True
        farmadati_file = st.file_uploader("Upload file (column 'sku')", type=["xlsx", "csv"], key="farmadati_file")
        
        if st.session_state.get("process_images_farmadati") and not st.session_state.get("farmadati_ready", False):
            # Inserire qui la logica di processing per il server Farmadati (simile a quella implementata in precedenza)
            st.session_state["farmadati_zip"] = BytesIO()  # placeholder
            st.session_state["farmadati_ready"] = True
        
        if st.session_state.get("farmadati_ready"):
            st.download_button(
                "Download Images (ZIP)",
                data=st.session_state["farmadati_zip"],
                file_name="Farmadati_images.zip",
                mime="application/zip"
            )
    elif server_country == "coming soon":
        st.header("coming soon")
        st.stop()

if __name__ == "__main__":
    run()

# Esporta la funzione per l'importazione esterna
renaming_app = run
