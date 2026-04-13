from flask import Flask, request, jsonify, send_file
from groq import Groq
from elevenlabs.client import ElevenLabs
from mtranslate import translate
import requests, uuid, os, json

app = Flask(__name__)

# ENV
GROQ_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")

groq = Groq(api_key=GROQ_KEY)
tts = ElevenLabs(api_key=ELEVEN_KEY)

MEMORY_FILE = "memory.json"

# MEMORY
def load_memory():
    if os.path.exists(MEMORY_FILE):
        return json.load(open(MEMORY_FILE))
    return {"history": []}

def save_memory(mem):
    json.dump(mem, open(MEMORY_FILE, "w"))

# TRANSLATE
def to_english(text):
    try:
        return translate(text, "en")
    except:
        return text

# SPEECH → TEXT (Groq Whisper API)
def speech_to_text(file):
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    files = {"file": open(file, "rb")}
    data = {"model": "whisper-large-v3"}

    res = requests.post(url, headers=headers, files=files, data=data)
    return res.json()["text"]

# SPEECH API
@app.route("/speech", methods=["POST"])
def speech():
    file = request.files["audio"]
    fname = f"{uuid.uuid4()}.wav"
    file.save(fname)

    text = speech_to_text(fname)
    os.remove(fname)

    return jsonify({
        "original": text,
        "translated": to_english(text)
    })

# ASK API
@app.route("/ask", methods=["POST"])
def ask():
    user_text = request.json["text"]

    memory = load_memory()
    history = memory["history"][-5:]

    prompt = "You are Jarvis. Reply short with emotion JSON."

    msgs = [{"role": "system", "content": prompt}]
    msgs += history
    msgs.append({"role": "user", "content": user_text})

    res = groq.chat.completions.create(
        messages=msgs,
        model="llama3-70b-8192"
    )

    content = res.choices[0].message.content

    try:
        data = json.loads(content)
    except:
        data = {"reply": content, "emotion": "neutral"}

    reply = data["reply"]
    emotion = data["emotion"]

    memory["history"].append({"role": "user", "content": user_text})
    memory["history"].append({"role": "assistant", "content": reply})
    save_memory(memory)

    audio = tts.generate(text=reply, voice="Rachel")

    fname = f"{uuid.uuid4()}.mp3"
    with open(fname, "wb") as f:
        f.write(audio)

    return jsonify({
        "reply": reply,
        "emotion": emotion,
        "audio": "/audio/" + fname
    })

@app.route("/audio/<file>")
def audio(file):
    return send_file(file, mimetype="audio/mpeg")

@app.route("/")
def home():
    return "Jarvis Running 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)