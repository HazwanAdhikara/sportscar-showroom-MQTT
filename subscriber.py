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

# --------------------------- CONFIGURASI ---------------------------
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 8883                 # Ganti ke 1883 jika plain MQTT tanpa TLS
USERNAME = "kelompokB"             # (boleh dikosongkan jika broker publik tidak memerlukan auth)
PASSWORD = "hzwnkptrm"
UNIQUE_TOPIC_PREFIX = "showroom/sportcar"
KEEPALIVE = 60
RATE_LIMIT_SUB = 5                 # maksimal pesan yang diproses per detik
MAX_QUEUE_SIZE = 50                # maksimum antrean pesan

# Topik‐topik utama yang akan di‐subscribe
TOPICS_TO_SUBSCRIBE = [
    (f"{UNIQUE_TOPIC_PREFIX}/inventory/+",      2),   # QoS 2: inventory update per car_id
    (f"{UNIQUE_TOPIC_PREFIX}/sensor/door/+",    1),   # QoS 1: sensor pintu (open/closed)
    (f"{UNIQUE_TOPIC_PREFIX}/sensor/hood/+",    1),   # QoS 1: sensor hood (open/closed)
    (f"{UNIQUE_TOPIC_PREFIX}/status/+",         1),   # QoS 1: status umum (available/on display)
    (f"{UNIQUE_TOPIC_PREFIX}/status/+/price",   1),   # QoS 1: perubahan harga
    (f"{UNIQUE_TOPIC_PREFIX}/request",          1),   # QoS 1: untuk request–response
    (f"{UNIQUE_TOPIC_PREFIX}/lwt",              1),   # QoS 1: Last Will
]

# Queue untuk flow control (subscriber side)
message_queue = Queue(maxsize=MAX_QUEUE_SIZE)
last_process_time = 0.0

# --------------------------- CALLBACKS ---------------------------
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
    """
    Semua pesan masuk dimasukkan ke antrean untuk diproses secara teratur.
    """
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

# --------------------------- FUNGSI PEMROSESAN PESAN ---------------------------
def handle_incoming_message(msg):
    topic = msg.topic
    qos = msg.qos
    retain = msg.retain
    payload = msg.payload.decode()
    props = msg.properties

    print(f"\n[Subscriber] Message received | Topic={topic} | QoS={qos} | Retain={retain}")

    # 1. Deteksi Last Will
    if topic.endswith("/lwt"):
        print(f"[Subscriber] 🔴 LAST WILL: {payload}")
        return

    # 2. Inventory Update: showroom/sportcar/inventory/<car_id>
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

    # 3. Sensor Pintu (door): showroom/sportcar/sensor/door/<car_id>
    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/sensor/door/"):
        car_id = topic.split("/")[-1]
        try:
            data = json.loads(payload)
            door_status = data["door_status"]  # harus ada key 'door_status'
            print(f"[Subscriber][SENSOR][DOOR] Car: {car_id} | Door is {door_status.upper()}")
        except json.JSONDecodeError:
            print(f"[Subscriber][ERROR] Door payload not valid JSON: Raw: {payload}")
        except KeyError:
            print(f"[Subscriber][ERROR] 'door_status' field missing in payload: {payload}")
        return

    # 4. Sensor Hood (hood): showroom/sportcar/sensor/hood/<car_id>
    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/sensor/hood/"):
        car_id = topic.split("/")[-1]
        try:
            data = json.loads(payload)
            hood_status = data["hood_status"]  # harus ada key 'hood_status'
            print(f"[Subscriber][SENSOR][HOOD] Car: {car_id} | Hood is {hood_status.upper()}")
        except json.JSONDecodeError:
            print(f"[Subscriber][ERROR] Hood payload not valid JSON: Raw: {payload}")
        except KeyError:
            print(f"[Subscriber][ERROR] 'hood_status' field missing in payload: {payload}")
        return

    # 5. Pesan status umum (available/on display)
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

    # 6. Perubahan Harga: showroom/sportcar/status/<car_id>/price
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

    # 7. Expiry (broker‐level) – cukup ditampilkan
    if topic.startswith(f"{UNIQUE_TOPIC_PREFIX}/expiry/"):
        print(f"[Subscriber][EXPIRY‐BROKER] Payload: {payload}")
        return

    # 8. Request–Response
    if topic == f"{UNIQUE_TOPIC_PREFIX}/request":
        handle_request(msg)
        return

    # Jika tidak masuk kategori di atas, tampilkan saja
    print(f"[Subscriber] Payload: {payload}")

def handle_request(msg):
    props = msg.properties

    # Ambil response_topic dan correlation_data (cek PascalCase atau snake_case)
    if props:
        if hasattr(props, "ResponseTopic"):
            resp_topic = props.ResponseTopic
        elif hasattr(props, "response_topic"):
            resp_topic = props.response_topic
        else:
            resp_topic = None

        if hasattr(props, "CorrelationData"):
            raw_corr = props.CorrelationData
        elif hasattr(props, "correlation_data"):
            raw_corr = props.correlation_data
        else:
            raw_corr = None

        if isinstance(raw_corr, (bytes, bytearray)):
            corr = raw_corr.decode()
        else:
            corr = raw_corr
    else:
        resp_topic = None
        corr = None

    print(f"[Subscriber][REQ] Processing request. ResponseTopic={resp_topic} | CorrelationData={corr}")

    # Parsing payload request dengan error handling
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

    # Misal command == "check_inventory", kirim data dummy
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

    # Kirim balasan jika resp_topic dan corr ada
    if resp_topic and corr:
        props_resp = Properties(PacketTypes.PUBLISH)
        # Tetap gunakan PascalCase ketika men‐set CorrelationData
        props_resp.CorrelationData = corr.encode() if isinstance(corr, str) else corr
        props_resp.PayloadFormatIndicator = 1
        client.publish(resp_topic, response_payload, qos=1, retain=False, properties=props_resp)
        print(f"[Subscriber][REQ] Sent response for {car_id} to {resp_topic} | CorrData={corr}")

    # Parsing payload request dengan error handling
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

    # Misal command == "check_inventory", kita kirim jumlah units/price/color
    if command == "check_inventory":
        # Dummy data (bisa diganti db lookup nyata)
        response_payload = json.dumps({
            "car_id": car_id,
            "units_available": 3,
            "price": 350000.0,
            "color": "red",
            "request_id": corr
        })
    else:
        # Default: konfirmasi command diterima tapi tidak dikenal
        response_payload = json.dumps({
            "car_id": car_id,
            "message": f"Unknown command '{command}'",
            "request_id": corr
        })

    # Publish balasan jika resp_topic dan corr ada
    if resp_topic and corr:
        props_resp = Properties(PacketTypes.PUBLISH)
        # Gunakan setter snake_case jika perlu
        if hasattr(props_resp, "CorrelationData"):
            props_resp.CorrelationData = corr.encode() if isinstance(corr, str) else corr
        else:
            props_resp.correlation_data = corr.encode() if isinstance(corr, str) else corr

        props_resp.PayloadFormatIndicator = 1
        client.publish(resp_topic, response_payload, qos=1, retain=False, properties=props_resp)
        print(f"[Subscriber][REQ] Sent response for {car_id} to {resp_topic} | CorrData={corr}")


# --------------------------- INISIALISASI CLIENT ---------------------------
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

# Jalankan thread pemroses pesan
threading.Thread(target=process_messages, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("[Subscriber] KeyboardInterrupt received. Exiting.")
    client.loop_stop()
    client.disconnect()
