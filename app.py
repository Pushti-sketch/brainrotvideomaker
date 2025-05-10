import streamlit as st
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_audioclips
import numpy as np
import tempfile
import os
from PIL import Image

# --- Default Files (Relative paths for GitHub deployment) ---
DEFAULT_BACKGROUND_MUSIC = "default_bg_music.mp3"
DEFAULT_OVERLAY_VIDEO = "greenscreen_overlay.mp4"

def chroma_key(clip, color_to_remove=(0, 255, 0), tolerance=100):
    """Applies chroma keying to remove a specific color."""
    def mask(get_frame):
        def make_mask(t):
            frame = get_frame(t)
            mask_array = np.all(np.abs(frame - color_to_remove) < tolerance, axis=2)
            return mask_array.astype(float)
        return make_mask
    return clip.set_mask(clip.fl_time(mask, apply_to=['mask']))

def process_media(audio_path, image_path):
    try:
        # Load user uploaded audio and image
        user_audio = AudioFileClip(audio_path)
        user_image = ImageClip(image_path, duration=user_audio.duration)

        # Load default background music and overlay video from the same directory
        bg_music = AudioFileClip(DEFAULT_BACKGROUND_MUSIC)
        overlay_clip = VideoFileClip(DEFAULT_OVERLAY_VIDEO, has_mask=True)

        # Resize the overlay video to the size of the image
        overlay_resized = overlay_clip.resize(user_image.size)

        # Apply chroma keying to the overlay video (assuming green screen)
        overlay_chroma_keyed = chroma_key(overlay_resized)

        # Image scaling animation
        def image_scale(t):
            if t < 1:  # Scale in over 1 second
                return 0 + t * 1  # Scale from 0 to 1
            else:
                return 1

        image_scaled = user_image.resize(image_scale)
        image_scaled = image_scaled.set_duration(user_audio.duration) # Match duration

        # Composite the image and the overlay
        final_video = CompositeVideoClip([image_scaled.set_position("center"), overlay_chroma_keyed.set_position("center")], size=user_image.size)
        final_video = final_video.set_duration(user_audio.duration)

        # Trim background music to the length of the user audio
        bg_music_trimmed = bg_music.subclip(0, user_audio.duration)

        # Combine user audio and background music
        final_audio = concatenate_audioclips([user_audio, bg_music_trimmed])
        final_video = final_video.set_audio(final_audio)

        return final_video

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

st.title("Media Fusion Studio")
st.write("Upload your audio and image to create a combined video with background music and a greenscreen overlay.")

uploaded_audio = st.file_uploader("Upload your audio file (MP3, WAV, etc.)", type=["mp3", "wav", "aac", "ogg"])
uploaded_image = st.file_uploader("Upload your image file (PNG, JPG, etc.)", type=["png", "jpg", "jpeg"])

if uploaded_audio and uploaded_image:
    # Save uploaded files to temporary locations
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(uploaded_audio.name)[1], delete=False) as tmp_audio:
        tmp_audio.write(uploaded_audio.read())
        audio_path = tmp_audio.name

    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(uploaded_image.name)[1], delete=False) as tmp_image:
        tmp_image.write(uploaded_image.read())
        image_path = tmp_image.name

    st.info("Processing your media...")
    final_clip = process_media(audio_path, image_path)

    if final_clip:
        # Save the final video to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            final_clip.write_videofile(tmp_video.name, codec="libx264", audio_codec="aac", fps=24)
            video_path = tmp_video.name

        with open(video_path, "rb") as file:
            st.download_button(
                label="Download Final Video",
                data=file.read(),
                file_name="final_video.mp4",
                mime="video/mp4",
            )

        # Clean up temporary files
        os.remove(audio_path)
        os.remove(image_path)
        os.remove(video_path)
        final_clip.close()

    else:
        st.error("Failed to process the media.")

st.sidebar.header("Default Files Info")
st.sidebar.info(f"Default Background Music: `{DEFAULT_BACKGROUND_MUSIC}`")
st.sidebar.info(f"Default Greenscreen Overlay: `{DEFAULT_OVERLAY_VIDEO}`")
st.sidebar.info("Ensure these default files are in the same directory as your Streamlit script in your GitHub repository.")
