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
import re
from bs4 import BeautifulSoup
from pynput import keyboard

from chat_history_manager import ChatHistoryManager
#test
# --- Settings ---
SERPER_API_KEY = "7dff68a61a60c8740b5383e52302972444cfd14"
GPT_MODEL = "gpt-4o"
WAKE_WORDS = ["สวัสดี", "hey ai"]
STOP_WORDS = ["หยุดพูด", "stop"]
EXIT_WORDS = ["ออกจากโปรแกรม"]
IDLE_TIMEOUT = 60  # sec

class AssistantManager:
    def __init__(self):
        self.history_manager = ChatHistoryManager()
        self.conversation_active = False
        self.last_interaction_time = time.time()
        self.wake_word_detected = threading.Event()

        self.current_audio_file = None
        self.current_sound_thread = None
        self.current_sound_channel = None

        pygame.mixer.init()
        threading.Thread(target=self.wake_word_listener, daemon=True).start()

    def clean_text_for_gtts(self,text):
        # 1. รักษาจุด (.) ระหว่างตัวเลข เช่น 2.14
        text = re.sub(r"(?<=\d)\.(?=\d)", "DOTPLACEHOLDER", text)
        
        # 2. รักษาจุด (.) ติดกับตัวอักษร เช่น U.S.A.
        text = re.sub(r"(?<=\w)\.(?=\w)", "DOTPLACEHOLDER", text)
        
        # 3. กรองเฉพาะ ก-ฮ, a-z, A-Z, 0-9, เว้นวรรค, เครื่องหมาย %, :
        text = re.sub(r"[^ก-๙a-zA-Z0-9\s%:-]", "", text)
        # 4. คืน DOT กลับ
        text = text.replace("DOTPLACEHOLDER", ".")

        # 5. ลบช่องว่างซ้ำ
        text = re.sub(r"\s+", " ", text).strip()

        return text

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
                self.last_interaction_time = time.time()  #when sound is playing, keep interaction time updated

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
            
            cleaned_text = self.clean_text_for_gtts(text)

            tts = gTTS(text=cleaned_text, lang="th")
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

    def summarize_text(self,text):
        if not text:
            return ""
        
        prompt = f"""
    สรุปเนื้อหานี้ให้อยู่ใน 3-5 บรรทัด สำคัญและเข้าใจง่าย:

    {text}
    """

        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content.strip()


    def fetch_webpage_content(self,url):
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text() for p in paragraphs)
            return text.strip()
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return ""

    def search_serper(self,query, top_k=5):
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY
        }
        payload = { "q": query }

        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()

        results = data.get("organic", [])[:top_k]

        return results
    
    def build_context_from_search_results(self,results):
        context_parts = []

        for idx, item in enumerate(results, 1):
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            link = item.get('link', '')

            print(f"🌐 Fetching from {link}")
            webpage_content = self.fetch_webpage_content(link)

            if webpage_content:
                summarized = self.summarize_text(webpage_content)
            else:
                summarized = snippet  # ใช้ Snippet แทนถ้าโหลดเนื้อเว็บไม่ได้

            context_parts.append(f"{idx}. {title}\n{summarized}\nLink: {link}\n")

        final_context = "\n\n".join(context_parts)
        return final_context.strip()


    def ask_gpt(self, question, context):
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
            
            if self.needs_history(question):
                print("need history=yes")
                messages = [{"role": "system", "content": system_prompt}] + self.history_manager.get_history(limit=10) + [{"role": "user", "content": prompt}]
            else:                
                print("need history=no")
                messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]

            response = self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0.3
            )
            reply = response.choices[0].message.content.strip()

            print("ChatGPT :", reply)

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

            if any(exit_word in user_input.lower() for exit_word in EXIT_WORDS):
                break

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
                results = self.search_serper(user_input)
                context = self.build_context_from_search_results(results)

               # print("context = ",context)
                reply = self.ask_gpt(user_input, context)            
                self.speak(reply)
                self.last_interaction_time = time.time()
        


if __name__ == "__main__":
    assistant = AssistantManager()
    assistant.realtime_keyboard_listener()  # ✅ Start Real-time Key Listener
    assistant.run()