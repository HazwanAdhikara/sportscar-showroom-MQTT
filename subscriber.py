# subscriber.py
import time
import threading
import json
import ssl
from queue import Queue
from paho.mqtt.client import Client, MQTTv5
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

BROKER_HOST = "broker.hivemq.com" # q4229b00.ala.asia-southeast1.emqxsl.com
BROKER_PORT = 8883
USERNAME = "kelompokB"
PASSWORD = "hzwnkptrm"
UNIQUE_TOPIC_PREFIX = "showroom/sportcar"
KEEPALIVE = 5
RATE_LIMIT_SUB = 5
MAX_QUEUE_SIZE = 50

TOPICS_TO_SUBSCRIBE = [
    (f"{UNIQUE_TOPIC_PREFIX}/inventory/+",      2),
    (f"{UNIQUE_TOPIC_PREFIX}/sensor/door/+",    1),
    (f"{UNIQUE_TOPIC_PREFIX}/sensor/hood/+",    1),
    (f"{UNIQUE_TOPIC_PREFIX}/status/+",         1),
    (f"{UNIQUE_TOPIC_PREFIX}/status/+/price",   1),
    (f"{UNIQUE_TOPIC_PREFIX}/flow/+",           1),
    (f"{UNIQUE_TOPIC_PREFIX}/expiry/+",         1),
    (f"{UNIQUE_TOPIC_PREFIX}/request",          1),
    (f"{UNIQUE_TOPIC_PREFIX}/lwt",              1),
]

message_queue = Queue(maxsize=MAX_QUEUE_SIZE)
last_process_time = 0.0

def on_connect(client, userdata, flags, reasonCode, properties):
    print(f"[Subscriber] Connected with result code {reasonCode}")
    for topic, qos in TOPICS_TO_SUBSCRIBE:
        client.subscribe(topic, qos=qos)
        print(f"[Subscriber] Subscribing to {topic} (QoS={qos})")

def on_disconnect(client, userdata, reasonCode, properties):
    print(f"[Subscriber] Disconnected with code {reasonCode}")

def on_subscribe(client, userdata, mid, granted_qos, properties):
    print(f"[Subscriber] Subscribed (MID={mid}, granted QoS={granted_qos})")

def on_message(client, userdata, msg):
    try:
        message_queue.put_nowait(msg)
    except Exception:
        print("[Subscriber] WARNING: Incoming message queue is full. Dropping message.")

def process_messages():
    global last_process_time
    while True:
        msg = message_queue.get()
        now = time.time()
        elapsed = now - last_process_time
        min_interval = 1.0 / RATE_LIMIT_SUB
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        handle_incoming_message(msg)
        last_process_time = time.time()
        message_queue.task_done()

def handle_incoming_message(msg):
    topic = msg.topic
    qos = msg.qos
    retain = msg.retain
    payload = msg.payload.decode()
    props = msg.properties

    print(f"\n[Subscriber] Message received | Topic={topic} | QoS={qos} | Retain={retain}")

    if topic.endswith("/lwt"):
        print(f"[Subscriber] 🔴 LAST WILL: {payload}")
        return

    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/inventory/"):
        try:
            data = json.loads(payload)
            car_id = topic.split("/")[-1]
            units   = data["units_available"]
            price   = data["price"]
            color   = data["color"]
            print(f"[Subscriber][INVENTORY] Car: {car_id} | Units: {units} | Price: {price} | Color: {color}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Subscriber][ERROR] Invalid inventory payload: {e} | Raw: {payload}")
        return

    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/sensor/door/"):
        car_id = topic.split("/")[-1]
        try:
            data = json.loads(payload)
            door_status = data["door_status"]
            print(f"[Subscriber][SENSOR][DOOR] Car: {car_id} | Door is {door_status.upper()}")
        except json.JSONDecodeError:
            print(f"[Subscriber][ERROR] Door payload not valid JSON: Raw: {payload}")
        except KeyError:
            print(f"[Subscriber][ERROR] 'door_status' field missing in payload: {payload}")
        return

    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/sensor/hood/"):
        car_id = topic.split("/")[-1]
        try:
            data = json.loads(payload)
            hood_status = data["hood_status"]
            print(f"[Subscriber][SENSOR][HOOD] Car: {car_id} | Hood is {hood_status.upper()}")
        except json.JSONDecodeError:
            print(f"[Subscriber][ERROR] Hood payload not valid JSON: Raw: {payload}")
        except KeyError:
            print(f"[Subscriber][ERROR] 'hood_status' field missing in payload: {payload}")
        return

    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/status/") and not topic.endswith("/price"):
        try:
            data = json.loads(payload)
            car_id = data.get("car_id", "<unknown>")
            status = data["status"]
            print(f"[Subscriber][STATUS] Car: {car_id} | Status: {status}")
        except json.JSONDecodeError:
            print(f"[Subscriber][ERROR] Status payload not valid JSON: Raw: {payload}")
        except KeyError:
            print(f"[Subscriber][ERROR] 'status' field missing in status payload: {payload}")
        return

    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/status/") and topic.endswith("/price"):
        try:
            data = json.loads(payload)
            car_id = data["car_id"]
            new_price = data["new_price"]
            print(f"[Subscriber][PRICE UPDATE] Car: {car_id} | New Price: {new_price}")
        except json.JSONDecodeError:
            print(f"[Subscriber][ERROR] Price payload not valid JSON: Raw: {payload}")
        except KeyError:
            print(f"[Subscriber][ERROR] 'car_id' or 'new_price' missing in price payload: {payload}")
        return

    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/expiry/"):
        print(f"[Subscriber][EXPIRY‐BROKER] Payload: {payload}")
        return

    if topic == f"{UNIQUE_TOPIC_PREFIX}/request":
        handle_request(msg)
        return

    print(f"[Subscriber] Payload: {payload}")

def handle_request(msg):
    props = msg.properties

    if props:
        resp_topic = props.ResponseTopic if hasattr(props, "ResponseTopic") else None
        raw_corr   = props.CorrelationData if hasattr(props, "CorrelationData") else None
    else:
        resp_topic = None
        raw_corr = None

    if isinstance(raw_corr, (bytes, bytearray)):
        corr = raw_corr.decode()
    else:
        corr = raw_corr

    print(f"[Subscriber][REQ] Processing request. ResponseTopic={resp_topic} | CorrelationData={corr}")

    try:
        data = json.loads(msg.payload.decode())
        car_id = data["car_id"]
        command = data["command"]
    except json.JSONDecodeError:
        print(f"[Subscriber][ERROR] Request payload not valid JSON: Raw: {msg.payload.decode()}")
        return
    except KeyError as e:
        print(f"[Subscriber][ERROR] Missing field in request payload: {e} | Raw: {msg.payload.decode()}")
        return

    if command == "check_inventory":
        response_payload = json.dumps({
            "car_id": car_id,
            "units_available": 3,
            "price": 350000.0,
            "color": "red",
            "request_id": corr
        })
    else:
        response_payload = json.dumps({
            "car_id": car_id,
            "message": f"Unknown command '{command}'",
            "request_id": corr
        })

    if resp_topic and corr:
        props_resp = Properties(PacketTypes.PUBLISH)
        props_resp.CorrelationData = corr.encode() if isinstance(corr, str) else corr
        props_resp.PayloadFormatIndicator = 1
        client.publish(resp_topic, response_payload, qos=1, retain=False, properties=props_resp)
        print(f"[Subscriber][REQ] Sent response for {car_id} to {resp_topic} | CorrData={corr}")
        time.sleep(0.05)

client = Client(
    client_id=f"subscriber_{int(time.time())}",
    protocol=MQTTv5
)
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(
    ca_certs=None,
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS,
    ciphers=None
)

client.on_connect    = on_connect
client.on_disconnect = on_disconnect
client.on_subscribe  = on_subscribe
client.on_message    = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=KEEPALIVE)
client.loop_start()

threading.Thread(target=process_messages, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("[Subscriber] Exiting.")
    client.loop_stop()
    client.disconnect()
