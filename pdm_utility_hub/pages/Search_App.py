# pages/Search_App.py
import streamlit as st
import pandas as pd
import re
from io import BytesIO

# 1) Page config (MUST be first)
st.set_page_config(
    page_title="Search App",
    page_icon="🔎",
    layout="centered"
)

# 2) Authentication check
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# 3) Global CSS
st.markdown(
    """
    <style>
      [data-testid="stSidebarNav"] { display: none !important; }
      [data-testid="stSidebar"] > div:first-child {
          width: 550px !important;
          min-width: 550px !important;
          max-width: 550px !important;
          background-color: #ecf0f1 !important;
          padding: 10px !important;
      }
      section.main { background-color: #d8dfe6 !important; }
      .main .block-container,
      div[data-testid="stAppViewContainer"] > section > div.block-container {
          background-color: transparent !important;
          padding: 2rem 1rem 1rem 1rem !important;
          border-radius: 0 !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# 4) Sidebar
st.sidebar.page_link(
    "app.py",
    label="**PDM Utility Hub**",
    icon="🏠"
)
st.sidebar.markdown("---")

# 5) Page title & description
st.title("🔎 Search App")
st.write(
    "Upload an Excel file and enter up to ten search terms. "
    "The search will match terms with any spacing or case variations."
)
st.write("Click 'Clear cache and data' to reset inputs, then 'Search and Download' to get your results.")

# 6) Clear cache and data
def clear_all():
    keys = ['uploaded_file'] + [f'term{i}' for i in range(1, 11)] + ['custom_filename']
    for k in keys:
        st.session_state.pop(k, None)

st.button("Clear cache and data", on_click=clear_all)

# 7) Inputs
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"], key='uploaded_file')
term_inputs = []
for i in range(1, 11):
    term = st.text_input(f"Term {i}", key=f'term{i}')
    if term and term.strip():
        term_inputs.append(term.strip())

# Optional: custom filename input
custom_filename = st.text_input(
    "Optional: Enter a custom name for the output Excel file (without extension)",
    value="filtered_results",
    key='custom_filename'
)

# 8) Search & download
progress_placeholder = st.empty()

if st.button("Search and Download"):
    if not uploaded_file:
        st.error("Please upload an Excel file first.")
    elif not term_inputs:
        st.error("Please enter at least one search term.")
    else:
        # build regex pattern allowing any spaces between characters
        patterns = []
        for term in term_inputs:
            compact = re.sub(r"\s+", "", term)
            pattern = r"(?<!\w)" + ''.join([re.escape(c) + r"\s*" for c in compact]) + r"(?!\w)"
            patterns.append(pattern)
        combined = r"(" + r"|".join(patterns) + r")"

        try:
            df = pd.read_excel(uploaded_file, dtype=str)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.stop()

        df_str = df.astype(str).fillna("")

        progress_bar = progress_placeholder.progress(0, text="Processing rows...")
        total_rows = df_str.shape[0]
        matches = []

        for idx, (_, row) in enumerate(df_str.iterrows()):
            row_text = ' '.join(row.values.astype(str))
            if re.search(combined, row_text, flags=re.IGNORECASE):
                matches.append(True)
            else:
                matches.append(False)

            if idx % 100 == 0 or idx == total_rows - 1:
                progress = (idx + 1) / total_rows
                progress_bar.progress(progress, text=f"Processing row {idx + 1} of {total_rows}")

        result = df[pd.Series(matches)]
        progress_placeholder.empty()

        buf = BytesIO()
        result.to_excel(buf, index=False, engine='openpyxl')
        buf.seek(0)

        # sanitize filename
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename.strip()) or "filtered_results"

        st.download_button(
            "Download filtered Excel",
            data=buf,
            file_name=f"{safe_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
