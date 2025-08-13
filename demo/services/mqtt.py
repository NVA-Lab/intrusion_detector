import time, threading
from demo.services.mqtt_manager import MQTTManager
from demo.config.settings import BROKER_ADDR, BROKER_PORT
from demo.services.mqtt_publisher import MQTTPublisher
import paho.mqtt.client as paho
import json

class MQTTService:
    def __init__(self, stream_manager, detection_processor=None):
        self.publisher = MQTTPublisher()
        self.stream_manager = stream_manager
        self.detection_processor = detection_processor
        self.last_loc_msg = None
        self.last_loc = None
        self.mgr = MQTTManager()
        # 문 열림 감지 관련 코드 제거

    # 문 열림 감지 관련 코드 제거

    def _send_stream_on(self):
        try:
            if not hasattr(self, "_fire_client"):
                self._fire_client = paho.Client()
                self._fire_client.connect(BROKER_ADDR, BROKER_PORT, 60)
            self._fire_client.publish("ptz/stream", "on", qos=0, retain=False)
        except Exception as e:
            print("[MQTT] stream-on publish failed:", e)

    def _send_stream_off(self):
        try:
            if not hasattr(self, "_fire_client"):
                self._fire_client = paho.Client()
                self._fire_client.connect(BROKER_ADDR, BROKER_PORT, 60)
            self._fire_client.publish("ptz/stream", "off", qos=0, retain=False)
        except Exception as e:
            print("[MQTT] stream-off publish failed:", e)