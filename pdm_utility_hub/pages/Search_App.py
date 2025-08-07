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

# 2) Authentication check: redirect to Hub if not logged in
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# 3) Global CSS: hide default nav/sidebar items, match Hub style
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

# 4) Sidebar: Hub button only
st.sidebar.page_link(
    "app.py",
    label="**PDM Utility Hub**",
    icon="🏠"
)
st.sidebar.markdown("---")

# 5) Page title & description
st.title("🔎 Search App")
st.write(
    "Upload an Excel or CSV file and enter up to five search terms. "
    "The search will match terms with any spacing or case variations."
)
st.write("Click 'Clear cache and data' to reset inputs, then 'Search and Download' to get your results.")

# 6) Clear cache and data
def clear_all():
    keys = ['uploaded_file'] + [f'term{i}' for i in range(1,6)]
    for k in keys:
        st.session_state.pop(k, None)

st.button("Clear cache and data", on_click=clear_all)

# 7) Inputs
uploaded_file = st.file_uploader("Choose an Excel or CSV file", type=["xlsx", "xls", "csv"], key='uploaded_file')
term_inputs = []
for i in range(1,6):
    term = st.text_input(f"Term {i}", key=f'term{i}')
    if term and term.strip():
        term_inputs.append(term.strip())

# 8) Search & download
if st.button("Search and Download"):
    if not uploaded_file:
        st.error("Please upload an Excel or CSV file first.")
    elif not term_inputs:
        st.error("Please enter at least one search term.")
    else:
        # build regex pattern: allow any spaces between characters, and enforce full-word matches
        patterns = []
        for term in term_inputs:
            compact = re.sub(r"\s+", "", term)
            pattern = r"(?<!\w)" + ''.join([re.escape(c) + r"\s*" for c in compact]) + r"(?!\w)"
            patterns.append(pattern)
        combined = r"(" + r"|".join(patterns) + r")"

        # try reading the file (Excel or CSV)
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(uploaded_file, dtype=str)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.stop()

        # convert to string and fill NaNs
        df_str = df.astype(str).fillna("")

        # row-wise search: join all cells into a single string per row
        row_text = df_str.apply(lambda row: ' '.join(row.values.astype(str)), axis=1)
        mask = row_text.str.contains(combined, case=False, regex=True, na=False)

        result = df[mask]

        # download
        buf = BytesIO()
        if uploaded_file.name.endswith(".csv"):
            result.to_csv(buf, index=False, encoding='utf-8-sig')
            mime_type = "text/csv"
            file_name = "filtered_results.csv"
        else:
            result.to_excel(buf, index=False, engine='openpyxl')
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            file_name = "filtered_results.xlsx"

        buf.seek(0)
        st.download_button(
            "Download filtered file",
            data=buf,
            file_name=file_name,
            mime=mime_type
        )
