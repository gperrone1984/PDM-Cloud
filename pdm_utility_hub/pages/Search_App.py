# pages/Search_App.py
import streamlit as st
import pandas as pd
import re
import unicodedata
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
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")

# 5) Page title & description
st.title("🔎 Search App")
st.write(
    "Upload an Excel file and enter up to ten search terms. "
    "The search matches any spacing/case variations and ignores accents (e.g., caffè/caffé/caffe)."
)
st.write("Click 'Clear cache and data' to reset inputs, then 'Search and Download' to get your results.")

# ---- helpers ----
def clear_all():
    keys = ['uploaded_file'] + [f'term{i}' for i in range(1, 11)] + ['custom_filename']
    for k in keys:
        st.session_state.pop(k, None)

def strip_accents(s: str) -> str:
    """Remove diacritics (è/é -> e) for accent-insensitive matching."""
    if not isinstance(s, str):
        s = str(s)
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if not unicodedata.combining(ch))

def build_spacing_pattern(term_no_accents: str) -> str:
    """
    Build a regex that allows arbitrary spaces between characters and enforces word boundaries.
    Example: 'caffe' -> (?<!\w)c\s*a\s*f\s*f\s*e(?!\w)
    """
    return r"(?<!\w)" + ''.join([re.escape(c) + r"\s*" for c in term_no_accents]) + r"(?!\w)"

st.button("Clear cache and data", on_click=clear_all)

# 7) Inputs
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"], key='uploaded_file')
term_inputs = []
for i in range(1, 10 + 1):
    term = st.text_input(f"Term {i}", key=f'term{i}')
    if term and term.strip():
        term_inputs.append(term.strip())

# Optional: custom filename input
st.markdown("**Optional: Enter a custom name for the output Excel file (without extension)**")
custom_filename = st.text_input("", value="filtered_results", key='custom_filename')

# 8) Search & download
progress_placeholder = st.empty()

if st.button("Search and Download"):
    if not uploaded_file:
        st.error("Please upload an Excel file first.")
    elif not term_inputs:
        st.error("Please enter at least one search term.")
    else:
        # Read Excel
        try:
            df = pd.read_excel(uploaded_file, dtype=str)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.stop()

        # Prepare data as string and build one big text per row
        df_str = df.astype(str).fillna("")
        row_texts = df_str.apply(lambda r: ' '.join(r.values.astype(str)), axis=1)
        row_texts_noacc = row_texts.map(strip_accents)

        # --- Build patterns (accent-insensitive + spacing-insensitive) ---
        term_noacc = [strip_accents(t) for t in term_inputs]
        term_compact = [re.sub(r"\s+", "", t) for t in term_noacc]
        pattern_strings = [build_spacing_pattern(t) for t in term_compact]
        compiled_patterns = [re.compile(p, flags=re.IGNORECASE) for p in pattern_strings]

        # ---- Iterate rows with progress, collect matches, per-term counts, and matched terms per row ----
        progress_bar = progress_placeholder.progress(0, text="Processing rows...")
        total_rows = len(row_texts_noacc)
        matches_any = []
        per_term_counts = [0] * len(compiled_patterns)
        matched_terms_per_row = []

        for idx, text_noacc in enumerate(row_texts_noacc):
            any_match = False
            row_hits = []
            for j, pat in enumerate(compiled_patterns):
                if pat.search(text_noacc):
                    per_term_counts[j] += 1
                    any_match = True
                    # use the original input term label
                    row_hits.append(term_inputs[j])
            matches_any.append(any_match)
            matched_terms_per_row.append(row_hits)

            if idx % 100 == 0 or idx == total_rows - 1:
                progress = (idx + 1) / total_rows
                progress_bar.progress(progress, text=f"Processing row {idx + 1} of {total_rows}")

        progress_placeholder.empty()

        # Filter the original df by rows that matched at least one term
        mask = pd.Series(matches_any, index=df.index)
        result = df[mask].copy()

        # Add "Matched terms" column (semicolon-separated), aligned by index
        matched_series = pd.Series([';'.join(hits) for hits in matched_terms_per_row], index=df.index)
        result['Matched terms'] = matched_series.loc[result.index].values

        # Optional: move "Matched terms" as the first column
        cols = ['Matched terms'] + [c for c in result.columns if c != 'Matched terms']
        result = result[cols]

        # Build report df: one row per original input term, with matched row count
        report_df = pd.DataFrame({
            "Term": term_inputs,
            "Rows matched": per_term_counts
        })

        # Show quick summary in app
        st.success(f"Matched {result.shape[0]} rows across {len(term_inputs)} terms.")
        st.dataframe(report_df, use_container_width=True)

        # Write Excel with two sheets: Filtered + Report
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            result.to_excel(writer, sheet_name="Filtered", index=False)
            report_df.to_excel(writer, sheet_name="Report", index=False)
        buf.seek(0)

        # sanitize filename
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename.strip()) or "filtered_results"

        st.download_button(
            "Download filtered Excel + report",
            data=buf,
            file_name=f"{safe_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
