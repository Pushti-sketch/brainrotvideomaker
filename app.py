import streamlit as st
import ffmpeg
import tempfile
import os
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.aac import AAC
from mutagen.oggvorbis import OggVorbis

# --- Default Files ---
DEFAULT_OVERLAY_VIDEO = "greenscreen_overlay.mp4"

# Get audio duration using mutagen (pure Python)
def get_audio_duration(audio_path):
    try:
        ext = os.path.splitext(audio_path)[1].lower()
        if ext == ".mp3":
            audio = MP3(audio_path)
        elif ext == ".wav":
            audio = WAVE(audio_path)
        elif ext == ".aac":
            audio = AAC(audio_path)
        elif ext == ".ogg":
            audio = OggVorbis(audio_path)
        else:
            st.error(f"Unsupported audio format: {ext}")
            return 0
        return audio.info.length
    except Exception as e:
        st.error(f"Could not determine audio duration: {e}")
        return 0

# Apply chroma key using ffmpeg
def apply_chroma_key(base_video_path, overlay_video_path, output_path, color_to_remove=(0, 255, 0), similarity=0.1):
    try:
        chroma_color = f"0x{color_to_remove[0]:02x}{color_to_remove[1]:02x}{color_to_remove[2]:02x}"
        ffmpeg.input(base_video_path).input(overlay_video_path).output(
            output_path,
            vcodec='libx264',
            acodec='aac',
            filter_complex=(
                f"[1:v]chromakey={chroma_color}:{similarity}[ckout];"
                f"[0:v][ckout]overlay=shortest=1[outv]"
            ),
            map="[outv]",
            shortest=None
        ).run(overwrite_output=True)
        return output_path
    except ffmpeg.Error as e:
        st.error(f"FFmpeg chroma key error: {e.stderr.decode()}")
        return None

# Combine audio with video
def combine_audio_video(audio_path, video_path, output_path):
    try:
        ffmpeg.input(video_path).input(audio_path).output(
            output_path,
            vcodec='libx264',
            acodec='aac',
            strict='experimental'
        ).run(overwrite_output=True)
        return output_path
    except ffmpeg.Error as e:
        st.error(f"FFmpeg combine error: {e.stderr.decode()}")
        return None

# Main processing logic
def process_media(audio_file, image_file):
    try:
        # Save uploaded files
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as tmp_audio:
            tmp_audio.write(audio_file.read())
            audio_path = tmp_audio.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_file.name)[1]) as tmp_image:
            tmp_image.write(image_file.read())
            image_path = tmp_image.name

        # Get audio duration
        duration = get_audio_duration(audio_path)
        if duration <= 0:
            st.error("Audio duration is invalid.")
            return None

        # Step 1: Turn image into video
        image_video_path = os.path.join(tempfile.gettempdir(), "image_video.mp4")
        ffmpeg.input(image_path, loop=1, t=duration).output(
            image_video_path, vcodec='libx264', pix_fmt='yuv420p', r=24
        ).run(overwrite_output=True)

        # Step 2: Overlay greenscreen video
        overlay_path = os.path.join(tempfile.gettempdir(), "overlay_video.mp4")
        apply_chroma_key(image_video_path, DEFAULT_OVERLAY_VIDEO, overlay_path)

        # Step 3: Combine with audio
        final_output_path = os.path.join(tempfile.gettempdir(), "final_output.mp4")
        combine_audio_video(audio_path, overlay_path, final_output_path)

        # Cleanup
        os.remove(audio_path)
        os.remove(image_path)
        os.remove(image_video_path)
        os.remove(overlay_path)

        return final_output_path

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# --- Streamlit UI ---
st.title("🎬 Media Fusion Studio")
st.write("Upload your audio and image to create a video with a greenscreen overlay!")

uploaded_audio = st.file_uploader("Upload your audio file (MP3, WAV, AAC, OGG)", type=["mp3", "wav", "aac", "ogg"])
uploaded_image = st.file_uploader("Upload your image file (PNG, JPG, etc.)", type=["png", "jpg", "jpeg"])

if uploaded_audio and uploaded_image:
    st.info("Processing your media... please wait ⏳")
    final_video_path = process_media(uploaded_audio, uploaded_image)

    if final_video_path:
        with open(final_video_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Final Video",
                data=f.read(),
                file_name="final_video.mp4",
                mime="video/mp4"
            )
        os.remove(final_video_path)
    else:
        st.error("Failed to generate the video. Please try again.")

st.sidebar.header("ℹ️ Default Files Info")
st.sidebar.info(f"Greenscreen Overlay: `{DEFAULT_OVERLAY_VIDEO}` (must be present in the same directory)")
