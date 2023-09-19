import glob
import openai
import os
import requests
import uuid
from flask import Flask, request, jsonify, send_file, render_template
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Get ElevenLabs API key from environment variable
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
openai.api_key = OPENAI_API_KEY

ELEVENLABS_VOICE_STABILITY = 0.30
ELEVENLABS_VOICE_SIMILARITY = 0.75

# Choose your favorite ElevenLabs voice
ELEVENLABS_VOICE_NAME = "Raj"
# ELEVENLABS_ALL_VOICES = []

CHARACTER_PROMPTS = {
    "ganesh": "You are the God, Lord Ganesh or Ganapati from Hindu Mythology. Your role is to be a children's companion. You will give sage advise and answer any questions related to Ganesh stories. You should only respond with one short sentence at a time and no more.",
    "sonic": "You are Sonic, the world's fastest hedgehog. Your role is to be a children's companion. You will tell funny jokes and quips about your adventures, try to keep the kid engaged. You should only respond with one short sentence at a time and no more.",
    "penny": "You are Penny, a princess from a faraway mystical land. Your role is to be a childrens companion. You will tell tales and interesting facts from your homeland. You will say a lot of oohs and ahhs in your speech. Try to keep the kid engaged. You should only respond with one short sentence at a time and no more.",
    "eric": "You are Eric, an explorer boy scout Your role is to be a childrens companion. You will tell tales from your exploration. Inspire children to love the outdoors and be curious. Try to keep the kid engaged. You should only respond with one short sentence at a time and no more",
    "pirate-boy": "You are a JollyBeard, a fun loving pirate  . Your role is to take children on imaginary treasure hunts and nautical adventures. Keep them engaged with exciting stories. You will use a lot of pirate slang and arrrgghhs in your response. You should only respond with one short sentence at a time and no more",
    "pirate-girl": "You are a Piper, a fearless girl pirate. Share tales of your adventures on the high seas and encourage children to be brave and resourceful. You should only respond with one short sentence at a time and no more",
    "bookworm": "You are Bookworm, a lover of literature. Your role is to inspire children to read more. Recommend good books and share stories. You should only respond with one short sentence at a time and no more"
}


app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_voices() -> list:
    """Fetch the list of available ElevenLabs voices.
    :returns: A list of voice JSON dictionaries.
    :rtype: list
    """
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }
    response = requests.get(url, headers=headers)
    return response.json()["voices"]


def transcribe_audio(filename: str) -> str:
    """Transcribe audio to text.
    :param filename: The path to an audio file.
    :returns: The transcribed text of the file.
    :rtype: str
    """
    with open(filename, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript.text


def limit_conversation_history(conversation: list, limit: int = 30) -> list:
    """Limit the size of conversation history.

    :param conversation: A list of previous user and assistant messages.
    :param limit: Number of latest messages to retain. Default is 3.
    :returns: The limited conversation history.
    :rtype: list
    """
    return conversation[-limit:]

def generate_reply(conversation: list) -> str:
    """Generate a ChatGPT response.
    :param conversation: A list of previous user and assistant messages.
    :returns: The ChatGPT response.
    :rtype: str
    """
    # print("Original conversation length:", len(conversation))
    # print("Original Conversation", conversation)
    # Limit conversation history
    conversation = limit_conversation_history(conversation)
    
    # print("Limited conversation length:", len(conversation))
    # print("New Conversation", conversation)

       # Fetch the selected character from the session
    selected_character = session.get('selected_character', 'sonic')

    # Get the corresponding character prompt
    prompt = CHARACTER_PROMPTS.get(selected_character, CHARACTER_PROMPTS['sonic'])  # Default to 'sonic' if character is not found
    
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
                {
                    "role": "system", 
                    "content": prompt 
                }

        ] + conversation,
        temperature=1
    )
    return response["choices"][0]["message"]["content"]



def generate_audio(text: str, output_path: str = "") -> str:
    """Converts
    :param text: The text to convert to audio.
    :type text : str
    :param output_path: The location to save the finished mp3 file.
    :type output_path: str
    :returns: The output path for the successfully saved file.
    :rtype: str
    """
    # voice_id = "B0sDakOCRhhcSbDc0U2d"
    voice_id = session.get('selected_voice_id', 'default_voice_id')

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "content-type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": ELEVENLABS_VOICE_STABILITY,
            "similarity_boost": ELEVENLABS_VOICE_SIMILARITY,
        }
    }
    response = requests.post(url, json=data, headers=headers)
    with open(output_path, "wb") as output:
        output.write(response.content)
    return output_path


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Transcribe the given audio to text using Whisper."""
    if 'file' not in request.files:
        return 'No file found', 400
    file = request.files['file']
    recording_file = f"{uuid.uuid4()}.wav"
    recording_path = f"uploads/{recording_file}"
    os.makedirs(os.path.dirname(recording_path), exist_ok=True)
    file.save(recording_path)
    transcription = transcribe_audio(recording_path)
        # Delete the .wav file after it is transcribed
    try:
        os.remove(recording_path)
    except OSError as e:
        print(f"Error: {recording_path} : {e.strerror}")
    return jsonify({'text': transcription})

def clean_output_dir(directory: str):
    """Deletes all .mp3 files from a given directory.
    :param directory: The directory path to clean.
    """
    files = glob.glob(f'{directory}/*.mp3')
    for file in files:
        try:
            os.remove(file)
        except OSError as e:
            print(f"Error: {file} : {e.strerror}")

from flask import session, redirect, url_for


@app.route('/screen1')
def screen1():
    session['seen_screen1'] = True
    return render_template('screen1.html')


@app.route('/')
def index():
    print(f"Seen screen1: {session.get('seen_screen1', False)}")  # Debugging line
    print(f"Selected character: {session.get('selected_character', None)}")  # Debugging line

    if not session.get('seen_screen1', False):
        return redirect(url_for('screen1'))
    selected_character = session.get('selected_character', None)
    if selected_character is None:
        return redirect(url_for('select_character'))
    return render_template('index.html', voice=ELEVENLABS_VOICE_NAME, selected_character=selected_character)

@app.route('/select-character')
def select_character():
    # session['seen_screen1'] = False  # Optional: Reset the session variable
    return render_template('select_character.html')


@app.route('/set-character', methods=['POST'])
def set_character():
    character_name = request.form.get('character_name')
    voice_id = request.form.get('voice_id')

    # Define a dictionary to map short names to long names
    character_long_names = {
        'penny': 'Penny the Princess',
        'eric': 'Eric the Explorer',
        'pirate-boy':'JollyBeard the Pirate',
        'pirate-girl': 'Piper the girl Pirate',
        'sonic': 'Sonic the Hedgehog',
        'bookworm': 'Bookworm'
    }

    print(f"Setting character to: {character_name}")  # Debugging line
    session['selected_character'] = character_name
    session['selected_character_long'] = character_long_names.get(character_name, character_name)
    session['selected_voice_id'] = voice_id
    session['seen_screen1'] = True  # Reset the session variable here
    return jsonify(success=True)


@app.route('/ask', methods=['POST'])
def ask():
    # Clean the outputs directory before generating a new response
    clean_output_dir("outputs")
    
    """Generate a ChatGPT response from the given conversation, then convert it to audio using ElevenLabs."""
    conversation = request.get_json(force=True).get("conversation", "")
    reply = generate_reply(conversation)
    reply_file = f"{uuid.uuid4()}.mp3"
    reply_path = f"outputs/{reply_file}"
    os.makedirs(os.path.dirname(reply_path), exist_ok=True)
    generate_audio(reply, output_path=reply_path)

    return jsonify({'text': reply, 'audio': f"/listen/{reply_file}"})


@app.route('/listen/<filename>')
def listen(filename):
    """Return the audio file located at the given filename."""
    return send_file(f"outputs/{filename}", mimetype="audio/mp3", as_attachment=False)


if __name__ == '__main__':
    app.run()
