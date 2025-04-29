# assistant/audio_manager.py

import pygame
import threading
import time
import os
import uuid
from gtts import gTTS

class AudioManager:
    def __init__(self):
        pygame.mixer.init()
        self.current_audio_file = None
        self.current_sound_channel = None
        self.is_sound_playing = False

    def speak(self, text):
        try:
            filename = f"temp_{uuid.uuid4()}.mp3"
            tts = gTTS(text=text, lang="th")
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