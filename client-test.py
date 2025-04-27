import asyncio
import websockets
import json
import aioconsole


SERVER_URL = "ws://192.168.100.101:8010/ws"  # Change to your Mac IP if running remotely

# 🔄 Background keep-alive pinger
async def send_keep_alive(websocket, interval=10):
    try:
        while True:
            await asyncio.sleep(interval)
            await websocket.send(json.dumps({"type": "ping"}))
            #print("📡 Sent ping (keep-alive)")
    except asyncio.CancelledError:
        print("⛔ Ping loop stopped.")
    except Exception as e:
        print("❌ Ping error:", e)

async def chat():
    async with websockets.connect(SERVER_URL,ping_interval=None) as websocket:
        # Receive session ID
        response = await websocket.recv()
        welcome = json.loads(response)
        session_id = welcome.get("session_id")
        print(f"✅ Connected (Session ID: {session_id})")

        # Start background ping loop
        ping_task = asyncio.create_task(send_keep_alive(websocket, interval=10))
        try:
            while True:
                #user_input = input("🧠 You: ")
                user_input = await aioconsole.ainput("🧠 You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break

                await websocket.send(json.dumps({
                    "message": user_input
                }))

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
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    asyncio.run(chat())