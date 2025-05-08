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
st.sidebar.page_link("app.py", label="🏠 **PDM Utility Hub**")

# 5) Title and instructions
st.title("🔎 Search App")
st.write(
    "Upload an Excel file and enter up to five search terms. "
    "The search will match terms with any spacing or case variations. "
    "Click 'Search and Download' to get your filtered results as an Excel file."
)

# 6) Inputs
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
term_inputs = []
for i in range(1, 6):
    term = st.text_input(f"Term {i}")
    if term and term.strip():
        term_inputs.append(term.strip())

# 7) Button logic
if st.button("Search and Download"):
    if not uploaded_file:
        st.error("Please upload an Excel file first.")
    elif not term_inputs:
        st.error("Please enter at least one search term.")
    else:
        # Build patterns allowing flexible spacing between all characters
        patterns = []
        for term in term_inputs:
            # remove existing spaces
            compact = re.sub(r"\s+", "", term)
            # add \s* after each char
            char_patterns = ''.join([re.escape(ch) + r"\s*" for ch in compact])
            patterns.append(char_patterns)
        combined_pattern = r"(" + r"|".join(patterns) + r")"

        # Read Excel
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
            st.stop()

        # Validate column
        if 'Long description' not in df.columns:
            st.error("No column named 'Long description' found.")
            st.stop()

        # Filter rows
        mask = df['Long description'].astype(str).str.contains(
            combined_pattern, case=False, regex=True, na=False
        )
        filtered = df[mask]

        # Prepare download
        output = BytesIO()
        filtered.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        st.download_button(
            label="Download filtered Excel",
            data=output,
            file_name="filtered_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
