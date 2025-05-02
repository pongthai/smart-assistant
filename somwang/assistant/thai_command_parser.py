# thai_command_parser.py

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
        "โต๊ะอาหาร": "dining_room",
        "ห้องกินข้าว": "dining_room",
        "ห้องนอน": "bedroom",
        "ห้องรับแขก": "living_room",
        "ห้องน้ำ": "bathroom",
        "ห้องครัว": "kitchen",
        "ไฟนอกบ้าน": "outdoor",
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
