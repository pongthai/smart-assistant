import threading
import time
import os
from gtts import gTTS
import pygame
import re

class ProgressiveTTSManager:
    def __init__(self,assistant_manager):
        pygame.mixer.init()

        self.assistant_manager = assistant_manager
        self.chunks = []
        self.chunk_files = []
        self.lock = threading.Lock()
        self.generating_done = False
        self.stop_flag = threading.Event()
    
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
    
    def smart_split_text(self, text, max_len=50):
        sentences = re.split(r'(?<=[.!?…])\s+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_len:
                current_chunk += (" " + sentence)
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def generate_chunks(self):
        for idx, chunk in enumerate(self.chunks):
            if self.stop_flag.is_set():
                break  # 🛑 ถ้ามีสั่งหยุด จะไม่ generate ต่อ

            filename = f"chunk_{idx}.mp3"
            cleaned_text = self.clean_text_for_gtts(chunk)
            tts = gTTS(text=cleaned_text, lang="th")
            tts.save(filename)
            with self.lock:
                self.chunk_files.append(filename)
        self.generating_done = True

    def play_chunks(self):
        idx = 0
        while True:
            if self.stop_flag.is_set():
                print("🛑 Stop signal received during playback.")
                break  # 🛑 หยุดเล่นทันที

            with self.lock:
                if idx < len(self.chunk_files):
                    filename = self.chunk_files[idx]
                    idx += 1
                else:
                    if self.generating_done:
                        break
                    time.sleep(0.1)
                    continue

            print(f"🔊 Playing {filename}")
            sound = pygame.mixer.Sound(filename)
            channel = sound.play()

            while channel.get_busy():
                if self.stop_flag.is_set():
                    channel.stop()
                    print("🛑 Stopped current sound.")
                    break
                self.assistant_manager.last_interaction_time = time.time()
                time.sleep(0.1)

     
    def speak(self, text):
        self.stop_flag.clear()
        self.chunks = self.smart_split_text(text, max_len=50)
        self.chunk_files = []
        self.generating_done = False

        threading.Thread(target=self.generate_chunks, daemon=True).start()
        self.play_chunks()
        self.cleanup()

    def stop(self):
        """ 🛑 สั่งหยุดการเล่น/สร้างเสียง """
        print("🛑 Stop requested.")
        self.stop_flag.set()

    def cleanup(self):
        """ ลบไฟล์หลังจากเล่นจบ """
        for file in self.chunk_files:
            try:
                os.remove(file)
            except:
                pass
        self.chunk_files.clear()
        print("🧹 Cleaned up temp audio files.")
