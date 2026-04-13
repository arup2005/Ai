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
    return res.json()["text"]

# ================== SPEECH API ==================
@app.route("/speech", methods=["POST"])
def speech():
    file = request.files["audio"]
    fname = f"{uuid.uuid4()}.wav"
    file.save(fname)

    text = speech_to_text(fname)
    os.remove(fname)

    translated = to_english(text)

    return jsonify({
        "original": text,
        "translated": translated
    })

# ================== AI ASK ==================
@app.route("/ask", methods=["POST"])
def ask():
    global latest_command

    user_text = request.json["text"]

    memory = load_memory()
    history = memory["history"][-5:]

    system_prompt = """
You are Jarvis AI.

Respond in short natural English.

ALWAYS return JSON:
{"reply":"...", "emotion":"happy/sad/angry/neutral/excited"}
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": user_text})

    res = groq.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192"
    )

    content = res.choices[0].message.content

    try:
        data = json.loads(content)
    except:
        data = {"reply": content, "emotion": "neutral"}

    reply = data["reply"]
    emotion = data["emotion"]

    # SAVE MEMORY
    memory["history"].append({"role": "user", "content": user_text})
    memory["history"].append({"role": "assistant", "content": reply})
    save_memory(memory)

    # UPDATE ESP COMMAND
    latest_command = {
        "text": user_text,
        "emotion": emotion
    }

    # TEXT TO SPEECH
    audio = tts.generate(text=reply, voice="Rachel")

    fname = f"{uuid.uuid4()}.mp3"
    with open(fname, "wb") as f:
        f.write(audio)

    return jsonify({
        "reply": reply,
        "emotion": emotion,
        "audio": "/audio/" + fname
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
