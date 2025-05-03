# thai_command_parser.py
import re

location_keywords = {
    "โต๊ะอาหาร": ["โต๊ะอาหาร", "ห้องกินข้าว", "โซนทานข้าว"],
    "ห้องนั่งเล่น 1": ["ห้องนั่งเล่น", "โซนโซฟา", "โซนทีวี"],
    "ห้องนั่งเล่น 2": ["บนโต๊ะกาแฟ"],     
    "หน้าบ้าน": ["หน้าบ้าน"],
    "น้ำพุ": ["น้ำพุ"],
    "ตู้ทำน้ำแข็ง": ["ตู้ทำน้ำแข็ง"],
}

def parse_command_thai_2(text):
    text = text.lower().strip()

    action = None
    print("enter parse commadn text, text = ", text)
    if re.search(r"\b(เปิด|สว่าง)\b", text):
        action = "turn_on"
    elif re.search(r"\b(ปิด|ดับ)\b", text):
        action = "turn_off"
    else:
        return None, None

    for key, variants in location_keywords.items():
        if any(word in text for word in variants):
            return action, key

    return action, None



def parse_command_thai(text):
    """
    Parses Thai smart home command into action and location.
    Example:
        "เปิดไฟในห้องกินข้าว" → ("turn_on", "dining_room")
    """
    if not text:
        return None, None

    text = text.lower()

    # Map of location keywords to device keys
    location_map = {
        "โต๊ะอาหาร": "โต๊ะอาหาร",
        "ห้องกินข้าว": "โต๊ะอาหาร",
        "โซนทานข้าว": "โต๊ะอาหาร",
        "ห้องรับแขก": "ห้องนั่งเล่น 1",
        "โซนโซฟา": "ห้องนั่งเล่น 1",
        "โซนทีวี": "ห้องนั่งเล่น 1",
        "บนโต๊ะกาแฟ": "ห้องนั่งเล่น 2",
        "หน้าบ้าน": "หน้าบ้าน",
        "น้ำพุ": "น้ำพุ",
        "ตู้ทำน้ำแข็ง": "ตู้ทำน้ำแข็ง",
    }

    # Detect ON/OFF commands
    if any(word in text for word in ["เปิด", "เปิดไฟ"]):
        action = "turn_on"
    elif any(word in text for word in ["ปิด", "ปิดไฟ"]):
        action = "turn_off"
    else:
        action = None

    # Match location
    location = None
    for key, value in location_map.items():
        if key in text:
            location = value
            break

    return action, location


