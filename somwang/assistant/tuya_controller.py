# --- Tuya Controller Module ---
# File: tuya_controller.py

from tuya_connector import TuyaOpenAPI
from .config import TUYA_ACCESS_ID, TUYA_ACCESS_KEY, TUYA_API_ENDPOINT

import os

 

# Mapping between user command and Tuya device function code
device_map = {
    "โต๊ะอาหาร": {
        "device_id": "ebf8854d356650d8d0gcyb",
        "switch_code": "switch_1"
    },
    "ห้องนั่งเล่น 1": {
        "device_id": "eb9026d5f9d0aea048hvse",
        "switch_code": "switch_1"
    },
    "ห้องนั่งเล่น 2": {
        "device_id": "eb9026d5f9d0aea048hvse",
        "switch_code": "switch_2"
    },
    "หน้าบ้าน": {
        "device_id": "eb9026d5f9d0aea048hvse",
        "switch_code": "switch_3"
    },
    "น้ำพุ": {
        "device_id": "eb42282d53730625bffo8k",
        "switch_code": "switch_1"
    }

}

class TuyaController:
    def __init__(self):
        self.api = TuyaOpenAPI(TUYA_API_ENDPOINT, TUYA_ACCESS_ID, TUYA_ACCESS_KEY)
        self.api.connect()

    def turn_on(self, location):
        if location not in device_map:
            return f"ไม่รู้จักอุปกรณ์สำหรับ {location}"

        device = device_map[location]
        commands = [{"code": device["switch_code"], "value": True}]
        self.api.post(f"/v1.0/iot-03/devices/{device['device_id']}/commands", {"commands": commands})
        return f"เปิดไฟ {location} เรียบร้อยแล้วจ้า"

    def turn_off(self, location):
        if location not in device_map:
            return f"ไม่รู้จักอุปกรณ์สำหรับ {location}"

        device = device_map[location]
        commands = [{"code": device["switch_code"], "value": False}]
        self.api.post(f"/v1.0/iot-03/devices/{device['device_id']}/commands", {"commands": commands})
        return f"ปิดไฟ {location} แล้วน้า"


# --- Thai Voice Command Parser ---
# File: thai_command_parser.py

import re

location_keywords = {
    "โต๊ะอาหาร": ["โต๊ะอาหาร", "ห้องกินข้าว", "โซนทานข้าว"],
    "ห้องนั่งเล่น 1": ["ห้องนั่งเล่น", "โซนโซฟา", "โซนทีวี"],
    "ห้องนั่งเล่น 2": ["บนโต๊ะกาแฟ"],     
    "หน้าบ้าน": ["หน้าบ้าน"],
    "น้ำพุ": ["น้ำพุ"],
    "ตู้ทำน้ำแข็ง": ["ตู้ทำน้ำแข็ง"],
}

def parse_command_thai2(text):
    print("Enter parse command that...")
    text = text.lower().strip()

    action = None
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


# --- Usage example in assistant logic ---

# from tuya_controller import TuyaController
# from thai_command_parser import parse_command_thai
#
# tuya = TuyaController()
# user_input = "เปิดไฟห้องน้ำหน่อยน้า"
#
# action, location = parse_command_thai(user_input)
# if action and location:
#     if action == "turn_on":
#         response = tuya.turn_on(location)
#     elif action == "turn_off":
#         response = tuya.turn_off(location)
# else:
#     response = "ขอโทษจ้า ไม่เข้าใจคำสั่งนั้น"
# speak(response)
