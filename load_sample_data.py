import json
import urllib.request
import urllib.error

URL = "http://localhost:8000/items"

with open("sample_data.json") as f:
    items = json.load(f)

for item in items:
    data = json.dumps(item).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            created = json.loads(resp.read())
            print(f"[{resp.status}] {created['name']} (score: {created['sustainability_score']})")
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] {item['name']} — {e.read().decode()}")
    except urllib.error.URLError as e:
        print(f"[ERROR] Could not connect to {URL}: {e.reason}")
        break
