from flask import Flask, request, jsonify, send_file
from groq import Groq
from elevenlabs.client import ElevenLabs
import os
import uuid
import speech_recognition as sr

app = Flask(__name__)

# ================= API KEYS =================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tts = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

recognizer = sr.Recognizer()

# ================= AI =================
def generate_reply(text):
    try:
        response = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct-0905",
            messages=[{"role": "user", "content": text}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# ================= SPEECH TO TEXT =================
def speech_to_text(audio_file):
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio).lower()
    except:
        return None

# ================= TEXT TO SPEECH =================
def generate_audio(text):
    filename = f"reply_{uuid.uuid4()}.mp3"

    audio = tts.text_to_speech.convert(
        voice_id="CwhRBWXzGAHq8TQ4Fs17",
        model_id="eleven_multilingual_v2",
        text=text
    )

    with open(filename, "wb") as f:
        f.write(b"".join(audio))

    return filename

# ================= VOICE API =================
@app.route("/voice", methods=["POST"])
def voice():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file"}), 400

        file = request.files["file"]
        filename = f"input_{uuid.uuid4()}.wav"
        file.save(filename)

        text = speech_to_text(filename)

        if not text:
            return jsonify({"error": "Speech not recognized"}), 400

        reply = generate_reply(text)
        audio_file = generate_audio(reply)

        base_url = request.host_url.rstrip("/")

        return jsonify({
            "input": text,
            "reply": reply,
            "audio_url": f"{base_url}/audio/{audio_file}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= AUDIO ROUTE =================
@app.route("/audio/<filename>")
def audio(filename):
    return send_file(filename, mimetype="audio/mpeg")

# ================= HOME =================
@app.route("/")
def home():
    return "Jarvis AI running 🚀"

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
