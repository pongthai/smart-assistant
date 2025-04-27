import sqlite3
from typing import List, Dict

class ChatHistoryManager:
    def __init__(self, db_path="chat_history.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_table()

    def create_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,  -- 'user' or 'assistant'
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def add_message(self, role: str, content: str):
        with self.conn:
            self.conn.execute(
                "INSERT INTO messages (role, content) VALUES (?, ?)",
                (role, content)
            )

    def get_history(self, limit: int = 10) -> List[Dict[str, str]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT role, content FROM (
                SELECT id, role, content FROM messages ORDER BY id DESC LIMIT ?
            ) subquery ORDER BY id ASC
        """, (limit,))
        rows = cursor.fetchall()
        return [{"role": role, "content": content} for role, content in rows]

    def clear_history(self):
        with self.conn:
            self.conn.execute("DELETE FROM messages")