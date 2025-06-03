# test_request_response.py
import time
import json
import uuid
from paho.mqtt.client import Client, MQTTv5
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

# ---- Konfigurasi broker/sistem ----
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 8883
USERNAME = "kelompokB"
PASSWORD = "hzwnkptrm"

PREFIX = "showroom/sportcar"
REQUEST_TOPIC = f"{PREFIX}/request"

# Menampung semua response yang diterima: dict[correlation_id] = payload_dict
RESPONSES = {}

def on_connect(client, userdata, flags, reasonCode, properties):
    print(f"[TestReqResp] Connected with code {reasonCode}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        props = msg.properties

        # Ambil correlation_data dari properti (PascalCase)
        raw_corr = props.CorrelationData if hasattr(props, "CorrelationData") else None

        if isinstance(raw_corr, (bytes, bytearray)):
            corr_id = raw_corr.decode()
        else:
            corr_id = raw_corr

        data = json.loads(payload)
        RESPONSES[corr_id] = data
        print(f"[TestReqResp] ✓ Received response for {corr_id}: {json.dumps(data)}")
    except Exception as e:
        print(f"[TestReqResp] ⚠️ Error in on_message: {e}")

def send_request_and_wait(client, car_id, command, timeout=5):
    request_id = str(uuid.uuid4())
    response_topic = f"{PREFIX}/response/{client._client_id.decode()}/{request_id}"
    client.subscribe(response_topic, qos=1)
    print(f"[TestReqResp] Subscribed to response topic = {response_topic}")

    payload = json.dumps({
        "car_id": car_id,
        "command": command
    })
    props = Properties(PacketTypes.PUBLISH)
    props.ResponseTopic = response_topic
    props.CorrelationData = request_id.encode()
    props.PayloadFormatIndicator = 1

    client.publish(REQUEST_TOPIC, payload, qos=1, retain=False, properties=props)
    print(f"[TestReqResp] → Sent request_id={request_id} | car_id={car_id} | command={command}")

    start = time.time()
    while time.time() - start < timeout:
        if request_id in RESPONSES:
            resp = RESPONSES.pop(request_id)
            time.sleep(0.05)  # beri waktu ringkas sebelum unsubscribe
            client.unsubscribe(response_topic)
            return resp
        time.sleep(0.1)

    client.unsubscribe(response_topic)
    return None

def run_request_response_tests():
    print("\n=== Running Request-Response Tests ===\n")

    client = Client(client_id=f"test_reqresp_{int(time.time())}", protocol=MQTTv5)
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)

    # --- Test 1: Standard request (check_inventory ferrari_488) ---
    print("\n[Test 1] Sending request (check_inventory ferrari_488)...")
    resp1 = send_request_and_wait(client, "ferrari_488", "check_inventory", timeout=5)
    if resp1:
        print(f"[Test 1] Response: {json.dumps(resp1, indent=2)}")
        if resp1.get("car_id") == "ferrari_488" and "units_available" in resp1:
            print("[Test 1] ✅ Valid response.")
        else:
            print("[Test 1] ❌ Payload mismatch or missing fields.")
    else:
        print("[Test 1] ❌ No response (timeout).")

    time.sleep(1)

    # --- Test 2: Second request (check_inventory lamborghini_huracan) ---
    print("\n[Test 2] Sending request (check_inventory lamborghini_huracan)...")
    resp2 = send_request_and_wait(client, "lamborghini_huracan", "check_inventory", timeout=5)
    if resp2:
        print(f"[Test 2] Response: {json.dumps(resp2, indent=2)}")
        if resp2.get("car_id") == "lamborghini_huracan" and "units_available" in resp2:
            print("[Test 2] ✅ Valid response.")
        else:
            print("[Test 2] ❌ Payload mismatch or missing fields.")
    else:
        print("[Test 2] ❌ No response (timeout).")

    time.sleep(1)

    # --- Test 3: Unknown command ---
    print("\n[Test 3] Sending request with unknown command...")
    resp3 = send_request_and_wait(client, "porsche_911", "unknown_action", timeout=5)
    if resp3:
        print(f"[Test 3] Response: {json.dumps(resp3, indent=2)}")
        if resp3.get("message", "").lower().startswith("unknown"):
            print("[Test 3] ✅ Received expected 'unknown' response.")
        else:
            print("[Test 3] ❌ Unexpected payload.")
    else:
        print("[Test 3] ❌ No response (timeout). Possibly subscriber ignored unknown command.")

    print("\n=== Request-Response Tests Finished ===\n")
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    run_request_response_tests()
