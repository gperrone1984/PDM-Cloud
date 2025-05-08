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

# 4) Sidebar: only back icon with bold label
st.sidebar.page_link(
    "app",  # refers to the root app.py page
    label="🏠 **PDM Utility Hub**",
    icon=None
)

# 5) Title and instructions
st.title("🔎 Search App")
st.write(
    "Upload an Excel file and enter up to five search terms. "
    "The search will match terms with any spacing or case variations."
)
st.write("Use the Clear cache and data button below to reset all inputs.")

# 6) Clear cache and data button
def clear_cache_and_data():
    keys_to_clear = ['uploaded_file'] + [f'term{i}' for i in range(1,6)]
    for key in keys_to_clear:
        st.session_state.pop(key, None)

st.button("Clear cache and data", on_click=clear_cache_and_data)

# 7) Inputs
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"], key='uploaded_file')
term_inputs = []
for i in range(1, 6):
    term = st.text_input(f"Term {i}", key=f'term{i}')
    if term and term.strip():
        term_inputs.append(term.strip())

# 8) Search and download button
if st.button("Search and Download"):
    if not uploaded_file:
        st.error("Please upload an Excel file first.")
    elif not term_inputs:
        st.error("Please enter at least one search term.")
    else:
        # Build patterns allowing flexible spacing
        patterns = []
        for term in term_inputs:
            compact = re.sub(r"\s+", "", term)
            # allow any spaces between all characters
            patterns.append(''.join([re.escape(ch) + r"\s*" for ch in compact]))
        combined_pattern = r"(" + r"|".join(patterns) + r")"

        # Read Excel file
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
            st.stop()

        # Apply search across all columns
        df_str = df.astype(str)
        mask_df = df_str.apply(
            lambda col: col.str.contains(combined_pattern, case=False, regex=True, na=False)
        )
        mask = mask_df.any(axis=1)
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
