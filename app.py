import streamlit as st
import ffmpeg
import tempfile
import os

# --- Default Files ---
DEFAULT_BACKGROUND_MUSIC = "default_bg_music.mp3"
DEFAULT_OVERLAY_VIDEO = "greenscreen_overlay.mp4"

# Function to get audio duration
def get_audio_duration(audio_path):
    try:
        probe = ffmpeg.probe(audio_path)
        return float(probe['format']['duration'])
    except Exception as e:
        st.error(f"Could not determine audio duration: {e}")
        return 0

# Function to apply chroma key (green screen)
def apply_chroma_key(base_video_path, overlay_video_path, output_path, color_to_remove=(0, 255, 0), similarity=0.1):
    try:
        ffmpeg.input(base_video_path).input(overlay_video_path).output(
            output_path,
            vcodec='libx264',
            acodec='aac',
            filter_complex=(
                f"[1:v]chromakey=0x{color_to_remove[0]:02x}{color_to_remove[1]:02x}{color_to_remove[2]:02x}:{similarity}[ckout];"
                f"[0:v][ckout]overlay=shortest=1[outv]"
            ),
            map="[outv]",
            shortest=None,
        ).run(overwrite_output=True)
        return output_path
    except ffmpeg.Error as e:
        st.error(f"FFmpeg chroma key error: {e.stderr.decode()}")
        return None

# Function to combine audio and video
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

# Main processing function
def process_media(audio_file, image_file):
    try:
        # Save uploaded files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
            tmp_audio.write(audio_file.read())
            audio_path = tmp_audio.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_image:
            tmp_image.write(image_file.read())
            image_path = tmp_image.name

        duration = get_audio_duration(audio_path)
        if duration <= 0:
            st.error("Audio duration is invalid.")
            return None

        # Step 1: Turn image into a video for the length of the audio
        temp_video_path = os.path.join(tempfile.gettempdir(), "image_video.mp4")
        ffmpeg.input(image_path, loop=1, t=duration).output(
            temp_video_path, vcodec='libx264', pix_fmt='yuv420p', r=24
        ).run(overwrite_output=True)

        # Step 2: Overlay greenscreen video onto the image video
        overlay_applied_path = os.path.join(tempfile.gettempdir(), "overlay_applied.mp4")
        apply_chroma_key(temp_video_path, DEFAULT_OVERLAY_VIDEO, overlay_applied_path)

        # Step 3: Combine with original audio
        final_output_path = os.path.join(tempfile.gettempdir(), "final_output.mp4")
        combine_audio_video(audio_path, overlay_applied_path, final_output_path)

        # Cleanup
        os.remove(audio_path)
        os.remove(image_path)
        os.remove(temp_video_path)
        os.remove(overlay_applied_path)

        return final_output_path

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Streamlit interface
st.title("🎬 Media Fusion Studio")
st.write("Upload your audio and image to create a custom video with background visuals and greenscreen overlay.")

uploaded_audio = st.file_uploader("Upload your audio file (MP3, WAV, etc.)", type=["mp3", "wav", "aac", "ogg"])
uploaded_image = st.file_uploader("Upload your image file (PNG, JPG, etc.)", type=["png", "jpg", "jpeg"])

if uploaded_audio and uploaded_image:
    st.info("Processing your media... please wait ⏳")
    result_video = process_media(uploaded_audio, uploaded_image)

    if result_video:
        with open(result_video, "rb") as f:
            st.download_button(
                label="⬇️ Download Final Video",
                data=f.read(),
                file_name="final_video.mp4",
                mime="video/mp4",
            )
        os.remove(result_video)
    else:
        st.error("Failed to process the media. Please check your files and try again.")

st.sidebar.header("ℹ️ Default Files Info")
st.sidebar.info(f"Default Background Music: `{DEFAULT_BACKGROUND_MUSIC}`\n(Default music not yet used)")
st.sidebar.info(f"Greenscreen Overlay: `{DEFAULT_OVERLAY_VIDEO}` (must be present in the same directory)")
