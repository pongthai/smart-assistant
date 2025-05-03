# voice_command_handler.py

from .thai_command_parser import parse_command_thai
from .tuya_controller import TuyaController
from .audio_manager import AudioManager
#from .latency_logger import LatencyTracker

from .logger_config import get_logger
logger = get_logger(__name__)

class VoiceCommandHandler:
    def __init__(self):        
        self.tuya = TuyaController()
        #self.tracker = LatencyTracker()
    
    
    def parse_command_action(self,command_text):
         # Try smart home command first
        
        action, location = parse_command_thai(command_text)
        logger.debug(f"command_text={command_text} : action={action} : location={location}")
        if action and location:
            logger.info(f"action={action} location={location}")
        
        if action == "turn_on":
            response = self.tuya.turn_on(location)            
        elif action == "turn_off":
            response = self.tuya.turn_off(location)
        else:
            response = None
        
        logger.debug(f"response={response}")
        return response
    
        
                        