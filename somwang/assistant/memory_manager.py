# assistant/memory_manager.py

import sqlite3
import os

class MemoryManager:
    def __init__(self, db_path="memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_message(self, role, content, summary=None):
        self.cursor.execute('INSERT INTO memory (role, content) VALUES (?, ?)', (role, content))
        self.conn.commit()

    def get_recent_memories(self, limit=5):
        self.cursor.execute('SELECT role, content FROM memory ORDER BY id DESC LIMIT ?', (limit,))
        return self.cursor.fetchall()

    def clear_memory(self):
        self.cursor.execute('DELETE FROM memory')
        self.conn.commit()

    def close(self):
        self.conn.close()