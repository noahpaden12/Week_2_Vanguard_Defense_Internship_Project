import streamlit as st
import os


# ---- CONFIG ----
st.set_page_config(page_title="Defense Annotation Tool", layout="wide")


# ---- INIT SESSION STATE ----
if "page" not in st.session_state:
   st.session_state.page = "home"
if "selected_dataset" not in st.session_state:
   st.session_state.selected_dataset = None
if "image_index" not in st.session_state:
   st.session_state.image_index = 0
if "images" not in st.session_state:
   st.session_state.images = []


#home page
def show_home():
   st.title("Defense Annotation Tool")
   st.header("Select a Dataset to Annotate")


   datasets = ["Dataset 1", "Dataset 2", "Dataset 3"]  # we gotta replace these with the folder (idk how to do em)


   for dataset in datasets:
       if st.button(dataset):
           st.session_state.selected_dataset = dataset
           st.session_state.images = [f"Image {i+1}" for i in range(1000)]  # Simulated image list
           st.session_state.image_index = 0
           st.session_state.page = "annotation"


# ANNOTATION PAGE
def show_annotation():
   st.title(" Annotation Page")
   st.subheader(f"Dataset: {st.session_state.selected_dataset}")


   # Show current image (placeholder text for now)
   current_image = st.session_state.images[st.session_state.image_index]
   st.write(f"📷 Currently viewing: **{current_image}**")


   # Image navigation
   col1, col2, col3 = st.columns(3)
   with col1:
       if st.button("⏮️ Previous") and st.session_state.image_index > 0:
           st.session_state.image_index -= 1
   with col2:
       if st.button("🖊️ Launch Annotation Tool"):
           st.info("not yet done")
   with col3:
       if st.button("⏭️ Next") and st.session_state.image_index < len(st.session_state.images) - 1:
           st.session_state.image_index += 1


   st.markdown("---")
   if st.button("🔙 Back to Home"):
       st.session_state.page = "home"
       st.session_state.selected_dataset = None
       st.session_state.image_index = 0
       st.session_state.images = []


# router
if st.session_state.page == "home":
   show_home()
elif st.session_state.page == "annotation":
   show_annotation()
