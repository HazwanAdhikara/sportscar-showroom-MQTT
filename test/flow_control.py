# test/flow_control.py
import sys
import os
import time
import json
from threading import Thread
import paho.mqtt.client as mqtt

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from publisher import send_with_rate_limit, client as publisher_client

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 8883
USERNAME = "kelompokB"
PASSWORD = "hzwnkptrm"
FLOW_TOPIC = "showroom/sportcar/flow/test"

def setup_publisher_client():

    if not publisher_client.is_connected():
        publisher_client.username_pw_set(USERNAME, PASSWORD)
        publisher_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        publisher_client.loop_start()
        time.sleep(1)  # tunggu koneksi stabil

def test_flow_control():
    print("=== Testing Flow Control ===")
    setup_publisher_client()

    # --------------------------------
    # Test 1: Kirim 10 pesan berturut-turut tanpa delay
    # --------------------------------
    print("\n[Test 1] Sending 10 messages sequentially (no extra sleep)")
    start = time.time()
    for i in range(10):
        payload = json.dumps({"seq": i})
        send_with_rate_limit(FLOW_TOPIC, payload, qos=1)
    elapsed = time.time() - start
    print(f"[Test 1] Sent 10 messages in {elapsed:.2f}s -> {10/elapsed:.2f} msg/s")

    # --------------------------------
    # Test 2: Kirim 5 pesan dengan very short sleep (0.01s)
    # --------------------------------
    print("\n[Test 2] Sending 5 messages with 0.01s sleep between")
    start = time.time()
    for i in range(5):
        payload = json.dumps({"short": i})
        send_with_rate_limit(FLOW_TOPIC, payload, qos=1)
        time.sleep(0.01)
    elapsed = time.time() - start
    print(f"[Test 2] Sent 5 messages in {elapsed:.2f}s -> {5/elapsed:.2f} msg/s")

    # --------------------------------
    # Test 3: Kirim 5 pesan secara concurrent (multi-thread)
    # --------------------------------
    print("\n[Test 3] Sending 5 messages concurrently in threads")
    def send_in_thread(idx):
        payload = json.dumps({"concurrent": idx})
        send_with_rate_limit(FLOW_TOPIC, payload, qos=1)
        print(f"[Test 3] Thread {idx} sent")

    threads = []
    start = time.time()
    for i in range(5):
        t = Thread(target=send_in_thread, args=(i,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    elapsed = time.time() - start
    print(f"[Test 3] Concurrent 5 messages in {elapsed:.2f}s -> {5/elapsed:.2f} msg/s")

    # Teardown
    publisher_client.loop_stop()
    publisher_client.disconnect()
    print("\n=== Flow Control Test Completed ===")

if __name__ == "__main__":
    test_flow_control()
