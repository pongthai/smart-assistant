# assistant/voice_listener.py

import threading
import time
import speech_recognition as sr

WAKE_WORDS = ["สวัสดี", "hey ai"]
COMMAND_WORDS = {
    "stop": ["หยุดพูด", "หยุด", "เงียบ"],
    "exit": ["ออกจากโปรแกรม", "เลิกทำงาน"]
}

class VoiceListener:
    def __init__(self, assistant_manager):
        self.assistant_manager = assistant_manager
        self.recognizer = sr.Recognizer()

        # 🔥 แยก 2 ไมค์
        self.background_mic = sr.Microphone()
        self.listen_mic = sr.Microphone()

        # Start background listener thread
        threading.Thread(target=self.background_listener, daemon=True).start()

    def background_listener(self):
        with self.background_mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while True:
                try:
                    if not self.assistant_manager.conversation_active:
                        # 📢 Idle mode: Listen for Wake Word
                        print("👂 (Idle) Listening for Wake Word...")
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                        text = self.recognizer.recognize_google(audio, language="th-TH").lower()
                        print(f"🗣️ Detected (Idle): {text}")
                        if any(wake_word in text for wake_word in WAKE_WORDS):
                            print("✅ Wake Word Detected!")
                            self.assistant_manager.wake_word_detected.set()
                    else:
                        # 🧠 Conversation mode: Listen for Commands
                        print("👂 (Conversation) Listening for Commands...")
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=2)
                        text = self.recognizer.recognize_google(audio, language="th-TH").lower()
                        print(f"🗣️ Detected (Conversation): {text}")
                        
                        # Check command
                        if self.detect_command(text, "stop"):
                            print("🛑 Stop command detected")
                            self.assistant_manager.audio_manager.stop_audio()

                        if self.detect_command(text, "exit"):
                            print("👋 Exit command detected")
                            self.assistant_manager.should_exit = True
                            break

                except (sr.UnknownValueError, sr.WaitTimeoutError):
                    time.sleep(0.1)
                except sr.RequestError as e:
                    print(f"❌ Speech Recognition Error: {e}")
                    time.sleep(1)

    def detect_command(self, text, command_type):
        keywords = COMMAND_WORDS.get(command_type, [])
        return any(keyword in text for keyword in keywords)

    def listen(self, timeout=15, phrase_time_limit=10):
        with self.listen_mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            self.recognizer.pause_threshold = 1.5 
            try:
                print("🎙️ Listening(2)...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = self.recognizer.recognize_google(audio, language="th-TH")
                return text.strip()
            except (sr.UnknownValueError, sr.WaitTimeoutError):
                return None
            except sr.RequestError as e:
                print(f"❌ Speech error: {e}")
                return None