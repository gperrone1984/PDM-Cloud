import streamlit as st
import pandas as pd
import re
import unicodedata
from io import BytesIO, StringIO

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Search App",
    page_icon="🔎",
    layout="centered"
)

# -------------------- AUTH CHECK --------------------
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# -------------------- GLOBAL CSS --------------------
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

# -------------------- SIDEBAR --------------------
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")

# -------------------- TITLE & INFO --------------------
st.title("🔎 Search App")
st.write(
    "Upload an Excel file and enter up to ten search terms. "
    "The search matches any spacing/case variations and ignores accents (e.g., caffè/caffé/caffe)."
)
st.write("Click 'Clear cache and data' to reset inputs, then 'Search and Download' to get your results.")

# -------------------- HELPERS --------------------
def clear_all():
    keys = ['uploaded_file'] + [f'term{i}' for i in range(1, 11)] + ['custom_filename']
    for k in keys:
        st.session_state.pop(k, None)

def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if not unicodedata.combining(ch))

def build_spacing_pattern(term_no_accents: str) -> str:
    return r"(?<!\w)" + ''.join([re.escape(c) + r"\s*" for c in term_no_accents]) + r"(?!\w)"

def excel_to_csv_buffer(excel_file) -> StringIO:
    """Converte l'Excel caricato in CSV (in memoria, senza scrivere su disco)."""
    df = pd.read_excel(excel_file, dtype=str)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer

st.button("Clear cache and data", on_click=clear_all)

# -------------------- INPUTS --------------------
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"], key='uploaded_file')
term_inputs = []
for i in range(1, 11):
    term = st.text_input(f"Term {i}", key=f'term{i}')
    if term and term.strip():
        term_inputs.append(term.strip())

st.markdown("**Optional: Enter a custom name for the output Excel file (without extension)**")
custom_filename = st.text_input("", value="filtered_results", key='custom_filename')

progress_placeholder = st.empty()

# -------------------- MAIN PROCESS --------------------
if st.button("Search and Download"):
    if not uploaded_file:
        st.error("Please upload an Excel file first.")
    elif not term_inputs:
        st.error("Please enter at least one search term.")
    else:
        # --- PREPARE REGEX PATTERNS ---
        term_noacc = [strip_accents(t) for t in term_inputs]
        term_compact = [re.sub(r"\s+", "", t) for t in term_noacc]
        pattern_strings = [build_spacing_pattern(t) for t in term_compact]
        compiled_patterns = [re.compile(p, flags=re.IGNORECASE) for p in pattern_strings]
        per_term_counts = [0] * len(compiled_patterns)

        # --- CONVERT EXCEL TO CSV BUFFER ---
        try:
            st.info("Converting Excel to CSV for chunk processing... (this may take a minute)")
            csv_buffer = excel_to_csv_buffer(uploaded_file)
        except Exception as e:
            st.error(f"Error converting Excel file: {e}")
            st.stop()

        # --- READ CSV IN CHUNKS ---
        chunksize = 5000
        matches = []
        total_rows = 0
        matched_rows_total = 0

        progress_bar = progress_placeholder.progress(0, text="Processing CSV in chunks...")

        for chunk_idx, chunk in enumerate(pd.read_csv(csv_buffer, dtype=str, chunksize=chunksize)):
            total_rows += len(chunk)
            chunk = chunk.fillna("")
            row_texts = chunk.apply(lambda r: ' '.join(r.values.astype(str)), axis=1)
            row_texts_noacc = row_texts.map(strip_accents)

            mask = []
            matched_terms = []
            for text_noacc in row_texts_noacc:
                row_hits = []
                any_match = False
                for j, pat in enumerate(compiled_patterns):
                    if pat.search(text_noacc):
                        per_term_counts[j] += 1
                        any_match = True
                        row_hits.append(term_inputs[j])
                mask.append(any_match)
                matched_terms.append(';'.join(row_hits))

            filtered_chunk = chunk[mask].copy()
            if not filtered_chunk.empty:
                filtered_chunk['Matched terms'] = [m for m, keep in zip(matched_terms, mask) if keep]
                matches.append(filtered_chunk)
                matched_rows_total += len(filtered_chunk)

            progress_bar.progress(
                text=f"Processed {total_rows} rows...",
                value=min(1.0, (chunk_idx + 1) * chunksize / (total_rows + 1))
            )

        progress_placeholder.empty()

        # --- COMBINE ALL MATCHES ---
        if matches:
            result = pd.concat(matches, ignore_index=True)
        else:
            result = pd.DataFrame()

        # --- BUILD REPORT ---
        report_df = pd.DataFrame({
            "Term": term_inputs,
            "Rows matched": per_term_counts
        })

        st.success(f"Matched {matched_rows_total} rows across {len(term_inputs)} terms.")
        st.dataframe(report_df, use_container_width=True)

        # --- EXPORT TO EXCEL ---
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            result.to_excel(writer, sheet_name="Filtered", index=False)
            report_df.to_excel(writer, sheet_name="Report", index=False)
        buf.seek(0)

        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename.strip()) or "filtered_results"

        st.download_button(
            "Download filtered Excel + report",
            data=buf,
            file_name=f"{safe_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
