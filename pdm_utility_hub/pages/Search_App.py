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

# 2) Auth guard (same as in your Hub)
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.error("You must be logged in to view this page.")
    st.stop()

# 3) Hub CSS + sidebar “back” link
st.markdown("""
    <style>
      /* hide default nav/sidebar, force your Hub styles */
      section[data-testid="stSidebar"] { width: 300px !important; }
    </style>
""", unsafe_allow_html=True)

# Link back to the Hub
st.sidebar.page_link("app.py", label="🏠 Back to PDM Utility Hub")

# 4) App title + instructions
st.title("🔎 Search App")
st.write("Upload an Excel file, enter up to five search terms (e.g. “biossido di titanio”, “E171”), then click Search and Filter.")

# 5) File uploader + term inputs
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
term1 = st.text_input("Term 1")
term2 = st.text_input("Term 2")
term3 = st.text_input("Term 3")
term4 = st.text_input("Term 4")
term5 = st.text_input("Term 5")

# Build regex pattern
terms = [t.strip() for t in (term1, term2, term3, term4, term5) if t.strip()]
pattern = None
if terms:
    escaped = [re.escape(t).replace(r"\ ", r"\s*") for t in terms]
    pattern = r"(" + r"|".join(escaped) + r")"

# 6) Search button logic
if st.button("Search and Filter"):
    if not uploaded_file:
        st.error("Please upload an Excel file first.")
    elif not pattern:
        st.error("Please enter at least one search term.")
    else:
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
        else:
            if 'Long description' not in df.columns:
                st.error("No column named 'Long description' found.")
            else:
                mask = df['Long description'].astype(str)\
                         .str.contains(pattern, case=False, regex=True, na=False)
                filtered = df[mask]
                st.write(f"Rows found: {len(filtered)}")
                st.dataframe(filtered)

                # download button
                towrite = BytesIO()
                filtered.to_excel(towrite, index=False, engine='openpyxl')
                towrite.seek(0)
                st.download_button(
                    "Download filtered Excel",
                    data=towrite,
                    file_name="filtered_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
