# assistant/chat_manager.py

import re
import json
from openai import OpenAI
from .config import OPENAI_API_KEY, GPT_MODEL

class ChatManager:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def ask_gpt_with_context(self, question, context=""):
        system_prompt = (
            "You are a helpful assistant. "
            "Answer the user's question based only on the provided context if available. "
            "If context is missing or incomplete, do your best to infer a reasonable answer, but clearly mention any assumptions. "
            "If you don't have enough information, politely say so."
        )

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": f"Question:\n{question}"})

        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            temperature=0.3,
        )

        reply = response.choices[0].message.content.strip()
        return reply

    def analyze_question_all_in_one(self, current_question, previous_question=None):
        if previous_question:
            prompt = f"""
Analyze the following conversation carefully:

Previous Question:
"{previous_question}"

Current Question:
"{current_question}"

Answer ONLY in JSON format with three fields:
- "need_web_search": "Yes" or "No"
- "need_memory": "Yes" or "No"
- "need_conversation_history": "Yes" or "No"

Rules:
- If the current question alone cannot be fully understood without the previous context, set "need_conversation_history" = "Yes".

Respond only with pure JSON. No explanation.
"""
        else:
            prompt = f"""
Analyze the following user question carefully:

"{current_question}"

Answer ONLY in JSON format with three fields:
- "need_web_search": "Yes" or "No"
- "need_memory": "Yes" or "No"
- "need_conversation_history": "Yes" or "No"

Rules:
- If the question refers to previous context or is incomplete without it, set "need_conversation_history" = "Yes".

Respond only with pure JSON. No explanation.
"""

        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        content = response.choices[0].message.content.strip()
        cleaned_content = re.sub(r"```(?:json)?\n([\s\S]*?)\n```", r"\1", content.strip())
        result = json.loads(cleaned_content)
        return result