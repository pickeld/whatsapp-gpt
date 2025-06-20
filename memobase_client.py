import requests

MEMOBASE_URL = "http://localhost:3001"

def get_context(chat_id):
    try:
        res = requests.get(f"{MEMOBASE_URL}/memory/{chat_id}")
        return res.json().get("memory", [])
    except:
        return []

def save_message(chat_id, role, content):
    payload = {
        "messages": [{"role": role, "content": content}]
    }
    requests.post(f"{MEMOBASE_URL}/memory/{chat_id}", json=payload)
