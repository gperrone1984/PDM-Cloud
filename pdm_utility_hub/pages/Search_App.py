# pages/Search_App.py
import streamlit as st
import streamlit.components.v1 as components  # <-- per iniettare JS affidabile
import pandas as pd
import re
import unicodedata
from io import BytesIO

# 1) Page config (MUST be first)
st.set_page_config(
    page_title="Search App",
    page_icon="🔎",
    layout="centered",
    # initial_sidebar_state="expanded",  # opzionale
)

# 2) Authentication check
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.switch_page("app.py")

# 3) Global CSS: 550px aperta, invisibile da chiusa, look base
st.markdown(
    """
    <style>
      /* Sidebar APERTA: larghezza forzata a 550px */
      [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
        width: 550px !important;
        min-width: 550px !important;
        max-width: 550px !important;
        background-color: #ecf0f1 !important;
        padding: 10px !important;
      }

      /* Sidebar CHIUSA: scompare del tutto */
      [data-testid="stSidebar"][aria-expanded="false"] {
        transform: translateX(-100%) !important;
        width: 0 !important; min-width: 0 !important; max-width: 0 !important;
        margin: 0 !important; padding: 0 !important; border: 0 !important;
        overflow: hidden !important;
      }
      [data-testid="stSidebar"][aria-expanded="false"] * {
        pointer-events: none !important;
      }

      /* Nascondi la nav interna (lasci solo ciò che aggiungi tu) */
      [data-testid="stSidebarNav"] { display: none !important; }

      /* Look del main */
      section.main { background-color: #d8dfe6 !important; }
      .main .block-container,
      div[data-testid="stAppViewContainer"] > section > div.block-container {
        background-color: transparent !important;
        padding: 2rem 1rem 1rem 1rem !important;
        border-radius: 0 !important;
      }

      /* Migliora visibilità frecce (non le nascondiamo) */
      header button {
        white-space: nowrap;
      }
      header button svg {
        width: 18px !important;
        height: 18px !important;
        opacity: 1 !important;
      }

      /* Etichetta che iniettiamo via JS: stile */
      #sb-inline-label {
        margin-left: 8px;
        font-weight: 700;
        font-size: 0.98rem;
        letter-spacing: .2px;
        color: #1f2937;
        background: #fff;
        border: 1px solid rgba(0,0,0,.08);
        border-radius: 8px;
        padding: 4px 8px;
        line-height: 1;
        cursor: pointer;
        user-select: none;
      }
      #sb-inline-label:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,.10);
      }

      @media (max-width: 480px) {
        #sb-inline-label { font-size: 0.9rem; padding: 3px 6px; }
      }
    </style>
    """,
    unsafe_allow_html=True
)

# 3-bis) JS robusto: aggiunge un <span> accanto al toggle nativo e sincronizza il testo
components.html(
    """
    <script>
      (function () {
        const doc = window.parent.document;
        const SB_SEL = '[data-testid="stSidebar"]';

        function findToggle() {
          const header = doc.querySelector('header');
          if (!header) return null;

          // 1) preferisci button con riferimenti "Sidebar"
          let btn = header.querySelector('[data-testid*="Sidebar" i]');
          if (btn) return btn;

          // 2) prova gli attributi più comuni
          btn = header.querySelector('button[title*="sidebar" i], button[aria-label*="sidebar" i]');
          if (btn) return btn;

          // 3) fallback: primo bottone in header
          return header.querySelector('button');
        }

        function getSidebar() { return doc.querySelector(SB_SEL); }

        function setLabelText() {
          const sb = getSidebar();
          const label = doc.getElementById('sb-inline-label');
          if (!sb || !label) return;
          const open = sb.getAttribute('aria-expanded') === 'true';
          label.textContent = open ? 'clicca per chiudere' : 'clicca per aprire';
        }

        function ensureLabel() {
          const btn = findToggle();
          if (!btn) return false;

          let label = doc.getElementById('sb-inline-label');
          if (!label) {
            label = doc.createElement('span');
            label.id = 'sb-inline-label';
            label.textContent = 'clicca per aprire';
            // click sul testo = click sulle frecce
            label.addEventListener('click', function(e){
              e.preventDefault(); e.stopPropagation();
              const b = findToggle(); if (b) b.click();
            });
            // inserisci subito DOPO il bottone delle frecce
            btn.parentElement.insertBefore(label, btn.nextSibling);
          }
          setLabelText();
          return true;
        }

        function observe() {
          const sb = getSidebar();
          if (!sb) return;
          if (window.parent.__sbInlineObs) return; // evita duplicazioni
          window.parent.__sbInlineObs = new MutationObserver(function(muts){
            for (const m of muts) {
              if (m.type === 'attributes' && m.attributeName === 'aria-expanded') setLabelText();
            }
          });
          window.parent.__sbInlineObs.observe(sb, { attributes: true, attributeFilter: ['aria-expanded'] });
        }

        // attesa finché header + sidebar non sono pronti
        let tries = 0;
        const iv = setInterval(function(){
          if (ensureLabel()) { clearInterval(iv); observe(); }
          if (++tries > 100) clearInterval(iv);
        }, 150);

        // ritocco al load
        window.addEventListener('load', setLabelText);
      })();
    </script>
    """,
    height=0, width=0
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
