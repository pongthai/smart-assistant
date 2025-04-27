from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import json


client = OpenAI(api_key  = "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")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        try:
            data_json = json.loads(data)
            message = data_json.get("message")
            if not message:
                await websocket.send_text("No message provided.")
                continue

            response = client.chat.completions.create(
               model="gpt-4o",
                messages=[{"role": "user", "content": }]
            )
            print(response.choices[0].message.content)

            reply = response.choices[0].message.content
            await websocket.send_text(json.dumps({"message": reply}))

        except Exception as e:
            await websocket.send_text(f"Error: {str(e)}")