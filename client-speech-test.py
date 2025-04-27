import asyncio
import websockets
import json
import aioconsole
import speech_recognition as sr
import audioop
import time 

SERVER_URL = "ws://192.168.100.101:8010/ws"  # Change to your Mac IP if running remotely

# 🔄 Background keep-alive pinger
async def send_keep_alive(websocket, interval=10):
    print("send_keep_alive")
    try:        
        while True:
            try:
                await websocket.send(json.dumps({"type": "ping"}))
                print("📡 Sent ping (keep-alive)")            
            except Exception as e:
                print("❌ Error sending ping:", e)
                raise e  # re-raise to exit loop

            try:
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                print("⛔ Sleep cancelled")
                raise
    except asyncio.CancelledError:
        print("⛔ send_keep_alive task cancelled due to WebSocket closed")
    except Exception as e:
        print("❌ Unexpected in keep_alive:", e)
    

def listen_for_speech(timeout=5, phrase_time_limit=15, language="th-TH", rms_threshold=300):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    recognizer.pause_threshold = 1.5         # allow longer pauses between words

    with mic as source:
        #print("🎤 Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        #print(f"🎚️ Energy threshold: {recognizer.energy_threshold}")

        print("🕒 Listening...")
        try:
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            print("❌ No speech detected (timeout).")
            return None

    # Check raw energy (RMS)
    raw_data = audio.get_raw_data()
    rms = audioop.rms(raw_data, 2)
    #print(f"🔊 Detected RMS Energy: {rms}")

    if rms < rms_threshold:
        #print("🤫 Detected silence or very low volume.")
        return None

    # Try recognizing speech
    try:
        transcript = recognizer.recognize_google(audio, language=language)
        print("🗣️ Recognized Speech:", transcript)
        return transcript
    except sr.UnknownValueError:
        #print("❌ Could not understand the audio.")
        return None
    except sr.RequestError as e:
        print(f"⚠️ API error: {e}")
        return None

async def chat():
    async with websockets.connect(SERVER_URL,ping_interval=3,ping_timeout=5 )  as websocket:               
        
        # Receive session ID
        #response = await websocket.recv()
        #welcome = json.loads(response)
        #session_id = welcome.get("session_id")
        #print(f"✅ Connected (Session ID: {session_id})")  
        
        # Start background ping loop          
        #ping_task = asyncio.create_task(send_keep_alive(websocket, interval=5))
        start_keep_alive_thread()
                
        try:
            while True:
                text = listen_for_speech()
                
                if text:
                    print("text =",text)
                    await websocket.send(json.dumps({
                            "question": text,
                            "mode": "web"
                        }))
                else:
                    print("Text returned is None..")
                    continue               
 

                while True:
                    try:
                        reply_raw = await websocket.recv()
                        reply_json = json.loads(reply_raw)

                        if "reply" in reply_json:
                            print(f"🤖 GPT: {reply_json['reply']}")
                            print(f"🧾 Tokens used so far: {reply_json['tokens_used']}\n")
                            break
                        elif "error" in reply_json:
                            print("❌ Error:", reply_json["error"])
                            break
                        elif "status" in reply_json:
                            print(f"ℹ️ {reply_json['status']}")
                        elif "pong" in reply_json:
                            print("pong received..")
                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 Connection closed.")
                        return
        finally:
            print("test")
            #ping_task.cancel()
            # try:
            #     print("test 2")
            #     #await ping_task
            # except asyncio.CancelledError:
            #     pass

if __name__ == "__main__":
    asyncio.run(chat())