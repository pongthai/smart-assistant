# assistant/config.py

# === API KEYS ===
SERPER_API_KEY = ""
OPENAI_API_KEY = ""
#test

# === Settings ===
GPT_MODEL = "gpt-4o"

WAKE_WORDS = ["สวัสดี", "hey ai"]
COMMAND_WORDS = {
    "stop": ["หยุดพูด", "หยุด", "เงียบ"],
    "exit": ["ออกจากโปรแกรม", "เลิกทำงาน"]
}

IDLE_TIMEOUT = 60  # seconds