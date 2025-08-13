from src.CADA.csi_buffer_utils import RealtimeCSIBufferManager 
from src.CADA.CADA_process import SlidingCadaProcessor, load_calibration_data
from demo.utils.mqtt_manager import MQTTManager
from demo.config.settings import (
    CSI_TOPIC, CSI_TOPICS, CSI_WINDOW_SIZE, CSI_STRIDE, CSI_SMALL_WIN_SIZE,
    CSI_SUBCARRIERS, CSI_INDICES_TO_REMOVE, CSI_FPS_LIMIT,
    BROKER_ADDR, BROKER_PORT
)
from flask_socketio import SocketIO

class CADAService:
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.buf_mgr = None
        self.sliding_processors = {}
        self.mqtt_manager = None
        self._initialized = False
        
    def initialize(self):
        if self._initialized:
            return
            
        # 모든 토픽을 구독하도록 변경
        self.buf_mgr = RealtimeCSIBufferManager(CSI_TOPICS)
        load_calibration_data(CSI_TOPICS, self.buf_mgr.mu_bg_dict, self.buf_mgr.sigma_bg_dict)
        
        for topic in CSI_TOPICS:
            self.buf_mgr.cada_ewma_states[topic] = 0.0

        self.sliding_processors = {
            topic: SlidingCadaProcessor(
                topic=topic,
                buffer_manager=self.buf_mgr,
                window_size=CSI_WINDOW_SIZE,
                stride=CSI_STRIDE,
                small_win_size=CSI_SMALL_WIN_SIZE,
                threshold_factor=2.8,
            ) for topic in CSI_TOPICS
        }

        self.mqtt_manager = MQTTManager(
            socketio=self.socketio,
            topics=CSI_TOPICS,  # 모든 토픽 구독
            broker_address=BROKER_ADDR,
            broker_port=BROKER_PORT,
            subcarriers=CSI_SUBCARRIERS,
            indices_to_remove=CSI_INDICES_TO_REMOVE,
            buffer_manager=self.buf_mgr,
            sliding_processors=self.sliding_processors,
            fps_limit=CSI_FPS_LIMIT
        )
        
        self._initialized = True
        
    def start(self):
        if not self._initialized:
            self.initialize()
        if self.mqtt_manager:
            self.mqtt_manager.start()
            
    def get_buffer_manager(self):
        return self.buf_mgr
        
    def get_sliding_processors(self):
        return self.sliding_processors 