# test_request_response.py
import time
import uuid
import json
from paho.mqtt.client import Client, MQTTv5
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 8883
USERNAME = "kelompokB"
PASSWORD = "hzwnkptrm"
PREFIX = "showroom/sportcar"
REQUEST_TOPIC = f"{PREFIX}/request"

# Menyimpan respons yang diterima { request_id: payload_str }
RESPONSES = {}

def on_connect(client, userdata, flags, reasonCode, properties):
    print(f"[ReqRespTester] Connected (code {reasonCode})")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        props = msg.properties
        raw_corr = None
        if hasattr(props, "CorrelationData"):
            raw_corr = props.CorrelationData
        elif hasattr(props, "correlation_data"):
            raw_corr = props.correlation_data
        corr = raw_corr.decode() if isinstance(raw_corr, (bytes, bytearray)) else raw_corr
        print(f"[ReqRespTester] Got response on {msg.topic} | RequestID={corr} | Payload={payload}")
        RESPONSES[corr] = payload
    except Exception as e:
        print(f"[ReqRespTester] Error in on_message: {e}")

def send_request(client, car_id, command="check_inventory", timeout=5.0):
    request_id = str(uuid.uuid4())
    response_topic = f"{PREFIX}/response/{client._client_id.decode()}/{request_id}"

    # Subscribe ke response topic
    client.subscribe(response_topic, qos=1)
    print(f"[ReqRespTester] Subscribed to {response_topic}")

    # Buat payload request
    payload = json.dumps({
        "car_id": car_id,
        "command": command
    })

    # Siapkan properti MQTT5
    props = Properties(PacketTypes.PUBLISH)
    props.ResponseTopic = response_topic
    props.CorrelationData = request_id.encode()
    props.PayloadFormatIndicator = 1

    # Publish request
    client.publish(REQUEST_TOPIC, payload=payload, qos=1, retain=False, properties=props)
    print(f"[ReqRespTester] Sent request Car={car_id} | Command={command} | RequestID={request_id}")

    # Tunggu sampai respons muncul atau timeout
    start = time.time()
    while time.time() - start < timeout:
        if request_id in RESPONSES:
            print(f"[ReqRespTester] Response received for {request_id}: {RESPONSES[request_id]}")
            break
        time.sleep(0.1)
    else:
        print(f"[ReqRespTester] TIMEOUT: No response within {timeout}s for {request_id}")

    # Unsubscribe dan bersihkan
    client.unsubscribe(response_topic)
    RESPONSES.pop(request_id, None)
    print(f"[ReqRespTester] Unsubscribed from {response_topic}\n")

def main():
    client = Client(client_id=f"reqresp_{uuid.uuid4()}", protocol=MQTTv5)
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()  # Gunakan CA public (HiveMQ)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)

    send_request(client, car_id="ferrari_488", command="check_inventory", timeout=5.0)

    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
