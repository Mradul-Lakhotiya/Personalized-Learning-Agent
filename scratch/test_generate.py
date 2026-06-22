import requests

url = "http://localhost:8000/api/v1/agent/generate-node"
data = {
    "node_id": "classes-and-objects",
    "thread_id": "test-convo",
    "title": "Classes and Objects",
    "description": "Test",
    "learning_goal": "Python",
    "user_id": "system"
}
try:
    with requests.post(url, json=data, stream=True) as r:
        print(f"Status: {r.status_code}")
        for line in r.iter_lines():
            if line:
                print(line.decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
