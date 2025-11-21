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
    layout="centered",
    # initial_sidebar_state="expanded",  # lasciamo il default
)

# 2) Authentication check
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# 3) Global CSS + JS
st.markdown(
    """
    <style>
      /* ---- Nascondi la nav interna della sidebar ---- */
      [data-testid="stSidebarNav"] { display: none !important; }

      /* ---- Sidebar APERTA: larghezza forzata 550px ---- */
      [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
          width: 550px !important;
          min-width: 550px !important;
          max-width: 550px !important;
          background-color: #ecf0f1 !important;
          padding: 10px !important;
      }

      /* ---- Main look ---- */
      section.main { background-color: #d8dfe6 !important; }
      .main .block-container,
      div[data-testid="stAppViewContainer"] > section > div.block-container {
          background-color: transparent !important;
          padding: 2rem 1rem 1rem 1rem !important;
          border-radius: 0 !important;
      }

      /* ---- Sidebar CHIUSA: scomparsa completa ---- */
      [data-testid="stSidebar"][aria-expanded="false"] {
          transform: translateX(-100%) !important;
          width: 0 !important; min-width: 0 !important; max-width: 0 !important;
          margin: 0 !important; padding: 0 !important; border: 0 !important;
          overflow: hidden !important;
      }
      [data-testid="stSidebar"][aria-expanded="false"] * {
          pointer-events: none !important;
      }

      /* ====== Toggle nativo personalizzato: SOLO TESTO BEN VISIBILE ====== */
      /* Nascondi l'icona (frecce) */
      header button[title="Toggle sidebar"] svg,
      header button[aria-label="Toggle sidebar"] svg,
      header button[data-testid="stSidebarCollapseButton"] svg {
        display: none !important;
      }

      /* Stile del bottone (posizione e resa) */
      header button[title="Toggle sidebar"],
      header button[aria-label="Toggle sidebar"],
      header button[data-testid="stSidebarCollapseButton"] {
        position: fixed !important;
        top: 16px !important;
        left: 16px !important;               /* mettilo vicino alla sidebar */
        z-index: 9999 !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        background: #ffffff !important;
        border: 1px solid rgba(0,0,0,.12) !important;
        box-shadow: 0 2px 10px rgba(0,0,0,.08) !important;
        cursor: pointer !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 38px !important;
      }

      /* Testo quando la sidebar è CHIUSA */
      html[data-sidebar="closed"] header button[title="Toggle sidebar"]::after,
      html[data-sidebar="closed"] header button[aria-label="Toggle sidebar"]::after,
      html[data-sidebar="closed"] header button[data-testid="stSidebarCollapseButton"]::after {
        content: "Clicca per aprire";
        font-weight: 700;
        font-size: 0.98rem;
        color: #1f2937;
        letter-spacing: .2px;
        white-space: nowrap;
      }

      /* Testo quando la sidebar è APERTA */
      html[data-sidebar="open"] header button[title="Toggle sidebar"]::after,
      html[data-sidebar="open"] header button[aria-label="Toggle sidebar"]::after,
      html[data-sidebar="open"] header button[data-testid="stSidebarCollapseButton"]::after {
        content: "Clicca per chiudere";
        font-weight: 700;
        font-size: 0.98rem;
        color: #1f2937;
        letter-spacing: .2px;
        white-space: nowrap;
      }

      /* Hover/Focus: più evidente */
      header button[title="Toggle sidebar"]:hover,
      header button[aria-label="Toggle sidebar"]:hover,
      header button[data-testid="stSidebarCollapseButton"]:hover {
        box-shadow: 0 4px 14px rgba(0,0,0,.14) !important;
        transform: translateY(-1px);
      }

      /* Mobile: se lo spazio è poco, riduci il testo ma resta visibile */
      @media (max-width: 480px) {
        html[data-sidebar] header button[title="Toggle sidebar"]::after,
        html[data-sidebar] header button[aria-label="Toggle sidebar"]::after,
        html[data-sidebar] header button[data-testid="stSidebarCollapseButton"]::after {
          font-size: 0.86rem;
        }
      }
    </style>

    <!-- JS: sincronizza data-sidebar="open|closed" con aria-expanded -->
    <script>
      (function () {
        function setFlag() {
          var sb = document.querySelector('[data-testid="stSidebar"]');
          if (!sb) return;
          var expanded = sb.getAttribute('aria-expanded') === 'true';
          document.documentElement.setAttribute('data-sidebar', expanded ? 'open' : 'closed');
        }
        function initObserver() {
          setFlag();
          var sb = document.querySelector('[data-testid="stSidebar"]');
          if (!sb) return;
          new MutationObserver(function(muts){
            for (var m of muts) {
              if (m.type === 'attributes' && m.attributeName === 'aria-expanded') setFlag();
            }
          }).observe(sb, { attributes: true });
        }
        var tries = 0, iv = setInterval(function(){
          tries++;
          if (document.querySelector('[data-testid="stSidebar"]')) { clearInterval(iv); initObserver(); }
          if (tries > 50) clearInterval(iv);
        }, 200);
        window.addEventListener('load', setFlag);
      })();
    </script>
    """,
    unsafe_allow_html=True
)

# 4) Sidebar (contenuti tuoi)
st.sidebar.page_link("app.py", label="**PDM Utility Hub**", icon="🏠")
st.sidebar.markdown("---")

# ---------- Helpers ----------
def strip_accents(s):
    if not isinstance(s, str):
        s = str(s)
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if not unicodedata.combining(ch))

def build_spacing_pattern(term):
    return r"(?<!\\w)" + ''.join([re.escape(c) + r"\\s*" for c in term]) + r"(?!\\w)"

# ---------- State ----------
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0
for i in range(1, 11):
    st.session_state.setdefault(f'term{i}', '')
st.session_state.setdefault('custom_filename', 'filtered_results')
st.session_state.setdefault('download_bytes', b'')
st.session_state.setdefault('download_filename', '')

def clear_all():
    for i in range(1, 11):
        st.session_state[f'term{i}'] = ''
    st.session_state['custom_filename'] = ''
    st.session_state['download_bytes'] = b''
    st.session_state['download_filename'] = ''
    st.session_state['uploader_key'] += 1

# ---------- UI ----------
st.title("Search App:")

st.markdown("""
**ℹ️ How to use::**
- Upload an Excel file (.xlsx or .xls).
- Enter up to **10** search terms or phrases.
- Choose the final output filename.
- Click **Search and Download** to get the filtered Excel + report.
""")

if st.button("Clear cache and data"):
    clear_all()
    st.rerun()

uploaded_file = st.file_uploader(
    "Choose an Excel file", type=["xlsx", "xls"],
    key=f'uploaded_file_{st.session_state["uploader_key"]}'
)

for i in range(1, 11):
    st.text_input(f"Term {i}", key=f'term{i}')
st.text_input("Output filename", key="custom_filename")

# ---------- Azione: cerca & salva ----------
if st.button("Search and Download"):
    terms = [st.session_state[f'term{i}'].strip() for i in range(1, 11) if st.session_state[f'term{i}'].strip()]

    if not uploaded_file:
        st.error("Please upload a file first."); st.stop()
    if not terms:
        st.error("Please enter at least one search term."); st.stop()

    st.info("Reading file progressively — please wait...")

    term_noacc = [strip_accents(t) for t in terms]
    term_compact = [re.sub(r"\\s+", "", t) for t in term_noacc]
    compiled = [re.compile(build_spacing_pattern(t), re.IGNORECASE) for t in term_compact]
    per_term_counts = [0] * len(compiled)

    wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
    ws = wb.active

    headers = [str(c.value) if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
    matches, total, matched = [], 0, 0
    progress = st.progress(0)

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        total += 1
        row_values = ["" if v is None else str(v) for v in row]
        text_noacc = strip_accents(' '.join(row_values))
        row_hits = [terms[j] for j, pat in enumerate(compiled) if pat.search(text_noacc)]
        if row_hits:
            matched += 1
            for j, pat in enumerate(compiled):
                if pat.search(text_noacc): per_term_counts[j] += 1
            rd = dict(zip(headers, row_values)); rd["Matched terms"] = ";".join(row_hits)
            matches.append(rd)
        if i % 1000 == 0:
            total_rows = ws.max_row or (i + 1)
            progress.progress(min(1.0, i / total_rows))

    progress.empty(); wb.close()

    if not matches:
        st.warning("No matches found."); st.stop()

    result_df = pd.DataFrame(matches)
    report_df = pd.DataFrame({"Term": terms, "Rows matched": per_term_counts})

    st.success(f"Matched {matched} rows out of ~{total} scanned.")
    st.dataframe(report_df, use_container_width=True)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        result_df.to_excel(writer, sheet_name="Filtered", index=False)
        report_df.to_excel(writer, sheet_name="Report", index=False)
    buf.seek(0)

    import os, re as _re
    safe_name = _re.sub(r'[<>:"/\\\\|?*]', '_', (st.session_state['custom_filename'] or '').strip()) or "filtered_results"
    st.session_state['download_bytes'] = buf.getvalue()
    st.session_state['download_filename'] = f"{safe_name}.xlsx"

# ---------- Download ----------
if st.session_state.get('download_bytes'):
    st.download_button(
        "Download filtered Excel + report",
        data=st.session_state['download_bytes'],
        file_name=st.session_state['download_filename'] or "filtered_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="download_btn"
    )
