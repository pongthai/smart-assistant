from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import json
from conversation_manager import ConversationManager

# === API Key ===

client = OpenAI(api_key  = "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")

app = FastAPI()
manager = ConversationManager(model="gpt-4o", max_tokens_per_session=5000)

# Optional: allow cross-origin if testing from browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = manager.create_session()

    await websocket.send_text(json.dumps({"status": "connected", "session_id": session_id}))

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                print ("ping received..")
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            user_message = msg.get("message")

            if not user_message:              
                await websocket.send_text(json.dumps({"error": "No message provided"}))
                continue

            # Add user message to memory
            manager.add_message(session_id, "user", user_message)

            # Get full message history
            messages = manager.get_history(session_id)

            # Call GPT-4o
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                reply = response.choices[0].message.content.strip()
            except Exception as e:
                reply = f"❌ GPT Error: {e}"

            # Save assistant response
            manager.add_message(session_id, "assistant", reply)

            await websocket.send_text(json.dumps({
                "reply": reply,
                "session_id": session_id,
                "tokens_used": manager.get_token_count(session_id)
            }))

    except Exception as e:
        print("WebSocket error:", str(e))
        await websocket.send_text(json.dumps({"error": str(e)}))