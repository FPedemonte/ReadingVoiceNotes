import streamlit as st
import openai
from tempfile import NamedTemporaryFile
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv
import os
from openai import OpenAI
import pytz
# Load environment variables
# load_dotenv()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
        spreadsheet = client.open_by_key('1q1z7cl5vgIVNjGWGSH340HnnyCi_8Ut04aDw6niT8Ks')
        
        # Select the first worksheet
        worksheet = spreadsheet.get_worksheet(0)
        
        # Example: Append a row of data
        worksheet.append_row(data)
        return True
    except Exception as e:
        st.error(f"Error writing to spreadsheet: {str(e)}")
        return False

def transcribe_audio(audio_file):
    # Save audio bytes to a temporary file
    with open('temp_audio.wav', 'wb') as f:
        # Get bytes from UploadedFile
        f.write(audio_file.getvalue())

    try:
        # Use Whisper API for transcription
        with open('temp_audio.wav', "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        os.remove('temp_audio.wav')  # Clean up the temporary file
        return transcript.text
    except Exception as e:
        st.error(f"Error during transcription: {str(e)}")
        if os.path.exists('temp_audio.wav'):
            os.remove('temp_audio.wav')  # Clean up in case of error
        return None

def main():
    st.title("Gastos Logger :money_with_wings:")
    
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

