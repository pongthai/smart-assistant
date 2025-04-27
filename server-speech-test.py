from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import json
import requests
from conversation_manager import ConversationManager


# === API Keys ===
SERPER_API_KEY = "7deff68a61a60c8740b5383e52302972444cfd14"

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

# === Ask GPT ===
def ask_gpt(question, context):
    prompt = f"""You are an AI assistant. Use the information below to answer the user's question. 
Only answer from the context, and if unclear, please try your best'

Context:
{context}

Question: {question}
"""
    system_prompt = (
    "You are a helpful assistant. You have access to live web results. "
    "Use the context provided to answer the user's question. "
    "If the context is not 100 percent complete, you may infer a reasonable answer, but clarify your assumptions. "
    "If the information is truly missing, be honest and say so."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"❌ GPT error: {e}"
  
    return reply
     

# === Search Serper (Web or News) ===
def search_serper(query, mode="web"):
    endpoint = "search" if mode == "web" else "news"
    url = f"https://google.serper.dev/{endpoint}"
    headers = { "X-API-KEY": SERPER_API_KEY }
    payload = { "q": query }

    res = requests.post(url, headers=headers, json=payload)
    data = res.json()
    results = data.get("organic" if mode == "web" else "news", [])[:3]

    if not results:
        return "No results found."

    context = "\n".join([
        f"- {item['title']} ({item.get('link', '')}): {item.get('snippet', '')}"
        for item in results
    ])
    return context


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = manager.create_session()

    #await websocket.send_text(json.dumps({"status": "connected", "session_id": session_id}))
    print("session_id =", session_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            text = msg.get("type")
            print ("text =", text)

            if msg.get("type") == "ping":
                print ("ping received..")
                #await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            user_message = msg.get("question")
            print("user_message =", user_message)
            
            if not user_message:              
                #await websocket.send_text(json.dumps({"error": "No message provided"}))
                print("No message provided")
                continue

            # Add user message to memory
            manager.add_message(session_id, "user", user_message)

            # Get full message history
            messages = manager.get_history(session_id)

            mode = msg.get("mode", "web").lower()

            if mode not in ["web", "news"]:
                #await websocket.send_text(json.dumps({"error": "Mode must be 'web' or 'news'."}))
                print("Error : Mode must be 'web' or 'news'.")
                continue

            #await websocket.send_text(json.dumps({"status": "searching"}))
            context = search_serper(user_message, mode)

            #await websocket.send_text(json.dumps({"status": "summarizing"}))
            
            # Call GPT-4o
            reply = ask_gpt(user_message,context)

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