import speech_recognition as sr
from gtts import gTTS
from openai import OpenAI
import os
import uuid
import threading
import pygame
import time
import sqlite3
import requests
from pynput import keyboard

from chat_history_manager import ChatHistoryManager
#test  

# --- Settings ---
SERPER_API_KEY = "7deff68a61a60c8740b5383e52302972444cfd14"
GPT_MODEL = "gpt-4o"
WAKE_WORDS = ["สวัสดี", "hey ai"]
STOP_WORDS = ["หยุดพูด", "stop"]
IDLE_TIMEOUT = 60  # sec

class AssistantManager:
    def __init__(self):
        self.client = OpenAI(api_key  = "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")
        self.history_manager = ChatHistoryManager()
        self.conversation_active = False
        self.last_interaction_time = time.time()
        self.wake_word_detected = threading.Event()

        self.current_audio_file = None
        self.current_sound_thread = None
        self.current_sound_channel = None

        pygame.mixer.init()
        threading.Thread(target=self.wake_word_listener, daemon=True).start()

    def realtime_keyboard_listener(self):
        def on_press(key):
            try:
                if key.char.lower() == 's':
                    print("🛑 Stop key pressed (real-time)")
                    self.stop_audio()
            except AttributeError:
                pass  # For special keys like ctrl, shift etc.

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True  # ทำให้ thread ปิดอัตโนมัติตอนจบโปรแกรม
        listener.start()

    # === Audio ===
    def play_audio(self, filename):
        try:
            sound = pygame.mixer.Sound(filename)
            self.current_sound_channel = sound.play()
            while self.current_sound_channel.get_busy():
                pygame.time.wait(100)
        except Exception as e:
            print(f"❌ Error playing sound: {e}")
        finally:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except:
                    pass

    def speak(self, text):
        try:
            filename = f"temp_{uuid.uuid4()}.mp3"
            tts = gTTS(text=text, lang="th")
            tts.save(filename)

            self.stop_audio()

            self.current_audio_file = filename
            self.current_sound_thread = threading.Thread(target=self.play_audio, args=(filename,))
            self.current_sound_thread.start()
        except Exception as e:
            print(f"❌ TTS Error: {e}")

    def stop_audio(self):
        if self.current_sound_channel and self.current_sound_channel.get_busy():
            self.current_sound_channel.stop()
        if self.current_sound_thread and self.current_sound_thread.is_alive():
            self.current_sound_thread.join()
        if self.current_audio_file and os.path.exists(self.current_audio_file):
            try:
                os.remove(self.current_audio_file)
            except:
                pass
        self.current_audio_file = None

    # === Speech Listening ===
    def listen(self, timeout=5, phrase_time_limit=10):             
        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        with mic as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source)
            recognizer.pause_threshold = 1.5   # ✅ เพิ่มตรงนี้ เพื่อให้รอหยุดพูดนานขึ้น
            try:
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = recognizer.recognize_google(audio, language="th-TH")
                return text.strip()
            except (sr.UnknownValueError, sr.WaitTimeoutError):
                return None
            except sr.RequestError as e:
                print(f"❌ Speech error: {e}")
                return None

    def wake_word_listener(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            while True:
                if self.conversation_active:
                    time.sleep(1)
                    continue

                try:
                    print("👂 (Idle) Listening for Wake Word...")
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)
                    text = recognizer.recognize_google(audio, language="th-TH").lower()
                    if any(wake_word in text for wake_word in WAKE_WORDS):
                        print("✅ Wake Word Detected!")
                        self.wake_word_detected.set()
                except (sr.UnknownValueError, sr.WaitTimeoutError):
                    time.sleep(0.1)
                except sr.RequestError as e:
                    print(f"❌ Wake Listener error: {e}")
                    time.sleep(1)

    # === AI Core ===
    def needs_history(self, user_input):
        prompt = f"""
พิจารณาข้อความต่อไปนี้: "{user_input}"
จำเป็นต้องใช้ประวัติการสนทนาเก่าหรือไม่ เพื่อเข้าใจหรือให้ข้อมูลที่ถูกต้อง?
ตอบกลับเพียงคำเดียวว่า "Yes" หรือ "No" เท่านั้น
"""
        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "คุณคือผู้ช่วยที่วิเคราะห์ความจำเป็นในการใช้ประวัติการสนทนา"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        answer = response.choices[0].message.content.strip().lower()
        return answer == "yes"

    def search_serper(self, query, mode="web"):
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

    def ask_gpt(self, question, context):
        system_prompt = (
            "You are a helpful assistant. You have access to live web results. "
            "Answer only based on context."
        )

        try:
            if self.needs_history(question):
                messages = [{"role": "system", "content": system_prompt}] + self.history_manager.get_history(limit=10) + [{"role": "user", "content": question}]
            else:
                messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]

            response = self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0.5
            )
            reply = response.choices[0].message.content.strip()

            # Save conversation
            self.history_manager.add_message("user", question)
            self.history_manager.add_message("assistant", reply)

            return reply
        except Exception as e:
            return f"❌ GPT Error: {e}"

    def is_clear_history_command(self, text):
        if not text:
            return False
        keywords = ["เริ่มบทสนทนาใหม่", "ล้างบทสนทนา", "เริ่มใหม่"]
        return any(keyword in text.lower() for keyword in keywords)

    # === Main Program ===
    def run(self):
        while True:
            if self.conversation_active and (time.time() - self.last_interaction_time > IDLE_TIMEOUT):
                print("⌛ Conversation idle timeout. Going back to Wake Word mode.")
                self.conversation_active = False

            if not self.conversation_active:
                print("⌛ Waiting for Wake Word...")
                self.wake_word_detected.wait()
                self.wake_word_detected.clear()
                self.conversation_active = True
                self.speak("ค่ะ มีอะไรให้ช่วยคะ?")

            user_input = self.listen(timeout=15, phrase_time_limit=10)
            if not user_input:
                continue

            print(f"🗣️ User said: {user_input}")
            self.last_interaction_time = time.time()

            if self.is_clear_history_command(user_input):
                self.history_manager.clear_history()
                self.stop_audio()
                self.speak("เริ่มต้นบทสนทนาใหม่แล้วค่ะ")
                continue

            if any(stop_word in user_input.lower() for stop_word in STOP_WORDS):
                print("Received Stop command.. Stopping Audio..")
                self.stop_audio()
                continue
            
            if not self.current_sound_channel.get_busy():
                print("Sending command to Chat GPT ...")
                context = self.search_serper(user_input)
                reply = self.ask_gpt(user_input, context)            
                self.speak(reply)
                self.last_interaction_time = time.time()
        


if __name__ == "__main__":
    assistant = AssistantManager()
    assistant.realtime_keyboard_listener()  # ✅ Start Real-time Key Listener
    assistant.run()