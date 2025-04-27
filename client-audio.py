import asyncio
import websockets
import speech_recognition as sr
import json
from gtts import gTTS
from playsound import playsound
import pyttsx3
import uuid
import os
import pygame
import threading
import time

# Your local server WebSocket URI
SERVER_URI = "ws://192.168.100.101:8010/ws"

# Initialize recognizer and TTS engine
recognizer = sr.Recognizer()
mic = sr.Microphone()
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)
tts_engine.setProperty('volume', 1.0)

pygame.mixer.init()

playback_flag = True

def speak_thai(text):
    print("🤖 ChatGPT:", text)
    tts = gTTS(text=text, lang='th')
    filename = f"tts_{uuid.uuid4().hex}.mp3"
    tts.save(filename)
    #playsound(filename)
    playback_flag = True
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
   
    # Wait until done, then clean up
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
        if (playback_flag == False):
            pygame.mixer.music.stop()
            print("🔇 Playback stopped.")
            break;
        continue

    playback_flag = False
    os.remove(filename)

# Create a thread-safe version
def speak_in_thread(text):
    thread = threading.Thread(target=speak_thai, args=(text,))
    thread.start()
    return thread  # optional: you can use thread.join() if needed
    
def speak(text):
    print("🤖 ChatGPT:", text)
    tts_engine.say(text)
    print("...done ... ")
    tts_engine.runAndWait()
    print("...exit speech ... ")


def listen_for_wake_word():
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("🎤 Waiting for wake word (say 'สวัสดี Pie')...")
        audio = recognizer.listen(source)
    try:
        trigger = recognizer.recognize_google(audio, language="th-TH")
        print("🗣️ Heard:", trigger)
        return "สวัสดี" in trigger or "pie" in trigger.lower()
    except Exception as e:
        print("❌ Wake word error:", e)
        return False

def listen_for_question():
    with mic as source:
        print("🎤 Listening for your question...")
        audio = recognizer.listen(source)
    try:
        question = recognizer.recognize_google(audio, language="th-TH")
        print("🧑 You asked:", question)
        return question
    except Exception as e:
        print("❌ Could not understand:", e)
        return None

async def send_to_server(message):
    try:
        async with websockets.connect(SERVER_URI) as websocket:
            await websocket.send(json.dumps({
                "action": "chat",
                "message": message
            }))
            response = await websocket.recv()
            print("🌐 Raw response:", response)
            response_data = json.loads(response)
            return response_data.get("message", response)
    except Exception as e:
        print("❌ Connection error:", e)
        return "ขออภัย เกิดปัญหาในการเชื่อมต่อ"

async def main_loop():
    while True:
        #if listen_for_wake_word():
            question = listen_for_question()
            if question:
                reply = await send_to_server(question)
                playback_flag = False
                #speak_in_thread(reply)

if __name__ == "__main__":
    asyncio.run(main_loop())