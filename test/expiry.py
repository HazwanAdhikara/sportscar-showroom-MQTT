# test_expiry.py
import time
import json
from paho.mqtt.client import Client, MQTTv5
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 8883
USERNAME = "kelompokB"
PASSWORD = "hzwnkptrm"

PREFIX = "showroom/sportcar"
EXPIRY_TOPIC = f"{PREFIX}/expiry"

def on_connect(client, userdata, flags, reasonCode, properties):
    print(f"[TestExpiry] Connected with code {reasonCode}")

def run_expiry_scenario():
    client = Client(client_id=f"test_expiry_{int(time.time())}", protocol=MQTTv5)
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()
    client.on_connect = on_connect

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)

    # --- Test 1: MQTT Expiry = 1 detik ---
    topic1 = f"{EXPIRY_TOPIC}/mc_laren_720s"
    payload1 = json.dumps({
        "car_id": "mc_laren_720s",
        "message": "MQTT-level expiry 1s test"
    })
    props1 = Properties(PacketTypes.PUBLISH)
    props1.MessageExpiryInterval = 1
    props1.PayloadFormatIndicator = 1
    client.publish(topic1, payload1, qos=1, retain=False, properties=props1)
    print(f"[TestExpiry] Sent to {topic1} | MQTT Expiry=1s")
    time.sleep(2)

    # --- Test 2: MQTT Expiry = 10 detik ---
    topic2 = f"{EXPIRY_TOPIC}/porsche_911"
    payload2 = json.dumps({
        "car_id": "porsche_911",
        "message": "MQTT-level expiry 10s test"
    })
    props2 = Properties(PacketTypes.PUBLISH)
    props2.MessageExpiryInterval = 10
    props2.PayloadFormatIndicator = 1
    client.publish(topic2, payload2, qos=1, retain=False, properties=props2)
    print(f"[TestExpiry] Sent to {topic2} | MQTT Expiry=10s")
    time.sleep(2)

    # --- Test 3: Application-Level Expiry ---
    topic3 = f"{EXPIRY_TOPIC}/app_level"
    now_ts = time.time()
    payload3 = json.dumps({
        "car_id": "app_level",
        "message": "App-level expiry test",
        "expiry": now_ts + 2
    })
    props3 = Properties(PacketTypes.PUBLISH)
    props3.MessageExpiryInterval = 10
    props3.PayloadFormatIndicator = 1
    client.publish(topic3, payload3, qos=1, retain=False, properties=props3)
    print(f"[TestExpiry] Sent to {topic3} | App-level expiry=now+2s")

    print("[TestExpiry] Waiting 5s to observe subscriber behavior...")
    time.sleep(5)

    client.loop_stop()
    client.disconnect()
    print("[TestExpiry] Done. Cek log subscriber.py untuk detail.")

if __name__ == "__main__":
    run_expiry_scenario()
