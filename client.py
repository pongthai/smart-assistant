import asyncio
import websockets
import speech_recognition as sr
import json
import audioop

# เปลี่ยนเป็น IP ของ Local Server
SERVER_URI = "ws://192.168.100.101:8010/ws"

async def send_message_to_server(message):
    async with websockets.connect(SERVER_URI) as websocket:
        await websocket.send(json.dumps({
            "action": "chat",
            "message": message
        }))
        response = await websocket.recv()
        decoded_res = response.encode('utf-8').decode('unicode_escape')
        print("ChatGPT:", decoded_res)


def listen_for_speech(timeout=5, phrase_time_limit=15, language="th-TH", rms_threshold=300):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("🎤 Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"🎚️ Energy threshold: {recognizer.energy_threshold}")

        print("🕒 Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            print("❌ No speech detected (timeout).")
            return None

    # Check raw energy (RMS)
    raw_data = audio.get_raw_data()
    rms = audioop.rms(raw_data, 2)
    print(f"🔊 Detected RMS Energy: {rms}")

    if rms < rms_threshold:
        print("🤫 Detected silence or very low volume.")
        return None

    # Try recognizing speech
    try:
        transcript = recognizer.recognize_google(audio, language=language)
        print("🗣️ Recognized Speech:", transcript)
        return transcript
    except sr.UnknownValueError:
        print("❌ Could not understand the audio.")
        return None
    except sr.RequestError as e:
        print(f"⚠️ API error: {e}")
        return None


def listen_and_recognize():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        print("..1.. ")
        audio = recognizer.listen(source)
        print (" .. 2 .. ")
        

    try:
        print("Processing...")
        text = recognizer.recognize_google(audio, language="th-TH")
        print("You said:", text)
        return text
    except sr.UnknownValueError:
        print("Sorry, I couldn't understand.")
    except sr.RequestError as e:
        print("Could not request results; {0}".format(e))
    return None

async def main():
    while True:
        text = listen_for_speech()
        if text:
            await send_message_to_server(text)

if __name__ == "__main__":
    asyncio.run(main())