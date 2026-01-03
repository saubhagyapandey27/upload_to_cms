import streamlit as st
import os
import requests
from dotenv import load_dotenv
import cms_utils

# Load environment variables
load_dotenv('.env.local')

st.set_page_config(page_title="CMS Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Sidebar Configuration
# Use secrets if available (Streamlit Cloud), else env vars
# Config Loading
api_url = os.getenv("COCKPIT_URL", "")
api_token = os.getenv("API_TOKEN", "")
default_password = os.getenv("UPLOAD_PASSWORD", "")

# Try loading from secrets (Cloud)
try:
    if st.secrets:
        if "COCKPIT_URL" in st.secrets: api_url = st.secrets["COCKPIT_URL"]
        if "API_TOKEN" in st.secrets: api_token = st.secrets["API_TOKEN"]
        if "UPLOAD_PASSWORD" in st.secrets: default_password = st.secrets["UPLOAD_PASSWORD"]
except (FileNotFoundError, AttributeError):
    pass

if not api_url or not api_token or not default_password:
    st.error("❌ Missing Configuration! Check .env.local or Streamlit Secrets.")
    st.stop()

st.title("Admin Dashboard")

# Session State Initialization
if 'processed_images' not in st.session_state: st.session_state['processed_images'] = []
if 'processed_audio' not in st.session_state: st.session_state['processed_audio'] = []
# For team member, we store the single processed processed object
if 'processed_teammember' not in st.session_state: st.session_state['processed_teammember'] = None

tab_img, tab_audio, tab_team = st.tabs(["🖼 Batch Image Upload", "🎵 Batch Audio Upload", "👤 Add Team Member"])

# --- TAB 1: IMAGES ---
with tab_img:
    st.header("Batch Image Processing & Upload")
    st.info("ℹ️ Images are resized to 16:9 (Horizontal) or 800x800 (Square) and compressed to Quality 60 JPEG to ensure file size is <200KB.")
    
    upload_mode = st.radio("Processing Mode", ["Horizontal (16:9)", "Square (Center Crop)"])
    mode_key = 'horizontal' if "Horizontal" in upload_mode else 'square'
    
    uploaded_images = st.file_uploader("Select Images", accept_multiple_files=True, type=['jpg', 'png', 'jpeg', 'webp'])
    
    # STEP 1: PROCESSING
    if st.button("Step 1: Process Images"):
        if not uploaded_images:
            st.warning("No images selected.")
        else:
            processed_data = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, img_file in enumerate(uploaded_images):
                status_text.text(f"Processing {img_file.name}...")
                file_bytes = img_file.read()
                p_bytes = cms_utils.process_image(file_bytes, mode=mode_key)
                
                if p_bytes:
                    new_name = os.path.splitext(img_file.name)[0] + ".jpg"
                    if mode_key == 'square': new_name = new_name.replace(".jpg", "_sq.jpg")
                    processed_data.append({"name": new_name, "bytes": p_bytes})
                
                progress_bar.progress((idx + 1) / len(uploaded_images))
            
            st.session_state['processed_images'] = processed_data
            status_text.empty()
            st.success(f"Processed {len(processed_data)} images. Ready for upload verification.")

    # STEP 2: AUTH & UPLOAD
    if st.session_state['processed_images']:
        st.divider()
        st.write(f"**Ready to upload {len(st.session_state['processed_images'])} images.**")
        
        auth_pass = st.text_input("Enter Upload Password", type="password", key="img_auth")
        
        if st.button("Step 2: Authenticate & Upload"):
            if auth_pass == default_password:
                success_count = 0
                prog = st.progress(0)
                
                for idx, item in enumerate(st.session_state['processed_images']):
                    asset = cms_utils.upload_asset(api_url, api_token, item['bytes'], item['name'])
                    if asset: success_count += 1
                    prog.progress((idx + 1) / len(st.session_state['processed_images']))
                
                if success_count == len(st.session_state['processed_images']):
                    st.success(f"All {success_count} images uploaded successfully!")
                    st.session_state['processed_images'] = [] # Clear
                else:
                    st.warning(f"Uploaded {success_count}/{len(st.session_state['processed_images'])} images.")
            else:
                st.error("Incorrect Password.")

# --- TAB 2: AUDIO ---
with tab_audio:
    st.header("Batch Audio Compression & Upload")
    st.info("ℹ️ Files will be compressed to 64kbps MP3 for minimal size.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        channel_mode = st.radio("Audio Channels", ["Mono (Smaller Size)", "Stereo (Better Quality)"])
    
    uploaded_audios = st.file_uploader("Select Audio Files", accept_multiple_files=True, type=['mp3', 'wav', 'm4a', 'ogg'])
    
    # STEP 1: PROCESSING
    if st.button("Step 1: Process Audio"):
        if not uploaded_audios:
            st.warning("No audio files selected.")
        else:
            processed_data = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            channels = 1 if "Mono" in channel_mode else 2
            
            for idx, audio_file in enumerate(uploaded_audios):
                status_text.text(f"Compressing {audio_file.name}...")
                file_bytes = audio_file.read()
                p_bytes = cms_utils.process_audio(file_bytes, audio_file.name, channels=channels)
                
                if p_bytes:
                    new_name = os.path.splitext(audio_file.name)[0] + ".mp3"
                    processed_data.append({"name": new_name, "bytes": p_bytes})
                
                progress_bar.progress((idx + 1) / len(uploaded_audios))
                
            st.session_state['processed_audio'] = processed_data
            status_text.empty()
            st.success(f"Processed {len(processed_data)} audio files. Ready for upload verification.")
            
    # STEP 2: AUTH & UPLOAD
    if st.session_state['processed_audio']:
        st.divider()
        st.write(f"**Ready to upload {len(st.session_state['processed_audio'])} audio files.**")
        
        auth_pass_audio = st.text_input("Enter Upload Password", type="password", key="audio_auth")
        
        if st.button("Step 2: Authenticate & Upload Audio"):
            if auth_pass_audio == default_password:
                success_count = 0
                prog = st.progress(0)
                
                for idx, item in enumerate(st.session_state['processed_audio']):
                    asset = cms_utils.upload_asset(api_url, api_token, item['bytes'], item['name'])
                    if asset: 
                        success_count += 1
                        st.write(f"✅ Uploaded: {item['name']}")
                    prog.progress((idx + 1) / len(st.session_state['processed_audio']))
                
                st.success(f"Completed! Uploaded {success_count} files.")
                st.session_state['processed_audio'] = [] # Clear
            else:
                st.error("Incorrect Password.")

# --- TAB 3: TEAM MEMBERS ---
with tab_team:
    st.header("Add New Team Member")
    
    col1, col2 = st.columns(2)
    with col1:
        t_name = st.text_input("Name")
        t_email = st.text_input("Email")
        t_role = st.selectbox("Role", ["Coordinator", "Secretary", "Ex-Coordinator"], index=None, placeholder="Choose Role")
        t_year = st.text_input("Year (only for ex-coordinators)")
    with col2:
        t_phone = st.text_input("Phone (only for coordinators)")
        t_sher_author = st.text_input("Sher Author")
        t_sher = st.text_area("Sher (Max 2 lines)")
        t_photo = st.file_uploader("Profile Photo", type=['jpg', 'png', 'jpeg'])

    # STEP 1: PREVIEW
    if st.button("Step 1: Process & Preview"):
        if not t_name or not t_role or not t_photo:
            st.error("Name, Role, and Photo are required.")
        else:
            p_bytes = cms_utils.process_image(t_photo.read(), mode='square')
            if p_bytes:
                st.image(p_bytes, caption="Processed Image Preview (Square)", width=200)
                st.session_state['processed_teammember'] = {
                    "photo_bytes": p_bytes,
                    "name": t_name,
                    "email": t_email,
                    "role": t_role,
                    "phone": t_phone,
                    "year": t_year,
                    "sher": t_sher,
                    "sher_author": t_sher_author
                }
                st.success("Data prepared. Please authenticate to upload.")
            else:
                st.error("Failed to process image.")

    # STEP 2: AUTH & UPLOAD
    if st.session_state['processed_teammember']:
        st.divider()
        st.write("**Authenticate to Create Enty**")
        auth_pass_team = st.text_input("Enter Upload Password", type="password", key="team_auth")
        
        if st.button("Step 2: Upload & Create"):
            if auth_pass_team == default_password:
                data = st.session_state['processed_teammember']
                
                with st.spinner("Uploading Asset..."):
                    img_name = f"team_{data['name'].replace(' ', '_').lower()}.jpg"
                    asset = cms_utils.upload_asset(api_url, api_token, data['photo_bytes'], img_name)
                    
                    if asset:
                        entry_data = {
                            "Name": data['name'],
                            "Email": data['email'],
                            "Role": data['role'],
                            "Phone": data['phone'],
                            "Sher": data['sher'].replace("\n", "<br>"),
                            "SherAuthor": data['sher_author'],
                            "Year": data['year'],
                            "Photo": {
                                "_id": asset.get("_id"),
                                "path": asset.get("path"),
                                "title": asset.get("title"),
                                "mime": asset.get("mime"),
                                "size": asset.get("size")
                            }
                        }
                        
                        resp = cms_utils.create_collection_entry(api_url, api_token, "teammembers", entry_data)
                        if resp:
                            st.success(f"Team Member '{data['name']}' added successfully!")
                            st.json(resp)
                            st.session_state['processed_teammember'] = None # Clear
                        else:
                            st.error("Failed to create collection entry.")
                    else:
                        st.error("Failed to upload asset.")
            else:
                st.error("Incorrect Password.")
