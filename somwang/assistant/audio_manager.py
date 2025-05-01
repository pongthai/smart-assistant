# assistant/audio_manager.py

import pygame
import threading
import time
import os
import uuid
import re
from gtts import gTTS
from .progressive_tts_manager import ProgressiveTTSManager
from .logger_config import get_logger

logger = get_logger(__name__)

class AudioManager:
    def __init__(self,assistant_manager):
        logger.info("AudioManager initialized")
        pygame.mixer.init()
        self.assistant_manager = assistant_manager
        self.tts_manager = ProgressiveTTSManager(assistant_manager)

        self.current_audio_file = None
        self.current_sound_channel = None
        self.is_sound_playing = False

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
    
    def speak(self,text):
        self.stop_audio()
        self.tts_manager.speak(text)
   
    def speak_org(self, text):
        try:
            filename = f"temp_{uuid.uuid4()}.mp3"
            cleaned_text = self.clean_text_for_gtts(text)
            print("cleaned text =",cleaned_text)
            tts = gTTS(text=cleaned_text, lang="th")
            tts.save(filename)

            self.stop_audio()

            self.current_audio_file = filename
            threading.Thread(target=self.play_audio, args=(filename,), daemon=True).start()

        except Exception as e:
            print(f"❌ TTS Error: {e}")

    def play_audio(self, filename):
        try:
            self.is_sound_playing = True
            sound = pygame.mixer.Sound(filename)
            self.current_sound_channel = sound.play()           

            def monitor_playback():
                while self.current_sound_channel.get_busy():
                    self.assistant_manager.last_interaction_time = time.time()
                    pygame.time.wait(100)
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
    def stop_audio(self):
        self.tts_manager.stop()
        self.is_sound_playing = False

    def stop_audio_org(self):
        if self.current_sound_channel and self.current_sound_channel.get_busy():
            print("🛑 Stopping audio...")
            self.current_sound_channel.stop()

        if self.current_audio_file and os.path.exists(self.current_audio_file):
            try:
                os.remove(self.current_audio_file)
            except:
                pass

        self.current_audio_file = None
        self.is_sound_playing = False