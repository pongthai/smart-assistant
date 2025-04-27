import speech_recognition as sr
from gtts import gTTS
from openai import OpenAI
import os
import uuid
import audioop
import requests
import threading
import pygame
import time
from conversation_manager import ConversationManager

# === API Keys ===
SERPER_API_KEY = "7deff68a61a60c8740b5383e52302972444cfd14"

# ตั้ง Wake Words
WAKE_WORDS = ["สวัสดี", "hey ai"]

STOP_WORDS = ["หยุดพูด", "stop"]

client = OpenAI(api_key  = "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")


# ตัวแปร Global สำหรับควบคุมการเล่นเสียง
current_sound_thread = None
current_audio_file = None  # 🔥 Global var to track filename
current_sound_channel = None
stop_playing = False
wake_word_detected = threading.Event()  # 🔥 ใช้ Event

# Initialize pygame mixer
pygame.mixer.init()

manager = ConversationManager(model="gpt-4o", max_tokens_per_session=5000)

def keyboard_listener():
    print("⌨️ Keyboard listener started (press 's' to stop audio)")
    while True:
        key = input()
        if key.lower() == "s":
            stop_audio()

# ฟังก์ชัน: หยุดเสียงที่กำลังเล่น
def stop_audio():
    global current_sound_channel, current_audio_file, current_sound_thread
    if current_sound_channel and current_sound_channel.get_busy():
        print("🛑 Force stopping audio...")
        current_sound_channel.stop()

    if current_sound_thread and current_sound_thread.is_alive():
        current_sound_thread.join()

    if current_audio_file and os.path.exists(current_audio_file):
        try:
            os.remove(current_audio_file)
            print(f"🧹 Deleted audio file: {current_audio_file}")
        except Exception as cleanup_error:
            print(f"❗ Error deleting audio file: {cleanup_error}")
        finally:
            current_audio_file = None
        

# ฟังก์ชัน: เล่นเสียงใน Thread แยก
def play_audio(filename):
    global current_sound_channel
    try:
        print("🔊 Playing sound...")
        sound = pygame.mixer.Sound(filename)
        current_sound_channel = sound.play()
        while current_sound_channel.get_busy():
            pygame.time.wait(100)
    except Exception as e:
        print(f"❌ Error playing sound: {e}")
    
    finally:
        # ✅ After playback finished, clean up
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"🧹 Deleted audio file: {filename}")
            except Exception as cleanup_error:
                print(f"❗ Error deleting file {filename}: {cleanup_error}")
            

# ฟังก์ชัน: พูดข้อความออกลำโพง
def speak(text):
    global current_sound_thread, stop_playing, current_audio_file
    try:
        filename = f"temp_{uuid.uuid4()}.mp3"
        tts = gTTS(text=text, lang="th")
        tts.save(filename)
        current_audio_file = filename  # Save filename for cleanup

        # หยุดเสียงเก่าถ้ามี
        if current_sound_thread and current_sound_thread.is_alive():
            stop_audio()

        stop_playing = False
        current_sound_thread = threading.Thread(target=play_audio, args=(filename,))
        current_sound_thread.start()

    except Exception as e:
        print(f"❌ TTS Error: {e}")

def listen_for_speech(timeout=5, phrase_time_limit=15, language="th-TH", rms_threshold=300):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    recognizer.pause_threshold = 1.5         # allow longer pauses between words

    with mic as source:
        #print("🎤 Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        #print(f"🎚️ Energy threshold: {recognizer.energy_threshold}")

        print("🕒 Listening...")
        try:
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            print("❌ No speech detected (timeout).")
            return None

    # Check raw energy (RMS)
    raw_data = audio.get_raw_data()
    rms = audioop.rms(raw_data, 2)
    #print(f"🔊 Detected RMS Energy: {rms}")

    if rms < rms_threshold:
        #print("🤫 Detected silence or very low volume.")
        return None

    # Try recognizing speech
    try:
        transcript = recognizer.recognize_google(audio, language=language)
        print("🗣️ Recognized Speech:", transcript)
        return transcript
    except sr.UnknownValueError:
        #print("❌ Could not understand the audio.")
        return None
    except sr.RequestError as e:
        print(f"⚠️ API error: {e}")
        return None


# === Ask GPT ===
def ask_gpt(question, context):
    prompt = f"""You are an AI assistant. Use the information below to answer the user's question. 
Only answer from the context, and if unclear, please try your best'

Context:
{context}

Question: {question}
"""
    system_prompt = (
    "You are a helpful assistant. You have access to live web results. "
    "Use the context provided to answer the user's question. "
    "If the context is not 100 percent complete, you may infer a reasonable answer, but clarify your assumptions. "
    "If the information is truly missing, be honest and say so."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        reply = response.choices[0].message.content.strip()
        print(f"🤖 ChatGPT: {reply}")
    except Exception as e:
        reply = f"❌ GPT error: {e}"
  
    return reply
     

# === Search Serper (Web or News) ===
def search_serper(query, mode="web"):
    endpoint = "search" if mode == "web" else "news"
    url = f"https://google.serper.dev/{endpoint}"
    headers = { "X-API-KEY": SERPER_API_KEY }
    payload = { "q": query }

    res = requests.post(url, headers=headers, json=payload)
    data = res.json()
    results = data.get("organic" if mode == "web" else "news", [])[:3]

    if not results:
        return "No results found."

    context = "\n".join([
        f"- {item['title']} ({item.get('link', '')}): {item.get('snippet', '')}"
        for item in results
    ])
    return context


# ฟังก์ชัน: ฟังเสียงและรู้จัก Wake Word
def listen_for_wake_word(timeout=3, phrase_time_limit=3):
    
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    recognizer.pause_threshold = 1.5         # allow longer pauses between words

    with mic as source:
        print("👂 Listening for wake word...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            text = recognizer.recognize_google(audio, language="th-TH").lower()
            print(f"🗣️ You said (WW): {text}")
            return text
        except sr.UnknownValueError:
            return ""
        except sr.WaitTimeoutError:
            return ""
        except sr.RequestError as e:
            print(f"❌ Speech Recognition error: {e}")
            return ""
        

# ฟังก์ชัน: ฟังเสียงพูดแล้วแปลงเป็นข้อความ
def listen_to_voice(timeout=15, phrase_time_limit=10):
    stop_audio()  # 🛑 หยุดเสียงก่อนเริ่มฟัง!
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    recognizer.pause_threshold = 1.5         # allow longer pauses between words
    
    with mic as source:
        print("🎙️ Listening...")        
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    try:
        
        text = recognizer.recognize_google(audio, language="th-TH")  # พูดภาษาไทย

        print(f"🗣️ You said: {text}")
        return text
    except sr.UnknownValueError:
        print("❓ Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"❌ Speech Recognition error: {e}")
        return None

# ฟังก์ชัน: ส่งคำถามไปถาม ChatGPT (ผ่าน HTTP Request)
def ask_chatgpt(question):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "คุณคือผู้ช่วยที่พูดคุยเป็นภาษาไทยได้."},
                {"role": "user", "content": question}
            ],
            temperature=0.5
        )
        answer = response.choices[0].message.content.strip()
        print(f"🤖 ChatGPT: {answer}")
        return answer
    except Exception as e:
        print(f"❌ Error contacting ChatGPT: {e}")
        return "ขออภัย ฉันไม่สามารถตอบได้ในตอนนี้"



# ฟังก์ชันหลัก: วนรอบ พูด → ถาม → ตอบ → พูด
def main_loop():
   
    while True:
        text = listen_for_wake_word()
        if any(wake_word in text for wake_word in STOP_WORDS):
            print("STOP word detected")
            stop_audio()

        if any(wake_word in text for wake_word in WAKE_WORDS):
            print("✅ Wake word detected!")
            speak("ค่ะ มีอะไรให้ช่วยคะ?")

            question = listen_to_voice()
            if question:
                answer = ask_chatgpt(question)
                speak(answer)
       

if __name__ == "__main__":
    main_loop()