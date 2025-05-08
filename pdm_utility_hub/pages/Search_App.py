# pages/Search_App.py
import streamlit as st
import pandas as pd
import re
from io import BytesIO

# 1) Page config
st.set_page_config(
    page_title="Search App",
    page_icon="🔎",
    layout="centered",
)

# 2) Auth guard
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.error("You must be logged in to view this page.")
    st.stop()

# 3) Custom CSS to hide default nav entries
st.markdown(
    """
    <style>
      /* Hide main sidebar nav entries */
      [data-testid="stSidebarNav"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# 4) Sidebar: only back icon
st.sidebar.page_link("app.py", label="🏠 **PDM Utility Hub**

")

# 5) Title and instructions
st.title("🔎 Search App")
st.write("Upload an Excel file and enter up to five search terms. Click 'Search and Download' to get your filtered results as an Excel file.")

# 6) Inputs
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
terms_patterns = []
for i in range(1, 6):
    term_input = st.text_input(f"Term {i}")
    if term_input.strip():
        # Remove all spaces, then allow flexible whitespace between all characters
        clean = re.sub(r"\s+", "", term_input)
        # Build pattern: each char followed by optional whitespace
        chars_pattern = "".join([re.escape(c) + r"\s*" for c in clean])
        terms_patterns.append(chars_pattern)

# 7) Search and download button
if st.button("Search and Download"):
    if not uploaded_file:
        st.error("Please upload an Excel file first.")
    elif not terms_patterns:
        st.error("Please enter at least one search term.")
    else:
        # Combine term patterns into one regex
        pattern = r"(" + r"|".join(terms_patterns) + r")"
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
            st.stop()

        if 'Long description' not in df.columns:
            st.error("No column named 'Long description' found.")
            st.stop()

        # Filter rows by regex (case-insensitive)
        mask = df['Long description'].astype(str).str.contains(pattern, case=False, regex=True, na=False)
        filtered = df[mask]

        # Prepare and offer download
        towrite = BytesIO()
        filtered.to_excel(towrite, index=False, engine='openpyxl')
        towrite.seek(0)
        st.download_button(
            "Download filtered Excel",
            data=towrite,
            file_name="filtered_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
