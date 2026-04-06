import os
import tempfile
from flask import Flask, request, jsonify, send_file
from groq import Groq
from serpapi.google_search import GoogleSearch
from elevenlabs.client import ElevenLabs
from mtranslate import translate

app = Flask(__name__)

# ==============================
# 🔑 API KEYS (SET IN CLOUD)
# ==============================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

if not GROQ_API_KEY or not SERPAPI_KEY or not ELEVEN_API_KEY:
    raise Exception("Missing API keys")

client = Groq(api_key=GROQ_API_KEY)
tts_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# ==============================
# 🧠 MEMORY (lightweight)
# ==============================
memory = {}

# ==============================
# 🌍 TRANSLATE
# ==============================
def translate_text(text):
    try:
        return translate(text, "en")
    except:
        return text

# ==============================
# 🌐 SEARCH
# ==============================
def search_google(query):
    try:
        params = {"q": query, "api_key": SERPAPI_KEY}
        results = GoogleSearch(params).get_dict()

        if "answer_box" in results:
            return results["answer_box"].get("answer") or results["answer_box"].get("snippet")

        if "knowledge_graph" in results:
            return results["knowledge_graph"].get("description")

        if "organic_results" in results:
            return results["organic_results"][0].get("snippet")

    except Exception as e:
        return f"Search error: {e}"

    return None

# ==============================
# 🤖 AI
# ==============================
def ask_ai(user_id, prompt):
    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append({"role": "user", "content": prompt})
    memory[user_id] = memory[user_id][-5:]

    messages = [
        {"role": "system", "content": "You are Jarvis. Be short, smart, futuristic."}
    ] + memory[user_id]

    response = client.chat.completions.create(
        model="moonshotai/kimi-k2-instruct-0905",
        messages=messages
    )

    reply = response.choices[0].message.content

    memory[user_id].append({"role": "assistant", "content": reply})

    return reply

# ==============================
# 🧠 ROUTER
# ==============================
def jarvis_brain(user_id, command):
    command = command.lower()

    if any(word in command for word in ["news", "weather", "latest"]):
        result = search_google(command)
        if result:
            return result

    result = search_google(command)
    if result:
        return result

    return ask_ai(user_id, command)

# ==============================
# 🔊 TTS
# ==============================
def generate_audio(text):
    audio_stream = tts_client.text_to_speech.convert(
        voice_id="CwhRBWXzGAHq8TQ4Fs17",
        model_id="eleven_multilingual_v2",
        text=text
    )

    audio_bytes = b"".join(audio_stream)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(audio_bytes)
    tmp.close()

    return tmp.name

# ==============================
# 🌐 API
# ==============================

# 🔹 TEXT API (FAST)
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json

    user_id = data.get("user_id", "esp32")
    text = data.get("text")

    if not text:
        return jsonify({"error": "No text"}), 400

    text = translate_text(text)

    reply = jarvis_brain(user_id, text)

    return jsonify({
        "reply": reply
    })

# 🔹 VOICE API (ESP32 can play)
@app.route("/voice", methods=["POST"])
def voice():
    data = request.json

    user_id = data.get("user_id", "esp32")
    text = data.get("text")

    text = translate_text(text)
    reply = jarvis_brain(user_id, text)

    audio_file = generate_audio(reply)

    return send_file(audio_file, mimetype="audio/mpeg")

# 🔹 HEALTH
@app.route("/")
def home():
    return "Jarvis Cloud is Running 🚀"

# ==============================
# ▶️ RUN
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)