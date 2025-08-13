import sys
import argparse
import paho.mqtt.client as mqtt

BROKER = "61.252.57.136"
PORT   = 4991

def main():
    parser = argparse.ArgumentParser(description="Publish MQTT messages to PTZ topics")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--control",      action="store_true", help="use topic ptz/control")
    group.add_argument("--stream",       action="store_true", help="use topic ptz/stream")
    group.add_argument("--trigger",      action="store_true", help="use topic ptz/trigger")
    group.add_argument("--localization", action="store_true", help="use topic ptz/localization")
    group.add_argument("--zone",         action="store_true", help="use topic Loc/zone/response")
    args = parser.parse_args()

    if args.control:
        topic = "ptz/control"
    elif args.stream:
        topic = "ptz/stream"
    elif args.trigger:
        topic = "ptz/trigger"
    elif args.zone:
        topic = "Loc/zone/response"
    else:
        topic = "ptz/localization"

    cli = mqtt.Client()
    cli.connect(BROKER, PORT, 60)
    cli.loop_start()

    print(f"Publishing to topic '{topic}'. Type messages, or 'q' to quit.")
    if args.zone:
        print("Zone response format examples:")
        print('  {"zone_1": "alert", "zone_2": "neutral", "zone_3": "neutral", "zone_4": "neutral", "zone_5": "neutral"}')
        print('  {"zone_1": "neutral", "zone_2": "alert", "zone_3": "neutral", "zone_4": "neutral", "zone_5": "neutral"}')
        print('  {"zone_1": "neutral", "zone_2": "neutral", "zone_3": "alert", "zone_4": "neutral", "zone_5": "neutral"}')
    
    try:
        for line in sys.stdin:
            msg = line.strip()
            if msg.lower() in {"q", "quit"}:
                break
            cli.publish(topic, msg)
            print(f"→ sent: {msg}")
    finally:
        cli.loop_stop()
        cli.disconnect()

if __name__ == "__main__":
    main()
