import time
import uuid
import json
import ssl
from paho.mqtt.client import Client, MQTTMessageInfo, MQTTv5
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

# --------------------------- CONFIGURASI ---------------------------
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 8883                 # 8883 untuk MQTTS
USERNAME = "kelompokB"
PASSWORD = "hzwnkptrm"
UNIQUE_TOPIC_PREFIX = "showroom/sportcar"
KEEPALIVE = 60
RATE_LIMIT_PUB = 5                 # pesan per detik maksimum

# Topik‐topik Standar
TOPIC_INVENTORY = f"{UNIQUE_TOPIC_PREFIX}/inventory"  # inventory updates
TOPIC_SENSOR_DOOR = f"{UNIQUE_TOPIC_PREFIX}/sensor/door"
TOPIC_SENSOR_HOOD = f"{UNIQUE_TOPIC_PREFIX}/sensor/hood"
TOPIC_STATUS = f"{UNIQUE_TOPIC_PREFIX}/status"
TOPIC_REQUEST = f"{UNIQUE_TOPIC_PREFIX}/request"
TOPIC_LAST_WILL = f"{UNIQUE_TOPIC_PREFIX}/lwt"
TOPIC_EXPIRY = f"{UNIQUE_TOPIC_PREFIX}/expiry"
TOPIC_FLOW = f"{UNIQUE_TOPIC_PREFIX}/flow"

last_pub_time = 0.0

# --------------------------- CALLBACKS ---------------------------
def on_connect(client, userdata, flags, reasonCode, properties):
    print(f"[Publisher] Connected with result code {reasonCode}")

def on_disconnect(client, userdata, reasonCode, properties):
    print(f"[Publisher] Disconnected with code {reasonCode}")

def on_publish(client, userdata, mid):
    print(f"[Publisher] Message acked, MID={mid}")

def on_message(client, userdata, msg):
    """
    Callback untuk menerima respons request–response
    """
    try:
        payload = msg.payload.decode()
        props = msg.properties
        corr = props.CorrelationData.decode() if props and isinstance(props.CorrelationData, bytes) else props.CorrelationData
        print(f"[Publisher] 📨 Response on {msg.topic} | CorrData={corr} | Payload={payload}")
    except Exception as e:
        print(f"[Publisher] Error decoding response: {e}")

# --------------------------- FUNGI PUBLISH DENGAN RATE LIMIT ---------------------------
def send_with_rate_limit(topic, payload, qos=0, retain=False, properties=None):
    global last_pub_time
    now = time.time()
    elapsed = now - last_pub_time
    min_interval = 1.0 / RATE_LIMIT_PUB
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    # Publish
    if properties:
        info: MQTTMessageInfo = client.publish(topic, payload=payload, qos=qos, retain=retain, properties=properties)
    else:
        info: MQTTMessageInfo = client.publish(topic, payload=payload, qos=qos, retain=retain)
    last_pub_time = time.time()
    return info

# --------------------------- INISIALISASI CLIENT ---------------------------
client = Client(client_id=f"publisher_{uuid.uuid4()}", protocol=MQTTv5)
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(
    ca_certs=None,
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS,
    ciphers=None
)

# Last Will
will_props = Properties(PacketTypes.PUBLISH)
will_props.PayloadFormatIndicator = 1
client.will_set(
    TOPIC_LAST_WILL,
    payload="Publisher has disconnected unexpectedly".encode(),
    qos=1,
    retain=False,
    properties=will_props
)

client.on_connect    = on_connect
client.on_disconnect = on_disconnect
client.on_publish    = on_publish
client.on_message    = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=KEEPALIVE)
client.loop_start()

# --------------------------- FUNGSI FASILITAS REAL‐LIFE ---------------------------

def publish_inventory_update(car_id: str, units: int, price: float, color: str, qos: int = 2, retained: bool = True):
    topic = f"{TOPIC_INVENTORY}/{car_id}"
    payload = json.dumps({
        "car_id": car_id,
        "units_available": units,
        "price": price,
        "color": color
    })
    props = Properties(PacketTypes.PUBLISH)
    props.PayloadFormatIndicator = 1
    send_with_rate_limit(topic, payload, qos=qos, retain=retained, properties=props)
    print(f"[Publisher][INVENTORY] Car={car_id} | Units={units} | Price={price} | Color={color} | QoS={qos} | Retained={retained}")

def publish_sensor_door(car_id: str, status: str, qos: int = 1, retained: bool = False):
    """
    Publikasikan status sensor pintu dalam payload JSON
    { "door_status": "open" } atau { "door_status": "closed" }
    """
    topic = f"{TOPIC_SENSOR_DOOR}/{car_id}"
    payload = json.dumps({
        "door_status": status  # gunakan key 'door_status'
    })
    props = Properties(PacketTypes.PUBLISH)
    props.PayloadFormatIndicator = 1
    send_with_rate_limit(topic, payload, qos=qos, retain=retained, properties=props)
    print(f"[Publisher][SENSOR][DOOR] Car={car_id} | Door={status} | QoS={qos}")

def publish_sensor_hood(car_id: str, status: str, qos: int = 1, retained: bool = False):
    """
    Publikasikan status sensor hood dalam payload JSON
    { "hood_status": "open" } atau { "hood_status": "closed" }
    """
    topic = f"{TOPIC_SENSOR_HOOD}/{car_id}"
    payload = json.dumps({
        "hood_status": status  # gunakan key 'hood_status'
    })
    props = Properties(PacketTypes.PUBLISH)
    props.PayloadFormatIndicator = 1
    send_with_rate_limit(topic, payload, qos=qos, retain=retained, properties=props)
    print(f"[Publisher][SENSOR][HOOD] Car={car_id} | Hood={status} | QoS={qos}")

def publish_status_update(car_id: str, status: str, qos: int = 1, retained: bool = True):
    """
    Publikasikan status umum mobil: "available", "on display", "sold".
    """
    topic = f"{TOPIC_STATUS}/{car_id}"
    payload = json.dumps({
        "car_id": car_id,
        "status": status
    })
    props = Properties(PacketTypes.PUBLISH)
    props.PayloadFormatIndicator = 1
    send_with_rate_limit(topic, payload, qos=qos, retain=retained, properties=props)
    print(f"[Publisher][STATUS] Car={car_id} | Status={status} | QoS={qos} | Retained={retained}")

def publish_price_change(car_id: str, new_price: float, qos: int = 1, retained: bool = False):
    """
    Publikasikan perubahan harga (sekali saja).
    """
    topic = f"{TOPIC_STATUS}/{car_id}/price"
    payload = json.dumps({
        "car_id": car_id,
        "new_price": new_price
    })
    props = Properties(PacketTypes.PUBLISH)
    props.PayloadFormatIndicator = 1
    send_with_rate_limit(topic, payload, qos=qos, retain=retained, properties=props)
    print(f"[Publisher][PRICE] Car={car_id} | New Price={new_price} | QoS={qos}")

def publish_expiring_message(car_id: str, message: str, expiry_interval: int = 5):
    """
    Kirim pesan dengan Message Expiry Interval.
    """
    topic = f"{TOPIC_EXPIRY}/{car_id}"
    payload = json.dumps({
        "car_id": car_id,
        "message": message
    })
    props = Properties(PacketTypes.PUBLISH)
    props.MessageExpiryInterval = expiry_interval
    props.PayloadFormatIndicator = 1
    send_with_rate_limit(topic, payload, qos=1, retain=False, properties=props)
    print(f"[Publisher][EXPIRY‐MSG] Car={car_id} | Message='{message}' | Expiry={expiry_interval}s")

def send_request(car_id: str, command: str, timeout: float = 5.0):
    """
    Implementasi Request‐Response (MQTT 5.0).
    """
    request_id = str(uuid.uuid4())
    response_topic = f"{UNIQUE_TOPIC_PREFIX}/response/{client._client_id.decode()}/{request_id}"
    client.subscribe(response_topic, qos=1)
    print(f"[Publisher][REQ] Subscribed to {response_topic}")

    payload = json.dumps({
        "car_id": car_id,
        "command": command
    })
    props = Properties(PacketTypes.PUBLISH)
    props.ResponseTopic = response_topic
    props.CorrelationData = request_id.encode()
    props.PayloadFormatIndicator = 1

    send_with_rate_limit(TOPIC_REQUEST, payload, qos=1, retain=False, properties=props)
    print(f"[Publisher][REQ] Sent request Car={car_id} command={command} | RequestID={request_id}")

    start = time.time()
    while True:
        if time.time() - start > timeout:
            print(f"[Publisher][REQ] No response within {timeout}s for RequestID={request_id}")
            break
        time.sleep(0.1)
    client.unsubscribe(response_topic)
    print(f"[Publisher][REQ] Unsubscribed from {response_topic}")

# --------------------------- BAGIAN UTAMA ---------------------------
if __name__ == "__main__":
    time.sleep(1.0)  # tunggu koneksi stabil
    
    # 1. Inventory Updates (retained)
    publish_inventory_update(car_id="ferrari_488", units=3, price=350000.0, color="red", qos=2, retained=True)
    publish_inventory_update(car_id="lamborghini_huracan", units=2, price=450000.0, color="yellow", qos=2, retained=True)

    # 2. Status Umum (retained)
    publish_status_update(car_id="ferrari_488", status="available", qos=1, retained=True)
    publish_status_update(car_id="lamborghini_huracan", status="on display", qos=1, retained=True)

    # 3. Sensor Pintu & Hood (JSON payload)
    time.sleep(1.0)
    publish_sensor_door(car_id="ferrari_488", status="closed", qos=1)
    publish_sensor_hood(car_id="ferrari_488", status="closed", qos=1)
    publish_sensor_door(car_id="lamborghini_huracan", status="open", qos=1)
    publish_sensor_hood(car_id="lamborghini_huracan", status="closed", qos=1)

    # 4. Perubahan Harga (sekali, QoS 1)
    time.sleep(1.0)
    publish_price_change(car_id="ferrari_488", new_price=340000.0, qos=1)

    # 5. Contoh Message Expiry
    time.sleep(1.0)
    publish_expiring_message(car_id="porsche_911", message="Flash sale ends soon", expiry_interval=5)

    # 6. Request–Response: misal "check_inventory"
    time.sleep(1.0)
    send_request(car_id="ferrari_488", command="check_inventory", timeout=5.0)

    # 7. Jika mau lihat LWT: matikan paksa script, subscriber akan terima di topik .../lwt

    # 8. Flow Control: kirim sekumpulan pesan cepat
    for i in range(10):
        payload = json.dumps({"test_seq": i})
        props = Properties(PacketTypes.PUBLISH)
        props.PayloadFormatIndicator = 1
        send_with_rate_limit(f"{TOPIC_FLOW}/test", payload, qos=1, retain=False, properties=props)
        print(f"[Publisher][FLOW] Queued test message {i}")
    
    time.sleep(5)
    print("[Publisher] Done. Exiting.")
    client.loop_stop()
    client.disconnect()
