import streamlit as st
import openpyxl
import re
import unicodedata
from io import BytesIO
import pandas as pd

st.set_page_config(page_title="Search App", page_icon="🔎", layout="centered")

# --- Sidebar: ONLY the requested button ---
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")  # separatore

# --- Hide any page links that might appear in the MAIN area ---
st.markdown("""
<style>
section[data-testid="stMain"] a[data-testid="stPageLink"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- Helpers ---
def strip_accents(s):
    if not isinstance(s, str):
        s = str(s)
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if not unicodedata.combining(ch))

def build_spacing_pattern(term):
    return r"(?<!\w)" + ''.join([re.escape(c) + r"\s*" for c in term]) + r"(?!\w)"

def clear_all():
    keys = ['uploaded_file'] + [f'term{i}' for i in range(1, 11)] + ['custom_filename']
    for k in keys:
        st.session_state.pop(k, None)

# --- UI ---
st.title("🔎 Search App")

st.markdown(
    """
**ℹ️ How to use::**
- Upload an Excel file (.xlsx or .xls).
- Enter up to **10** search terms or phrases.
- Choose the final output filename.
- Click **Search and Download** to get the filtered Excel + report.
"""
)

st.button("Clear cache and data", on_click=clear_all)

uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"], key='uploaded_file')
terms = [st.text_input(f"Term {i}") for i in range(1, 11)]
terms = [t.strip() for t in terms if t.strip()]
custom_filename = st.text_input("Output filename", value="filtered_results")

if st.button("Search and Download"):
    if not uploaded_file:
        st.error("Please upload a file first.")
        st.stop()
    if not terms:
        st.error("Please enter at least one search term.")
        st.stop()

    st.info("Reading file progressively — please wait...")

    # compile patterns
    term_noacc = [strip_accents(t) for t in terms]
    term_compact = [re.sub(r"\s+", "", t) for t in term_noacc]
    compiled = [re.compile(build_spacing_pattern(t), re.IGNORECASE) for t in term_compact]
    per_term_counts = [0] * len(compiled)

    wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
    ws = wb.active

    headers = [str(c.value) if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
    matches = []
    total = 0
    matched = 0
    progress = st.progress(0)

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        total += 1
        row_values = ["" if v is None else str(v) for v in row]
        text = ' '.join(row_values)
        text_noacc = strip_accents(text)
        row_hits = [terms[j] for j, pat in enumerate(compiled) if pat.search(text_noacc)]
        if row_hits:
            matched += 1
            for j, pat in enumerate(compiled):
                if pat.search(text_noacc):
                    per_term_counts[j] += 1
            row_dict = dict(zip(headers, row_values))
            row_dict["Matched terms"] = ";".join(row_hits)
            matches.append(row_dict)
        if i % 1000 == 0:
            progress.progress(min(1.0, i / (ws.max_row or 1)))

    progress.empty()
    wb.close()

    if not matches:
        st.warning("No matches found.")
        st.stop()

    result_df = pd.DataFrame(matches)
    report_df = pd.DataFrame({"Term": terms, "Rows matched": per_term_counts})

    st.success(f"Matched {matched} rows out of ~{total} scanned.")
    st.dataframe(report_df)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        result_df.to_excel(writer, sheet_name="Filtered", index=False)
        report_df.to_excel(writer, sheet_name="Report", index=False)
    buf.seek(0)

    st.download_button(
        "Download filtered Excel + report",
        data=buf,
        file_name=f"{re.sub(r'[<>:\"/\\\\|?*]', '_', custom_filename.strip())}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
