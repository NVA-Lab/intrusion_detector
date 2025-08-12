import json
import queue
import threading
import time

class AlertManager:
    def __init__(self, max_queue_size=100):
        self.alerts_queue = queue.Queue(maxsize=max_queue_size)
        self._lock = threading.Lock()
        self._last_alert_time = {}
        
    def send_alert(self, code: str, message: str):
        try:
            # 중복 알림 방지 (같은 코드의 알림은 1초 내에 한 번만)
            current_time = time.time()
            if code in self._last_alert_time:
                if current_time - self._last_alert_time[code] < 1.0:
                    return  # 중복 알림 무시
            
            self._last_alert_time[code] = current_time
            
            payload = json.dumps({'code': code, 'message': message})
            with self._lock:
                # 큐가 가득 찬 경우 오래된 메시지 제거
                if self.alerts_queue.full():
                    try:
                        self.alerts_queue.get_nowait()  # 오래된 메시지 제거
                    except queue.Empty:
                        pass
                
                self.alerts_queue.put(payload)
                print(f'[ALERT] {code}: {message}')
                
        except Exception as e:
            print(f'[ALERT ERROR] Failed to send alert: {e}')
        
    def get_alerts_queue(self):
        return self.alerts_queue

    def get_next_alert(self, timeout=10):
        try:
            return self.alerts_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        except Exception as e:
            print(f'[ALERT ERROR] Failed to get alert: {e}')
            return None

class AlertCodes:
    SYSTEM_STARTED = "00"
    PERSON_DETECTED = "01"
    PERSON_LOST = "02"
    STATIONARY_BEHAVIOR = "03"
    INTRUSION_DETECTED = "04"