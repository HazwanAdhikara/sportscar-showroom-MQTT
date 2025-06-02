# test_expiry.py
import time
import json
import uuid
from paho.mqtt.client import Client, MQTTv5
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 8883
USERNAME = "kelompokB"
PASSWORD = "hzwnkptrm"
PREFIX = "showroom/sportcar"
EXPIRY_TOPIC_BASE = f"{PREFIX}/expiry"

def on_connect(client, userdata, flags, reasonCode, properties):
    print(f"[ExpiryTester] Connected (code {reasonCode})")
    # Subscribe ke wildcard expiry
    client.subscribe(f"{EXPIRY_TOPIC_BASE}/+", qos=1)
    print(f"[ExpiryTester] Subscribed to {EXPIRY_TOPIC_BASE}/+ (QoS=1)")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[ExpiryTester] Received on {msg.topic}: {payload}")
    # Cek application-level expiry jika field "expiry" ada
    try:
        data = json.loads(payload)
        if "expiry" in data:
            now = time.time()
            if now > data["expiry"]:
                print(f"[ExpiryTester] → APPLICATION-LEVEL EXPIRED (now={now}, expiry={data['expiry']})")
            else:
                print("[ExpiryTester] → APPLICATION-LEVEL VALID")
    except:
        pass

def main():
    client = Client(client_id=f"expiry_{uuid.uuid4()}", protocol=MQTTv5)
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)

    car_id = "porsche_911"

    # 1. Broker‐level expiry pendek (1 detik)
    props_short = Properties(PacketTypes.PUBLISH)
    props_short.MessageExpiryInterval = 1
    props_short.PayloadFormatIndicator = 1
    payload_short = json.dumps({
        "car_id": car_id,
        "message": "Short‐lived message",
        "timestamp": time.time()
    })
    print("[ExpiryTester] Publishing broker‐level expiry 1s...")
    client.publish(f"{EXPIRY_TOPIC_BASE}/{car_id}", payload=payload_short, qos=1, retain=False, properties=props_short)

    # Tunggu 2 detik (pesan 1s sudah ter‐expire di broker)
    time.sleep(2)

    # 2. Broker‐level expiry panjang (10 detik)
    props_long = Properties(PacketTypes.PUBLISH)
    props_long.MessageExpiryInterval = 10
    props_long.PayloadFormatIndicator = 1
    payload_long = json.dumps({
        "car_id": car_id,
        "message": "Long‐lived message",
        "timestamp": time.time()
    })
    print("[ExpiryTester] Publishing broker‐level expiry 10s...")
    client.publish(f"{EXPIRY_TOPIC_BASE}/{car_id}", payload=payload_long, qos=1, retain=False, properties=props_long)

    # 3. Application‐level expiry: expiry ts = now + 1s
    expiry_ts = time.time() + 1
    payload_app = json.dumps({
        "car_id": car_id,
        "info": "App‐level expiry message",
        "expiry": expiry_ts,
        "timestamp": time.time()
    })
    print("[ExpiryTester] Publishing application‐level expiry (1s)...")
    client.publish(f"{EXPIRY_TOPIC_BASE}/{car_id}", payload=payload_app, qos=1, retain=False)

    # Tunggu 5 detik untuk menerima pesan yang valid dan expired
    time.sleep(5)

    client.loop_stop()
    client.disconnect()
    print("[ExpiryTester] Done.")

if __name__ == "__main__":
    main()
