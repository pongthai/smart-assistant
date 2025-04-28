import sqlite3

class MemoryManager:
    def __init__(self, db_path="memory.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,          -- "user" หรือ "assistant"
                content TEXT,        -- เนื้อหาที่พูด
                summary TEXT,        -- สรุปข้อความสั้นๆ
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_message(self, role, content, summary=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO memory (role, content, summary)
            VALUES (?, ?, ?)
        ''', (role, content, summary))
        self.conn.commit()

    def get_recent_memories(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT role, summary FROM memory
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def close(self):
        self.conn.close()