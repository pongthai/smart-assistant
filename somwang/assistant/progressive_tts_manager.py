import threading
import time
import os
from gtts import gTTS
import pygame
import re
from pythainlp.tokenize import sent_tokenize
import uuid
import platform
from .logger_config import get_logger

logger = get_logger(__name__)

class ProgressiveTTSManager:
    def __init__(self,assistant_manager):
        logger.info("ProgressiveTTSManager initialized")
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
    

    def smart_split_text(self, text, max_len=60):

        text = text.replace("\n", ". \n")  # add a sentence-like marker

        sentences = sent_tokenize(text)
        chunks = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= max_len:
                chunks.append(sentence) 
            else:
                # ตัดเพิ่มตามความยาว
                words = sentence.split()
                temp = ""
                for word in words:
                    if len(temp + " " + word) > max_len:
                        if temp.strip():
                            chunks.append(temp.strip())
                        temp = word
                    else:
                        temp += " " + word
                if temp.strip():
                    chunks.append(temp.strip())


        return chunks

    def generate_chunks(self):     
        try: 
            logger.info("Enter generate_chunks")
            for idx, chunk in enumerate(self.chunks):
                if self.stop_flag.is_set():
                    break  # 🛑 ถ้ามีสั่งหยุด จะไม่ generate ต่อ            
                if not chunk.strip():
                    continue  # ✅ ข้าม chunk ว่าง
                is_macos = platform.system() == "Darwin"
                temp_dir = "/tmp" if is_macos else "/dev/shm"

                filename = f"{temp_dir}/temp_{uuid.uuid4()}.mp3"
                
                cleaned_text = ( self.clean_text_for_gtts(chunk) or "").strip()
                
                if not cleaned_text:
                    logger.error("❌ Input text is empty. Cannot generate TTS. input = %s",chunk)    
                    continue                        
                #print("cleaned_text=",cleaned_text)
                tts = gTTS(text=cleaned_text, lang="th")
                tts.save(filename)
                with self.lock:
                    self.chunk_files.append(filename)
            self.generating_done = True
            logger.info("Exit generate_chunks")

        except AssertionError as e:
            logger.error(f"❗ gTTS error: {e}")
        except ValueError as e:
            logger.error(f"❗ TTS skipped: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during TTS: {e}")
        

    def play_chunks(self):
        idx = 0
        logger.info("🔊 Playing sound")
        while True:
            if self.stop_flag.is_set():
                logger.info("🛑 Stop signal received during playback.")
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

            #print(f"🔊 Playing {filename}")
            sound = pygame.mixer.Sound(filename)
            channel = sound.play()

            while channel.get_busy():
                if self.stop_flag.is_set():
                    channel.stop()
                    logger.info("🛑 Stopped current sound.")
                    break
                self.assistant_manager.last_interaction_time = time.time()
                time.sleep(0.1)

     
    def speak(self, text):
        logger.info("Enter speak")
        self.stop_flag.clear()
        self.chunks = self.smart_split_text(text, max_len=50)
        self.chunk_files = []
        self.generating_done = False

        threading.Thread(target=self.generate_chunks, daemon=True).start()        
        self.play_chunks()
        self.cleanup()

    def stop(self):
        """ 🛑 สั่งหยุดการเล่น/สร้างเสียง """
        logger.info("🛑 Stop requested.")
        self.stop_flag.set()

    def cleanup(self):
        """ ลบไฟล์หลังจากเล่นจบ """
        for file in self.chunk_files:
            try:
                os.remove(file)
            except:
                pass
        self.chunk_files.clear()
        logger.info("🧹 Cleaned up temp audio files.")
