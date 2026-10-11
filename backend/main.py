from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sounddevice as sd
import soundfile as sf
import numpy as np
import wave
import tempfile
import os
import re
import subprocess
import requests
from faster_whisper import WhisperModel
import piper
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """You are Ghost, a personal AI assistant. You are intelligent, concise, and slightly dry in tone.
You respond in plain spoken English only — no markdown, no bullet points, no asterisks.
Keep responses short and conversational unless the user asks for detail.
When you perform an action like opening an app or changing volume, confirm it briefly."""

print("Loading Whisper model...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
print("Whisper ready.")

print("Loading Piper voice...")
piper_voice = piper.PiperVoice.load(
    r"C:\Ghost\models\piper\en_US-lessac-medium.onnx",
    config_path=r"C:\Ghost\models\piper\en_US-lessac-medium.onnx.json"
)
print("Piper ready.")


class TextRequest(BaseModel):
    text: str


# ── VOLUME ───────────────────────────────────────────────────────────────────

def get_volume():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))

def volume_up():
    v = get_volume()
    current = v.GetMasterVolumeLevelScalar()
    v.SetMasterVolumeLevelScalar(min(1.0, current + 0.1), None)
    return f"Volume up to {int(min(1.0, current + 0.1) * 100)}%."

def volume_down():
    v = get_volume()
    current = v.GetMasterVolumeLevelScalar()
    v.SetMasterVolumeLevelScalar(max(0.0, current - 0.1), None)
    return f"Volume down to {int(max(0.0, current - 0.1) * 100)}%."

def set_volume(level):
    v = get_volume()
    v.SetMasterVolumeLevelScalar(level / 100, None)
    return f"Volume set to {level}%."

def mute():
    get_volume().SetMute(1, None)
    return "Muted."

def unmute():
    get_volume().SetMute(0, None)
    return "Unmuted."


# ── HELPERS ──────────────────────────────────────────────────────────────────

def open_url(url):
    subprocess.Popen(["cmd", "/c", "start", url], shell=True)

def open_app(app_name):
    subprocess.Popen(["cmd", "/c", "start", app_name], shell=True)


# ── INTENT DETECTION ─────────────────────────────────────────────────────────

def detect_and_execute(text):
    t = text.lower().strip()

    # Websites
    if "open youtube" in t or "play youtube" in t:
        open_url("https://www.youtube.com")
        return "Opening YouTube."
    if "open google" in t:
        open_url("https://www.google.com")
        return "Opening Google."
    if "open github" in t:
        open_url("https://www.github.com")
        return "Opening GitHub."
    if "open netflix" in t:
        open_url("https://www.netflix.com")
        return "Opening Netflix."
    if "open spotify" in t:
        open_url("https://open.spotify.com")
        return "Opening Spotify."
    if "open reddit" in t:
        open_url("https://www.reddit.com")
        return "Opening Reddit."
    if "open twitter" in t or "open x" in t:
        open_url("https://www.twitter.com")
        return "Opening Twitter."
    if "open instagram" in t:
        open_url("https://www.instagram.com")
        return "Opening Instagram."
    if "open whatsapp" in t:
        open_url("https://web.whatsapp.com")
        return "Opening WhatsApp."
    if "open amazon" in t:
        open_url("https://www.amazon.co.uk")
        return "Opening Amazon."
    if "open twitch" in t:
        open_url("https://www.twitch.tv")
        return "Opening Twitch."
    if "open chatgpt" in t:
        open_url("https://chat.openai.com")
        return "Opening ChatGPT."

    # Web search
    search = re.search(r"(?:search|google|look up|find)(?: for| the web for)? (.+)", t)
    if search:
        query = search.group(1)
        open_url(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return f"Searching for {query}."

    # YouTube search
    yt_search = re.search(r"(?:play|search youtube for|youtube) (.+)", t)
    if yt_search and "open youtube" not in t:
        query = yt_search.group(1)
        open_url(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
        return f"Searching YouTube for {query}."

    # Apps
    if "open notepad" in t:
        subprocess.Popen(["notepad.exe"])
        return "Opening Notepad."
    if "open explorer" in t or "open file explorer" in t or "open files" in t:
        subprocess.Popen(["explorer.exe"])
        return "Opening File Explorer."
    if "open task manager" in t:
        subprocess.Popen(["taskmgr.exe"])
        return "Opening Task Manager."
    if "open settings" in t:
        subprocess.Popen("start ms-settings:", shell=True)
        return "Opening Settings."
    if "open calculator" in t or "open calc" in t:
        subprocess.Popen(["calc.exe"])
        return "Opening Calculator."
    if "open chrome" in t:
        subprocess.Popen(["cmd", "/c", "start", "chrome"], shell=True)
        return "Opening Chrome."
    if "open discord" in t:
        discord_path = os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe")
        subprocess.Popen([discord_path, "--processStart", "Discord.exe"])
        return "Opening Discord."
    if "open vs code" in t or "open vscode" in t or "open visual studio code" in t:
        subprocess.Popen(["cmd", "/c", "start", "code"], shell=True)
        return "Opening VS Code."
    if "open paint" in t:
        subprocess.Popen(["mspaint.exe"])
        return "Opening Paint."
    if "open word" in t:
        subprocess.Popen(["cmd", "/c", "start", "winword"], shell=True)
        return "Opening Word."
    if "open excel" in t:
        subprocess.Popen(["cmd", "/c", "start", "excel"], shell=True)
        return "Opening Excel."
    if "open powerpoint" in t:
        subprocess.Popen(["cmd", "/c", "start", "powerpnt"], shell=True)
        return "Opening PowerPoint."
    if "open camera" in t:
        subprocess.Popen("start microsoft.windows.camera:", shell=True)
        return "Opening Camera."
    if "open clock" in t or "open alarm" in t:
        subprocess.Popen("start ms-clock:", shell=True)
        return "Opening Clock."
    if "open maps" in t:
        subprocess.Popen("start bingmaps:", shell=True)
        return "Opening Maps."

    # Volume
    if "volume up" in t or "turn up" in t or "louder" in t or "increase volume" in t:
        return volume_up()
    if "volume down" in t or "turn down" in t or "quieter" in t or "decrease volume" in t or "lower volume" in t:
        return volume_down()
    if "unmute" in t:
        return unmute()
    if "mute" in t:
        return mute()

    vol_match = re.search(r"(?:set volume|volume)(?: to)? (\d+)", t)
    if vol_match:
        return set_volume(int(vol_match.group(1)))

    # System
    if ("lock" in t and "pc" in t) or "lock screen" in t or "lock computer" in t:
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "PC locked."
    if "cancel shutdown" in t or "abort shutdown" in t:
        subprocess.Popen(["shutdown", "/a"])
        return "Shutdown cancelled."
    if "shutdown" in t or "shut down" in t or "turn off" in t and "pc" in t:
        subprocess.Popen(["shutdown", "/s", "/t", "30"])
        return "Shutting down in 30 seconds. Say cancel shutdown to abort."
    if "restart" in t or "reboot" in t:
        subprocess.Popen(["shutdown", "/r", "/t", "30"])
        return "Restarting in 30 seconds."
    if "sleep" in t and ("pc" in t or "computer" in t):
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return "Going to sleep."
    if "screenshot" in t:
        os.makedirs("C:\\Ghost\\screenshots", exist_ok=True)
        subprocess.Popen(["snippingtool.exe"])
        return "Opening Snipping Tool."

    return None


# ── AUDIO HELPERS ─────────────────────────────────────────────────────────────

def record_audio(duration=5):
    sample_rate = 16000
    print(f"Recording for {duration} seconds...")
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    return np.squeeze(audio), sample_rate

def save_wav(audio_np, sample_rate):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((audio_np * 32767).astype(np.int16).tobytes())
    return tmp_path

def transcribe_audio(tmp_path):
    segments, _ = whisper_model.transcribe(tmp_path)
    os.unlink(tmp_path)
    return " ".join([s.text for s in segments]).strip()

def ask_ghost(user_text):
    response = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "stream": False
    })
    response.raise_for_status()
    return response.json()["message"]["content"]

def speak_text(text):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    with wave.open(tmp_path, "wb") as wav_file:
        piper_voice.synthesize_wav(text, wav_file)
    data, sample_rate = sf.read(tmp_path)
    sd.play(data, sample_rate)
    sd.wait()
    os.unlink(tmp_path)


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "Ghost is online"}

@app.post("/think")
def think(req: TextRequest):
    action_result = detect_and_execute(req.text)
    reply = action_result if action_result else ask_ghost(req.text)
    print(f"Ghost: {reply}")
    return {"reply": reply}

@app.post("/speak")
def speak(req: TextRequest):
    speak_text(req.text)
    return {"status": "spoken"}

@app.post("/transcribe")
def transcribe(duration: int = 5):
    audio_np, sample_rate = record_audio(duration)
    tmp_path = save_wav(audio_np, sample_rate)
    transcript = transcribe_audio(tmp_path)
    print(f"Transcribed: {transcript}")
    return {"transcript": transcript}

@app.post("/voice")
def voice(duration: int = 5):
    audio_np, sample_rate = record_audio(duration)
    tmp_path = save_wav(audio_np, sample_rate)
    transcript = transcribe_audio(tmp_path)
    if not transcript:
        return {"error": "Could not transcribe audio"}
    print(f"You: {transcript}")
    action_result = detect_and_execute(transcript)
    reply = action_result if action_result else ask_ghost(transcript)
    print(f"Ghost: {reply}")
    speak_text(reply)
    return {"transcript": transcript, "reply": reply}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)