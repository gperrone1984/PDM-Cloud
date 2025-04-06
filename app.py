import streamlit as st
from bundle_images import bundle_images_app
from repository_images import repository_images_app

# Page configuration
st.set_page_config(
    page_title="PDM Utility Hub",
    page_icon="🧰",
    layout="wide"
)

# Sidebar
st.sidebar.title("🧰 PDM Utility Hub")
st.sidebar.markdown("### Select a tool")

app_choice = st.sidebar.radio(
    "",
    (
        "Bundle & Set Images Creator",
        "Repository Image Download & Renaming",
        "Coming Soon"
    )
)

# Main content
if app_choice == "Bundle & Set Images Creator":
    bundle_images_app()

elif app_choice == "Repository Image Download & Renaming":
    repository_images_app()

elif app_choice == "Coming Soon":
    st.title("🚧 Coming Soon")
    st.write("This section is under development. Stay tuned!")