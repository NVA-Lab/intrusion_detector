import autorootcwd
import time
import numpy as np
from flask_socketio import SocketIO
from src.CADA.CADA_process import parse_and_normalize_payload
import paho.mqtt.client as paho
import paho.mqtt.client as mqtt
import threading
from demo.config.settings import (
    BROKER_ADDR, BROKER_PORT, CSI_TOPICS
)

def start_csi_mqtt_thread(message_handler, topics=None, broker_address=None, broker_port=None, daemon=True):
    """
    Run CSI MQTT client in background thread.
    Automatically subscribes to given topics and delivers decoded payload to message_handler.
    """
    topics = topics or CSI_TOPICS
    broker_address = broker_address or BROKER_ADDR
    broker_port = broker_port or BROKER_PORT

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("MQTT connected.")
            for topic in topics:
                client.subscribe(topic)
                print(f"Subscribed to: {topic}")
        else:
            print(f"MQTT connection failed. Code: {rc}")

    def on_message(client, userdata, msg):
        message_handler(msg.topic, msg.payload.decode())

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker_address, broker_port, 60)

    thread = threading.Thread(target=client.loop_forever, daemon=daemon)
    thread.start()

    return thread, client

class MQTTManager:
    def __init__(self, socketio: SocketIO, topics: list, broker_address: str, broker_port: int,
                 subcarriers: int, indices_to_remove: list, buffer_manager, sliding_processors: dict,
                 fps_limit: int = 10):
        self.socketio = socketio
        self.topics = topics
        self.broker_address = broker_address
        self.broker_port = broker_port
        self.subcarriers = subcarriers
        self.indices_to_remove = indices_to_remove
        self.buffer_manager = buffer_manager
        self.sliding_processors = sliding_processors
        self.fps_limit = fps_limit
        self._mqtt_started = False
        self.time_last_emit = {}
        # 문 열림 감지 관련 코드 제거

    def start(self):
        if self._mqtt_started:
            return
        start_csi_mqtt_thread(
            message_handler=self.mqtt_handler,
            topics=self.topics,
            broker_address=self.broker_address,
            broker_port=self.broker_port,
            daemon=True,
        )
        self._mqtt_started = True

    def mqtt_handler(self, topic: str, payload: str):
        now = time.time()
        prev_emit = self.time_last_emit.get(topic, 0.0)

        # 기존 처리 방식은 그대로 유지
        parsed = parse_and_normalize_payload(
            payload, topic, self.subcarriers, self.indices_to_remove,
            self.buffer_manager.mu_bg_dict, self.buffer_manager.sigma_bg_dict)
        if parsed is None:
            return
        amp_z, pkt_time = parsed
        self.buffer_manager.timestamp_buffer[topic].append(pkt_time)
        self.sliding_processors[topic].push(amp_z, pkt_time)

        # Raw CSI 데이터 추출
        try:
            # CSI 문자열에서 raw 데이터 추출
            csi_data_str = payload.split("CSI values: ")[-1].strip()
            csi_values = list(map(int, csi_data_str.split()))
            
            # 복소수 배열로 변환
            csi_complex = [csi_values[i] + 1j * csi_values[i + 1]
                          for i in range(0, len(csi_values), 2)]
            csi_complex = np.array(csi_complex)[:self.subcarriers]
            
            # 노이즈 채널 제거
            if self.indices_to_remove:
                csi_complex = np.delete(csi_complex, self.indices_to_remove)
            
            # 실수부와 허수부를 분리
            csi_real = np.real(csi_complex).tolist()
            csi_imag = np.imag(csi_complex).tolist()
            csi_amplitude = np.abs(csi_complex).tolist()
            
            ts_ms = int(pkt_time.timestamp()*1000)
            
            if (now - prev_emit) < 1.0/self.fps_limit:
                return
            self.time_last_emit[topic] = now
            
            # Raw 데이터와 기존 CADA 결과 함께 전송
            if self.buffer_manager.cada_feature_buffers["activity_detection"][topic]:
                idx = -1
                activity = self.buffer_manager.cada_feature_buffers["activity_detection"][topic][idx]
                flag = self.buffer_manager.cada_feature_buffers["activity_flag"][topic][idx]
                threshold = self.buffer_manager.cada_feature_buffers["threshold"][topic][idx]
                
                self.socketio.emit("cada_result", {
                    "topic": topic,
                    "timestamp_ms": ts_ms,
                    "activity": float(activity),
                    "flag": int(flag),
                    "threshold": float(threshold),
                    "raw_amplitude": csi_amplitude,  # 진폭 추가
                    "raw_real": csi_real,            # 실수부 추가
                    "raw_imag": csi_imag,            # 허수부 추가
                }, namespace="/csi")
            else:
                # CADA 결과가 없더라도 raw 데이터는 전송
                self.socketio.emit("cada_result", {
                    "topic": topic,
                    "timestamp_ms": ts_ms,
                    "raw_amplitude": csi_amplitude,  # 진폭 추가
                    "raw_real": csi_real,            # 실수부 추가
                    "raw_imag": csi_imag,            # 허수부 추가
                }, namespace="/csi")
                
        except Exception as e:
            print(f"[MQTT] Raw CSI 데이터 처리 오류: {e}")
            # 오류 발생 시 기존 방식으로 데이터 전송
            if self.buffer_manager.cada_feature_buffers["activity_detection"][topic]:
                idx = -1
                activity = self.buffer_manager.cada_feature_buffers["activity_detection"][topic][idx]
                flag = self.buffer_manager.cada_feature_buffers["activity_flag"][topic][idx]
                threshold = self.buffer_manager.cada_feature_buffers["threshold"][topic][idx]
                ts_ms = int(pkt_time.timestamp()*1000)
                
                self.socketio.emit("cada_result", {
                    "topic": topic,
                    "timestamp_ms": ts_ms,
                    "activity": float(activity),
                    "flag": int(flag),
                    "threshold": float(threshold),
                }, namespace="/csi")
        # 문 열림 감지 관련 코드 제거

