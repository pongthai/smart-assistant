# conversation_manager.py
from typing import List, Dict
import uuid
import tiktoken

class ConversationManager:
    def __init__(self, model="gpt-4o", max_tokens_per_session=5000):
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self.token_usage: Dict[str, int] = {}
        self.model = model
        self.max_tokens = max_tokens_per_session
        #self.encoding = tiktoken.encoding_for_model(model)
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        self.token_usage[session_id] = self._count_tokens(self.sessions[session_id])
        return session_id

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.create_session()
        self.sessions[session_id].append({"role": role, "content": content})
        self.token_usage[session_id] = self._count_tokens(self.sessions[session_id])

        # Auto-trim if tokens exceed max
        if self.token_usage[session_id] > self.max_tokens:
            self._trim_oldest(session_id)

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id] = [
                {"role": "system", "content": "You are a helpful assistant."}
            ]
            self.token_usage[session_id] = self._count_tokens(self.sessions[session_id])

    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message has overhead
            for key, value in message.items():
                num_tokens += len(self.encoding.encode(value))
        num_tokens += 2  # priming tokens
        return num_tokens

    def _trim_oldest(self, session_id: str):
        messages = self.sessions[session_id]
        # keep system + last 4 rounds (8 messages)
        trimmed = [messages[0]] + messages[-8:]
        self.sessions[session_id] = trimmed
        self.token_usage[session_id] = self._count_tokens(trimmed)

    def get_token_count(self, session_id: str) -> int:
        return self.token_usage.get(session_id, 0)
