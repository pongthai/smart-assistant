from fastapi import FastAPI, WebSocket
from typing import Dict

app = FastAPI()

# Mock user database
users_db = {
    "alice": "1234",
    "bob": "abcd"
}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_json()
        action = data.get("action")

        if action == "login":
            username = data.get("username")
            password = data.get("password")

            if users_db.get(username) == password:
                await websocket.send_json({"status": "success", "message": f"Welcome, {username}!"})
            else:
                await websocket.send_json({"status": "error", "message": "Invalid credentials"})
        else:
            await websocket.send_json({"status": "error", "message": "Unknown action"})