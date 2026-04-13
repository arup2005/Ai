from flask import Flask, request, jsonify, send_file
from groq import Groq
from elevenlabs.client import ElevenLabs
from mtranslate import translate
import requests, uuid, os, json

app = Flask(__name__)

# ================== ENV KEYS ==================
GROQ_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")

groq = Groq(api_key=GROQ_KEY)
tts = ElevenLabs(api_key=ELEVEN_KEY)

# ================== MEMORY ==================
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        return json.load(open(MEMORY_FILE))
    return {"history": []}

def save_memory(mem):
    json.dump(mem, open(MEMORY_FILE, "w"))

# ================== ESP STORAGE ==================
latest_command = {"text": "", "emotion": "neutral"}

# ================== TRANSLATE ==================
def to_english(text):
    try:
        return translate(text, "en")
    except:
        return text

# ================== SPEECH TO TEXT ==================
def speech_to_text(file):
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"

        headers = {
            "Authorization": f"Bearer {GROQ_KEY}"
        }

        files = {
            "file": open(file, "rb")
        }

        data = {
            "model": "whisper-large-v3"
        }

        res = requests.post(url, headers=headers, files=files, data=data)

        if res.status_code != 200:
            print("Whisper Error:", res.text)
            return ""

        return res.json().get("text", "")

    except Exception as e:
        print("Speech Error:", e)
        return ""

# ================== SPEECH API ==================
@app.route("/speech", methods=["POST"])
def speech():
    try:
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

    except Exception as e:
        print("Speech Route Error:", e)
        return jsonify({
            "original": "",
            "translated": ""
        })

# ================== AI ASK ==================
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

        # 🤖 AI CALL
        try:
            res = groq.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are Jarvis. Reply short and natural."},
                    {"role": "user", "content": user_text}
                ],
                model="moonshotai/kimi-k2-instruct-0905"
            )

            reply = res.choices[0].message.content

        except Exception as e:
            print("Groq Error:", e)
            reply = "Sorry, AI is not available."

        # 🧠 SIMPLE EMOTION DETECTION
        if any(word in reply.lower() for word in ["great", "awesome", "yes"]):
            emotion = "happy"
        elif any(word in reply.lower() for word in ["no", "not", "error"]):
            emotion = "sad"
        else:
            emotion = "neutral"

        # 📡 UPDATE ESP
        latest_command = {
            "text": user_text,
            "emotion": emotion
        }

        # 🔊 ELEVENLABS VOICE ID (Rachel)
        VOICE_ID = "K24eC7JpUgk8zMtQYrpV"

        audio_path = ""

        try:
            audio = tts.generate(
                text=reply,
                voice=VOICE_ID,
                model="eleven_multilingual_v2"
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
        print("ASK ERROR:", e)

        return jsonify({
            "reply": "Server error occurred",
            "emotion": "sad",
            "audio": ""
        })

# ================== ESP ENDPOINT ==================
@app.route("/esp", methods=["GET"])
def esp():
    return jsonify(latest_command)

# ================== AUDIO ==================
@app.route("/audio/<file>")
def audio(file):
    return send_file(file, mimetype="audio/mpeg")

# ================== HEALTH ==================
@app.route("/")
def home():
    return "Jarvis Server Running 🚀"

# ================== RUN ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
