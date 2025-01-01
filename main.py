import streamlit as st
import sys
import subprocess
import io
import os
from datetime import datetime
import pytz
from pydub import AudioSegment
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import openai


# Add debug information first
st.write("Python version:", sys.version)
try:
    ffmpeg_version = subprocess.check_output(['ffmpeg', '-version']).decode('utf-8').split('\n')[0]
    st.write("FFmpeg version:", ffmpeg_version)
except Exception as e:
    st.write("FFmpeg check error:", str(e))

try:
    from pydub import AudioSegment
    st.write("pydub successfully imported")
except Exception as e:
    st.write("pydub import error:", str(e))

# Initialize OpenAI client with error handling
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    st.write("OpenAI client initialized successfully")
except Exception as e:
    st.error(f"Error initializing OpenAI client: {str(e)}")
    raise e

def setup_google_sheets():
    # Define the scope
    scope = ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive']

    # Use credentials from streamlit secrets
    credentials = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"],
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
    }
    
    # Create credentials object from dictionary
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scope)
    
    # Authorize the client
    client = gspread.authorize(creds)
    return client

def write_to_spreadsheet(data):
    try:
        # Get the client
        client = setup_google_sheets()
        
        # Use spreadsheet ID instead of name
        spreadsheet = client.open_by_key('1vtFjNlNBLcrZwQXfbseHel1Won6_fynJq4ey7WEgPYM')
        
        # Select the first worksheet
        worksheet = spreadsheet.get_worksheet(0)
        
        # Example: Append a row of data
        worksheet.append_row(data)
        return True
    except Exception as e:
        st.error(f"Error writing to spreadsheet: {str(e)}")
        return False

def transcribe_audio(audio_file):
    try:
        # Convert the audio bytes to WAV first
        audio_bytes = audio_file.getvalue()
        audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
        
        # Add error handling for empty audio
        if len(audio) == 0:
            st.error("The audio file appears to be empty")
            return None
            
        # Convert to MP3 with 128kbps
        mp3_buffer = io.BytesIO()
        try:
            audio.export(mp3_buffer, format='mp3', bitrate='128k')
        except Exception as e:
            st.error(f"Error converting audio to MP3: {str(e)}")
            return None
            
        mp3_buffer.seek(0)
        
        # Check file size before sending to API (Whisper has a 25MB limit)
        file_size = mp3_buffer.getbuffer().nbytes
        if file_size > 25 * 1024 * 1024:  # 25MB in bytes
            st.error("Audio file is too large (max 25MB)")
            return None
        
        # Use Whisper API for transcription
        try:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=("audio.mp3", mp3_buffer, "audio/mp3")
            )
            return transcript.text
        except Exception as e:
            st.error(f"Whisper API error: {str(e)}")
            return None
            
    except Exception as e:
        st.error(f"Error during transcription: {str(e)}")
        return None

def main():
    st.title("Reading Voice Notes :speech_balloon:")
    
    # Audio recorder
    audio_bytes = st.audio_input("Click to record", key="audio_recorder")
    
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        
        # Transcribe button
        if st.button("Transcribe and Save"):
            with st.spinner("Transcribing..."):
                transcription = transcribe_audio(audio_bytes)
                
                if transcription:
                    st.success("Transcription complete!")
                    st.write("Transcription:", transcription)
                    
                    # Prepare data for spreadsheet
                    timezone = pytz.timezone('America/Buenos_Aires')
                    current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")
                    data_row = [current_time, transcription]
                    
                    # Save to spreadsheet
                    if write_to_spreadsheet(data_row):
                        st.success("Saved to Google Sheets!")

if __name__ == "__main__":
    main()

