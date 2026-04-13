from flask import Flask, request, jsonify, send_file
from groq import Groq
from elevenlabs.client import ElevenLabs
from mtranslate import translate
import requests, uuid, os, json

app = Flask(__name__)

# KEYS
GROQ_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")

groq = Groq(api_key=GROQ_KEY)
tts = ElevenLabs(api_key=ELEVEN_KEY)

latest_command = {"text": "", "emotion": "neutral"}

# TRANSLATE
def to_english(text):
    try:
        return translate(text, "en")
    except:
        return text

# SPEECH → TEXT
def speech_to_text(file):
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_KEY}"}

        res = requests.post(
            url,
            headers=headers,
            files={"file": open(file, "rb")},
            data={"model": "whisper-large-v3"}
        )

        return res.json().get("text", "")
    except:
        return ""

# SPEECH API
@app.route("/speech", methods=["POST"])
def speech():
    file = request.files["audio"]
    fname = f"{uuid.uuid4()}.wav"
    file.save(fname)

    text = speech_to_text(fname)
    os.remove(fname)

    if not text.strip() or text.strip() == ".":
        text = ""

    return jsonify({
        "original": text,
        "translated": to_english(text)
    })

# ASK API
@app.route("/ask", methods=["POST"])
def ask():
    global latest_command

    try:
        user_text = request.json.get("text", "")

        if not user_text.strip():
            return jsonify({
                "reply": "I didn't hear anything.",
                "emotion": "neutral",
                "audio": ""
            })

        # AI
        try:
            res = groq.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are Jarvis. Reply short."},
                    {"role": "user", "content": user_text}
                ],
                model="moonshotai/kimi-k2-instruct-0905"
            )
            reply = res.choices[0].message.content
        except:
            reply = "AI error"

        emotion = "neutral"

        # ESP UPDATE
        latest_command = {
            "text": user_text,
            "emotion": emotion
        }

        # ELEVENLABS VOICE ID
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

        audio_path = ""

        try:
            audio = tts.generate(
                text=reply,
                voice=VOICE_ID,
                model="eleven_monolingual_v1"
            )

            fname = f"{uuid.uuid4()}.mp3"
            with open(fname, "wb") as f:
                f.write(audio)

            audio_path = "/audio/" + fname

        except Exception as e:
            print("TTS Error:", e)

        return jsonify({
            "reply": reply,
            "emotion": emotion,
            "audio": audio_path
        })

    except Exception as e:
        print("Server Error:", e)

        return jsonify({
            "reply": "Server error",
            "emotion": "sad",
            "audio": ""
        })

# ESP ENDPOINT
@app.route("/esp")
def esp():
    return jsonify(latest_command)

# AUDIO
@app.route("/audio/<file>")
def audio(file):
    return send_file(file, mimetype="audio/mpeg")

@app.route("/")
def home():
    return "Jarvis Running 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
