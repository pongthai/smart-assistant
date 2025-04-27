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
import sqlite3

from chat_history_manager import ChatHistoryManager

# === API Keys ===
SERPER_API_KEY = "7deff68a61a60c8740b5383e52302972444cfd14"

GPT_MODEL = "gpt-4o"

# ตั้ง Wake Words
WAKE_WORDS = ["สวัสดี", "hey ai"]

STOP_WORDS = ["หยุดพูด", "stop"]

client = OpenAI(api_key  = "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")


# ตัวแปร Global สำหรับควบคุมการเล่นเสียง
current_sound_thread = None
current_audio_file = None  # 🔥 Global var to track filename
current_sound_channel = None
stop_playing = False

conversation_active = False
last_interaction_time = time.time()
wake_word_detected = threading.Event()  # 🔥 ใช้ Event

# Initialize pygame mixer
pygame.mixer.init()

history_manager = ChatHistoryManager()

# === Wake Word Listener ===
def wake_word_listener():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            if conversation_active:
                time.sleep(1)
                continue

            print("👂 (Idle) Listening for Wake Word...")
            try:
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)
                text = recognizer.recognize_google(audio, language="th-TH").lower()
                print(f"🗣️ (Idle) Detected: {text}")
                if any(wake_word in text for wake_word in WAKE_WORDS):
                    print("✅ Wake Word Detected!")
                    wake_word_detected.set()
            except (sr.UnknownValueError, sr.WaitTimeoutError):
                time.sleep(0.1)
            except sr.RequestError as e:
                print(f"❌ Wake Listener error: {e}")
                time.sleep(1)

# === Helper Functions ===
def check_idle(timeout_sec=60):
    global conversation_active, last_interaction_time
    if conversation_active and (time.time() - last_interaction_time > timeout_sec):
        print("⌛ Conversation idle timeout. Going back to Wake Word mode.")
        conversation_active = False
           
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

# === ฟังก์ชันวิเคราะห์ว่า ต้องใช้ History ไหม? ===
def needs_history(user_input: str) -> bool:
    prompt = f"""
พิจารณาข้อความต่อไปนี้: "{user_input}"
จำเป็นต้องใช้ประวัติการสนทนาเก่าหรือไม่ เพื่อเข้าใจหรือให้ข้อมูลที่ถูกต้อง?
ตอบกลับเพียงคำเดียวว่า "Yes" หรือ "No" เท่านั้น
"""
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": "คุณคือผู้ช่วยที่วิเคราะห์ความจำเป็นในการใช้ประวัติการสนทนา"},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    answer = response.choices[0].message.content.strip().lower()
    print(f"🔎 AI วิเคราะห์ว่า: {answer}")
    return answer == "yes"


# === Ask GPT ===
def ask_gpt(question, context):

    system_prompt = (
    "You are a helpful assistant. You have access to live web results. "
    "Use the context provided to answer the user's question. "
    "If the context is not 100 percent complete, you may infer a reasonable answer, but clarify your assumptions. "
    "If the information is truly missing, be honest and say so."
    )

    try:
        prompt = f"""You are an AI assistant. Use the information below to answer the user's question. 
        Only answer from the context, and if unclear, please try your best'

        Context:
        {context}

        Question: {question}
        """

        # วิเคราะห์ว่าใช้ history ไหม
        if needs_history(question):
            try:
                msg = [{"role": "system", "content": system_prompt}] + history_manager.get_history(limit=10) + [{"role": "user", "content": prompt}]                    
            except Exception as e:
                msg = f"❌ MSG error: {e}"
        else:
            msg = [{"role": "system", "content": system_prompt}] + [{"role": "user", "content": prompt}]

        #print("msg = ",msg)

        response = client.chat.completions.create(
            model=GPT_MODEL,
            temperature=0.3,
            messages=msg
        )
        
        reply = response.choices[0].message.content.strip()
        print(f"🤖 ChatGPT: {reply}")

        # Save conversation
        history_manager.add_message("user", question)
        history_manager.add_message("assistant", reply)

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

def is_clear_history_command(text: str) -> bool:
    if text:
        keywords = ["เริ่มบทสนทนาใหม่", "ล้างบทสนทนา"]
        return any(keyword in text.lower() for keyword in keywords)
    else:
        return False

# ฟังก์ชันหลัก: วนรอบ พูด → ถาม → ตอบ → พูด
def main_loop():
    global conversation_active, last_interaction_time

    threading.Thread(target=wake_word_listener, daemon=True).start()

    while True:
        check_idle(timeout_sec=60)

        if not conversation_active:
            print("⌛ Waiting for Wake Word...")
            wake_word_detected.wait()
            wake_word_detected.clear()
            speak("ค่ะ มีอะไรให้ช่วยคะ?")
            conversation_active = True      
      
        user_input = listen_to_voice()

        if user_input :
            # 🔥 เช็คว่าผู้ใช้สั่ง Clear History ไหม
            if is_clear_history_command(user_input):
                history_manager.clear_history()
                speak("เริ่มต้นบทสนทนาใหม่แล้วค่ะ")
                continue  # 🛑 ไม่ต้องส่งไปถาม ChatGPT

            if any(wake_word in user_input for wake_word in STOP_WORDS):
                print("STOP word detected")
                stop_audio()
                continue

                
            context = search_serper(user_input, "web")
            answer = ask_gpt(user_input,context)
            speak(answer)
            last_interaction_time = time.time()
             

if __name__ == "__main__":
    main_loop()