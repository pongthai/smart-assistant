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

from memory_manager import MemoryManager

#test
# --- Settings ---
SERPER_API_KEY = ""
GPT_MODEL = "gpt-4o"
WAKE_WORDS = ["สวัสดี", "hey ai"]
STOP_WORDS = ["หยุดพูด", "stop"]
EXIT_WORDS = ["ออกจากโปรแกรม"]
IDLE_TIMEOUT = 60  # sec

class AssistantManager:
    def __init__(self):
        self.client = OpenAI(api_key  = "")
        self.should_exit = False
        self.conversation_active = False
        self.last_interaction_time = time.time()
        self.wake_word_detected = threading.Event()
        self.current_audio_file = None
        self.current_sound_thread = None
        self.current_sound_channel = None
        self.is_sound_playing = False
        self.previous_question = None

        pygame.mixer.init()

        #🔥 Start real-time command listener
        threading.Thread(target=self.command_listener, daemon=True).start()

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
            self.is_sound_playing = True
            sound = pygame.mixer.Sound(filename)
            self.current_sound_channel = sound.play()                       

            # ✅ สร้าง thread คอย monitor การเล่น
            def monitor_playback():
                while self.current_sound_channel.get_busy():
                    pygame.time.wait(100)  # รอทุก 100 ms
                    self.last_interaction_time = time.time()    
                # เมื่อเสียงเล่นจบเอง
                print("🎵 Sound playback finished.")
                self.is_sound_playing = False

            threading.Thread(target=monitor_playback, daemon=True).start()

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

            self.current_audio_file = filename
            self.current_sound_thread = threading.Thread(target=self.play_audio, args=(filename,))
            self.current_sound_thread.start()
        except Exception as e:
            print(f"❌ TTS Error: {e}")

    def stop_audio(self):
        if self.current_sound_channel and self.current_sound_channel.get_busy():
            print("🛑 Stopping audio...")
            self.current_sound_channel.stop()

        if self.current_sound_thread and self.current_sound_thread.is_alive():
            print("🧹 Cleaning audio thread...")
            self.current_sound_thread.join(timeout=1)  # ไม่ต้องรอ join นาน

        if self.current_audio_file and os.path.exists(self.current_audio_file):
            try:
                os.remove(self.current_audio_file)
            except:
                pass

        self.current_audio_file = None
        self.is_sound_playing = False 

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

    
    def summarize_for_memory(self,text):
        prompt = f"""
    สรุปข้อความต่อไปนี้ให้อยู่ในรูปแบบที่เข้าใจง่าย กระชับ และเน้นใจความสำคัญ:

    {text}
    """

        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        summary  = response.choices[0].message.content.strip()
        return summary


    def smart_full_flow(self,user_question, memory_manager):
        # วิเคราะห์ความต้องการ
        analysis = self.analyze_question_all_in_one(user_question,self.previous_question)
        need_web = analysis.get("need_web_search", "No") == "Yes"
        need_memory = analysis.get("need_memory", "No") == "Yes"
        need_history = analysis.get("need_conversation_history", "No") == "Yes"

        print(f"📊 Analysis: need_web={need_web}, need_memory={need_memory}, need_history={need_history}")

        context_parts = []

        # 1. Web Search
        if need_web:
            print("🌐 Searching web...")
            search_results = self.search_serper(user_question, top_k=5)
            web_context = self.build_context_from_search_results(search_results)
            context_parts.append(web_context)

        # 2. Memory (Long Term)
        if need_memory:
            print("🧠 Loading memory...")
            recent_memories = memory_manager.get_recent_memories(limit=5)
            memory_text = "\n".join([f"{role.capitalize()}: {summary}" for role, summary in reversed(recent_memories)])
            context_parts.append(memory_text)

        # 3. Conversation History (Short Term)
        if need_history:
            print("🗣️ Loading conversation history...")
            history_text = self.get_conversation_history(memory_manager,limit=5)
            context_parts.append(history_text)

        # รวม Context
        full_context = "\n\n".join(context_parts).strip()

        if not full_context:
            print("🚀 No extra context needed. Asking GPT directly...")
            full_context = ""

        # ส่งถาม GPT
        answer = self.ask_gpt_with_context(user_question, context=full_context)

        print("ChatGPT : ",answer)

        # หลังจากตอบ → บันทึกลง Memory ด้วย
        user_summary = self.summarize_for_memory(user_question)
        memory_manager.add_message("user", user_question, user_summary)

        assistant_summary = self.summarize_for_memory(answer)
        memory_manager.add_message("assistant", answer, assistant_summary)

        return answer

    def get_conversation_history(self,memory_manager, limit=5):
        memories = memory_manager.get_recent_memories(limit=limit)

        if not memories:
            return ""

        context = ""
        for role, summary in reversed(memories):  # เรียงจากเก่า → ใหม่
            context += f"{role.capitalize()}: {summary}\n"

        return context.strip()

    def analyze_question_all_in_one(self,current_question, previous_question=None):
        if previous_question:
            combined_prompt = f"""
    Analyze the following conversation carefully:

    Previous Question:
    "{previous_question}"

    Current Question:
    "{current_question}"

    Answer ONLY in JSON format with three fields:
    - "need_web_search": "Yes" or "No"
    - "need_memory": "Yes" or "No"
    - "need_conversation_history": "Yes" or "No"

    Rules:
    - If the current question alone cannot be fully understood without the previous context, set "need_conversation_history" = "Yes".
    - Other rules about web search and memory apply as usual.

    Respond only with pure JSON. No explanation.
    """
        else:
            combined_prompt = f"""
    Analyze the following user question carefully:

    "{current_question}"

    Answer ONLY in JSON format with three fields:
    - "need_web_search": "Yes" or "No"
    - "need_memory": "Yes" or "No"
    - "need_conversation_history": "Yes" or "No"

    Rules:
    - If the question refers to previous context or is incomplete without it, set "need_conversation_history" = "Yes".

    Respond only with pure JSON. No explanation.
    """

        # 🔥 ส่งไปถาม GPT
        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": combined_prompt}],
            temperature=0
        )

        content = response.choices[0].message.content.strip()

        import json
        cleaned_content = re.sub(r"```(?:json)?\n([\s\S]*?)\n```", r"\1", content.strip())
        result = json.loads(cleaned_content)
        return result
  
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

            if not title and not snippet:
                continue  # ข้ามอันที่ไม่มีเนื้อหาเลย

            # เอา title + snippet มาประกอบกัน
            context_entry = f"{idx}. {title}\n{snippet}\nLink: {link}"
            context_parts.append(context_entry)

        final_context = "\n\n".join(context_parts)
        return final_context.strip()

    def ask_gpt_with_context(self,question, context=""):
        system_prompt = (
            "You are a helpful assistant. "
            "Answer the user's question based only on the provided context if available. "
            "If context is missing or incomplete, do your best to infer a reasonable answer, but clearly mention any assumptions. "
            "If you don't have enough information, politely say so."
        )

        # เตรียม Messages ที่จะส่งเข้า GPT
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # ถ้ามี Context แนบ (เช่น Memory หรือ Web Search หรือ History)
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})

        # แล้วตามด้วยคำถามจริง
        messages.append({"role": "user", "content": f"Question:\n{question}"})

        # เรียก OpenAI API
        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            temperature=0.3,
        )

        self.previous_question = question
        # ดึงคำตอบ
        reply = response.choices[0].message.content.strip()
        return reply

    
    def is_clear_history_command(self, text):
        if not text:
            return False
        keywords = ["เริ่มบทสนทนาใหม่", "ล้างบทสนทนา", "เริ่มใหม่"]
        return any(keyword in text.lower() for keyword in keywords)

# === Real-time Command Listener ===
    def command_listener(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            print("👂 Command Listener started.")

            while True:
                if self.conversation_active:

                    try:
                        
                        audio = recognizer.listen(source, timeout=2, phrase_time_limit=2)
                        command = recognizer.recognize_google(audio, language="th-TH").lower()

                        print(f"🗣️ Heard: {command}")

                        if any(stop_word in command for stop_word in STOP_WORDS):
                            print("🛑 Stop command detected!")
                            self.stop_audio()
                        # 🔥 Check EXIT WORD
                        if any(exit_word in command for exit_word in EXIT_WORDS):
                            print("👋 Exit command detected!")
                            self.should_exit = True
                        
                    except (sr.UnknownValueError, sr.WaitTimeoutError):
                        continue
                    except sr.RequestError as e:
                        print(f"❌ Voice recognition error: {e}")
                        time.sleep(1)
                else:
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

    # === Main Program ===
    def run(self):
        memory_manager = MemoryManager()

        while not self.should_exit:
            if self.conversation_active and (time.time() - self.last_interaction_time > IDLE_TIMEOUT):
                print("⌛ Conversation idle timeout. Going back to Wake Word mode.")
                self.conversation_active = False

            if not self.conversation_active:
                print("⌛ Waiting for Wake Word...")
                self.wake_word_detected.wait()
                self.wake_word_detected.clear()                
                self.speak("ค่ะ มีอะไรให้ช่วยคะ?")
                time.sleep(1)
                self.conversation_active = True
                self.last_interaction_time = time.time()    
            
            if not self.is_sound_playing:
                user_input = self.listen(timeout=15, phrase_time_limit=10)
                if not user_input:
                    continue       

                print(f"🗣️ User said: {user_input}")
                self.last_interaction_time = time.time()                      
                        
                # ✅ ส่งคำถามเข้า smart_full_flow พร้อม MemoryManager
                print("Sending to GPT...")
                answer = self.smart_full_flow(user_input, memory_manager)     
                self.speak(answer)
                self.last_interaction_time = time.time()
       
        # ✅ Exit cleanly
        print("👋 Program exiting... Goodbye!")

if __name__ == "__main__":
    assistant = AssistantManager()
    assistant.realtime_keyboard_listener()  # ✅ Start Real-time Key Listener
    assistant.run()