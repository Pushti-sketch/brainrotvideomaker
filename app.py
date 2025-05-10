import streamlit as st
import ffmpeg
import numpy as np
from PIL import Image
import tempfile
import os
import shutil
from io import BytesIO

# --- Default Files (Relative paths for GitHub deployment) ---
DEFAULT_BACKGROUND_MUSIC = "default_bg_music.mp3"
DEFAULT_OVERLAY_VIDEO = "greenscreen_overlay.mp4"

def apply_chroma_key(input_video_path, overlay_video_path, output_video_path, color_to_remove=(0, 255, 0), tolerance=100):
    """Applies chroma keying to overlay a video onto another."""
    try:
        # Construct the ffmpeg filter for chroma keying
        chroma_filter = f"[1:v]chromakey={color_to_remove[0]}:{color_to_remove[1]}:{color_to_remove[2]}:{tolerance/255.0}[ckout];"
        overlay_filter = f"[0:v][ckout]overlay=shortest=1[out]"

        # Run ffmpeg to apply chroma key and overlay
        ffmpeg.input(input_video_path).input(overlay_video_path).output(output_video_path, vcodec='libx264', acodec='aac', filter_complex=chroma_filter + overlay_filter).run(overwrite_output=True)
        return output_video_path
    except ffmpeg.Error as e:
        st.error(f"FFmpeg error: {e.stderr.decode()}")
        return None

def combine_audio_video(audio_path, video_path, output_path):
    """Combines audio and video into a single file."""
    try:
        ffmpeg.input(video_path).input(audio_path).output(output_path, vcodec='libx264', acodec='aac').run(overwrite_output=True)
        return output_path
    except ffmpeg.Error as e:
        st.error(f"FFmpeg error: {e.stderr.decode()}")
        return None

def process_media(audio_file, image_file):
    """Processes the uploaded audio and image to create a video."""
    try:
        # Save the uploaded files to temporary locations
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
            tmp_audio.write(audio_file.read())
            audio_path = tmp_audio.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_image:
            tmp_image.write(image_file.read())
            image_path = tmp_image.name

        # Create a temporary video from the image
        video_path = "temp_video.mp4"
        ffmpeg.input('anullsrc=r=30:cl=stereo', f='lavfi', t=audio_file.duration).output(video_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p').run(overwrite_output=True)

        # Apply chroma keying to overlay the image onto the video
        final_video_path = "final_video.mp4"
        apply_chroma_key(video_path, image_path, final_video_path)

        # Combine the final video with the audio
        final_output_path = "final_output.mp4"
        combine_audio_video(audio_path, final_video_path, final_output_path)

        # Clean up temporary files
        os.remove(audio_path)
        os.remove(image_path)
        os.remove(video_path)
        os.remove(final_video_path)

        return final_output_path
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Streamlit app interface
st.title("Media Fusion Studio")
st.write("Upload your audio and image to create a combined video with background music and a greenscreen overlay.")

uploaded_audio = st.file_uploader("Upload your audio file (MP3, WAV, etc.)", type=["mp3", "wav", "aac", "ogg"])
uploaded_image = st.file_uploader("Upload your image file (PNG, JPG, etc.)", type=["png", "jpg", "jpeg"])

if uploaded_audio and uploaded_image:
    st.info("Processing your media...")
    final_video_path = process_media(uploaded_audio, uploaded_image)

    if final_video_path:
        with open(final_video_path, "rb") as f:
            st.download_button(
                label="Download Final Video",
                data=f.read(),
                file_name="final_video.mp4",
                mime="video/mp4",
            )

        # Clean up the final video file
        os.remove(final_video_path)
