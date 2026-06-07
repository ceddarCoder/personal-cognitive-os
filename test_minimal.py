import requests
import time
import threading

BASE = "http://127.0.0.1:8765"
TIMEOUT = 15

def test_health():
    r = requests.get(f"{BASE}/health", timeout=TIMEOUT)
    print("✅ Health:", r.json())

def test_capture():
    r = requests.post(f"{BASE}/capture", json={"content": "test note from script", "source": "test"}, timeout=TIMEOUT)
    print("✅ Capture:", r.json())

def test_notes():
    r = requests.get(f"{BASE}/notes?limit=5", timeout=TIMEOUT)
    notes = r.json()
    print(f"✅ Notes: {len(notes.get('notes', []))} notes retrieved")

def test_state():
    r = requests.get(f"{BASE}/state", timeout=TIMEOUT)
    print("✅ State:", r.json())

def test_search():
    r = requests.get(f"{BASE}/notes/search", params={"q": "test"}, timeout=TIMEOUT)
    print("✅ Search:", r.json())

def test_divergence():
    r = requests.get(f"{BASE}/diverge", params={"current_state": "morning_focus"}, timeout=TIMEOUT)
    print("✅ Divergence prompt:", r.json().get("prompt", "")[:80])

def test_convergence():
    r = requests.get(f"{BASE}/converge", params={"current_state": "stuck"}, timeout=TIMEOUT)
    print("✅ Convergence prompt:", r.json().get("prompt", "")[:80])

def test_chat_general():
    r = requests.post(f"{BASE}/chat", json={"message": "hello, what can you do?"}, timeout=TIMEOUT)
    print("✅ Chat general:", r.json().get("response", "")[:80])

def test_chat_capture():
    r = requests.post(f"{BASE}/chat", json={"message": "note: remember to buy milk"}, timeout=TIMEOUT)
    print("✅ Chat capture:", r.json().get("response", "")[:80])

def test_concurrency():
    def long_req():
        try:
            r = requests.get(f"{BASE}/diverge", params={"current_state": "exploring"}, timeout=30)
            print("  ↔ Concurrent divergence returned")
        except Exception as e:
            print(f"  ↔ Concurrent divergence error: {e}")
    t = threading.Thread(target=long_req)
    t.start()
    time.sleep(0.5)
    start = time.time()
    r = requests.get(f"{BASE}/state", timeout=TIMEOUT)
    elapsed = time.time() - start
    print(f"✅ State responds in {elapsed:.2f}s during concurrent request:", r.json().get("state"))
    t.join(timeout=5)

if __name__ == "__main__":
    print("Testing PCOS endpoints...\n")
    test_health()
    test_capture()
    test_notes()
    test_state()
    test_search()
    test_divergence()
    test_convergence()
    test_chat_general()
    test_chat_capture()
    test_concurrency()
    print("\nAll tests completed.")