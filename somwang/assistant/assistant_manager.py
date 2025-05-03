# assistant/assistant_manager.py

import threading
import time
from .config import IDLE_TIMEOUT, SYSTEM_TONE, HELLO_MSG
from .audio_manager import AudioManager
from .voice_listener import VoiceListener
from .memory_manager import MemoryManager
from .search_manager import SearchManager
from .chat_manager import ChatManager
from .voice_command_handler import VoiceCommandHandler

from .logger_config import get_logger

logger = get_logger(__name__)

class AssistantManager:
    def __init__(self):
        logger.info("AssistantManager initialized")
        # 🔥 เตรียม Event เพื่อ Sync Wake Word
        self.wake_word_detected = threading.Event()
        self.should_exit = False
        self.conversation_active = False
        self.last_interaction_time = time.time()
        self.previous_question = None

        self.audio_manager = AudioManager(self)
        self.memory_manager = MemoryManager()
        self.search_manager = SearchManager()
        self.chat_manager = ChatManager(SYSTEM_TONE)
        self.voice_listener = VoiceListener(self)
        self.voice_command_handler = VoiceCommandHandler()        

        # Start command listener
       # threading.Thread(target=self.voice_listener.command_listener, daemon=True).start()

    def check_idle(self):
        """ถ้าไม่มี interaction นานเกิน IDLE_TIMEOUT ให้กลับไป Idle Mode"""
        if self.conversation_active and (time.time() - self.last_interaction_time > IDLE_TIMEOUT):
            print("⌛ Conversation idle timeout. Going back to Wake Word mode.")
            self.conversation_active = False


    def run(self):
        logger.info("🚀 Assistant Started. Waiting for Wake Word...")

        while not self.should_exit:
            self.check_idle()

            if not self.conversation_active and not self.audio_manager.is_sound_playing:                
                logger.info("⌛ Waiting for Wake Word...")
                self.wake_word_detected.wait()      # ✅ รอ Wake Word
                self.wake_word_detected.clear()     # ✅ เคลียร์ event สำหรับรอบถัดไป
                self.conversation_active = True
                self.audio_manager.speak(HELLO_MSG)
                self.last_interaction_time = time.time()
                time.sleep(1)
                continue            

            if not self.audio_manager.is_sound_playing:
                #logger.info("Start Listening")
                user_voice = self.voice_listener.listen()
                
                if not user_voice:
                    continue
                
                logger.info(f"🗣️ User said: {user_voice}")
                self.last_interaction_time = time.time()

                response = self.voice_command_handler.parse_command_action(user_voice)
                
                #if the user_voice is command then skip - not send to chatGPT
                if not response:
                    continue
                
                # Analyze need (Web search / Memory / History)
                analysis = self.chat_manager.analyze_question_all_in_one(
                    current_question=user_voice,
                    previous_question=self.previous_question
                )

                need_web = analysis.get("need_web_search", "No") == "Yes"
                need_memory = analysis.get("need_memory", "No") == "Yes"
                need_history = analysis.get("need_conversation_history", "No") == "Yes"

                logger.info(f"📊 Analysis: need_web={need_web}, need_memory={need_memory}, need_history={need_history}")

                # Build context
                context_parts = []

                if need_web:
                    logger.info("🌐 Searching web.,")
                    self.audio_manager.speak("รอซักครู่นะ!")
                    search_results = self.search_manager.search_serper(user_voice, top_k=5)
                    web_context = self.search_manager.build_context_from_search_results(search_results)
                    context_parts.append(web_context)
                    logger.info("S Searching web...done")

                if need_memory:
                    logger.info("🧠 Loading memory...")
                    recent_memories = self.memory_manager.get_recent_memories(limit=5)
                    memory_text = "\n".join([f"{role.capitalize()}: {summary}" for role, summary in reversed(recent_memories)])
                    context_parts.append(memory_text)

                if need_history:
                    logger.info("🗣️ Loading conversation history...")
                    history_text = self.get_conversation_history(limit=5)
                    context_parts.append(history_text)

                full_context = "\n\n".join(context_parts).strip()

                if not full_context:
                    logger.info("🚀 No extra context needed.")

                # Ask GPT
                logger.info("Asking ChatGPT..")
                answer = self.chat_manager.ask_gpt_with_context(user_voice, context=full_context)
                logger.info("ChatGPT: %s",answer)
                self.audio_manager.speak(answer)
                self.last_interaction_time = time.time()

                # Save to memory
                self.memory_manager.add_message("user", user_voice)
                self.memory_manager.add_message("assistant", answer)

                # Update previous question
                self.previous_question = user_voice

        logger.info("👋 Program exiting... Goodbye!")
        self.memory_manager.close()

    def get_conversation_history(self, limit=5):
        memories = self.memory_manager.get_recent_memories(limit=limit)

        if not memories:
            return ""

        context = ""
        for role, summary in reversed(memories):
            context += f"{role.capitalize()}: {summary}\n"

        return context.strip()