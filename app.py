import streamlit as st
import tempfile
import os
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip

# --- Default Files ---
DEFAULT_OVERLAY_VIDEO = "greenscreen_overlay.mp4"  # Pre-generated video

# Get audio duration using mutagen (pure Python)
def get_audio_duration(audio_path):
    try:
        from mutagen.mp3 import MP3
        from mutagen.wave import WAVE
        from mutagen.aac import AAC
        from mutagen.oggvorbis import OggVorbis

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

# Process media and create final video
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

        # Load video and prepare overlay
        overlay_clip = VideoFileClip(DEFAULT_OVERLAY_VIDEO)
        overlay_clip_resized = overlay_clip.resize(width=1280)  # Adjust size to fit the image
        overlay_clip_resized = overlay_clip_resized.set_duration(duration)  # Match duration to the audio

        # Load the image
        image_clip = ImageClip(image_path).set_duration(duration).resize(height=720).set_position('center')

        # Combine image and overlay video
        final_video = CompositeVideoClip([image_clip, overlay_clip_resized])

        # Add audio
        audio = AudioFileClip(audio_path).subclip(0, duration)  # Trim audio to match video
        final_video = final_video.set_audio(audio)

        # Save the final video
        final_output_path = os.path.join(tempfile.gettempdir(), "final_output.mp4")
        final_video.write_videofile(final_output_path, codec="libx264", audio_codec="aac", fps=24)

        # Cleanup
        os.remove(audio_path)
        os.remove(image_path)

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
