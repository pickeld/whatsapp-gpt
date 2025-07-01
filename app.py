import os
import base64
import requests
from typing import Dict
from flask import Flask, request, jsonify, render_template_string

from config import config
from utiles.logger import Logger
from utiles.classes import Providers
from memory_agent import MemoryAgent
from providers.gpt import GPT
from providers.dalle import Dalle


logger = Logger()
app = Flask(__name__)
memory = MemoryAgent()


def send_request(method: str, endpoint: str, payload: Dict = None):
    payload = payload or {}
    headers = {"X-Api-Key": config.waha_api_key}
    url = f"{config.waha_api_url}{endpoint}"
    method_map = {
        "GET": requests.get,
        "POST": requests.post,
        "PUT": requests.put,
    }

    try:
        func = method_map[method.upper()]
        response = func(url, headers=headers, **({"json": payload} if method != "GET" else {}))
        response.raise_for_status()
        logger.debug(f"Request to {url} completed with status code {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return {"error": str(e)}


def filter_msg(payload: Dict) -> bool:
    if not payload.get("fromMe") or "body" not in payload:
        return False
    msg = payload["body"].strip()
    return msg[:2] in [config.gpt_prefix, config.dalle_prefix]


def msg_router(msg: str):
    if msg.startswith(config.gpt_prefix):
        return Providers.GPT
    if msg.startswith(config.dalle_prefix):
        return Providers.DALLE
    raise ValueError("Unrecognized message prefix")


def gpt_handler(payload: Dict):
    gpt = GPT()
    chat_id = payload.get("to")
    message = payload.get("body", "").strip()

    if not chat_id or not message:
        logger.error("Invalid payload for GPT handler")
        return

    context = memory.get_context(chat_id, max_chars=3000)
    print(f"Context for chat {chat_id}: {context}")
    prompt = f"{context}\n{message}" if context else message
    response = gpt.chat(prompt)

    if not response:
        logger.error("GPT returned no response")
        return

    memory.add_memory(chat_id, message, role="user")
    memory.add_memory(chat_id, response, role="assistant")

    send_request("POST", "/api/sendText", {
        "chatId": chat_id,
        "text": response,
        "session": "default"
    })


def dalle_handler(payload: Dict):
    dalle = Dalle()
    chat_id = payload.get("to")
    message = payload.get("body", "").strip()

    if not chat_id or not message:
        logger.error("Invalid payload for DALL-E handler")
        return

    context = memory.get_context(chat_id, max_chars=3500)
    logger.debug(f"Context for chat {chat_id}: {context}")
    prompt = f"{context}\n{message}" if context else message
    image_url = dalle.dalle(prompt)

    memory.add_memory(chat_id, message, role="user")

    send_request("POST", "/api/sendImage", {
        "chatId": chat_id,
        "file": {"url": image_url},
        "session": "default"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "up"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.json.get("payload", {})
    if not filter_msg(payload):
        logger.warning("Message filtered out or invalid.")
        return jsonify({"status": "ignored"}), 200

    msg = payload.get("body", "").strip()
    try:
        handler = msg_router(msg)
        if handler == Providers.GPT:
            gpt_handler(payload)
        elif handler == Providers.DALLE:
            dalle_handler(payload)
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        return jsonify({"error": str(e)}), 400

    return jsonify({"status": "ok"}), 200


@app.route("/pair", methods=["GET"])
def pair():
    session_name = "default"

    # Step 1: Check session status
    response = send_request("GET", f"/api/sessions/{session_name}")
    if isinstance(response, dict) and "error" in response:
        return f"Failed to get session status: {response['error']}", 500

    status_data = response.json()
    if status_data.get("status") == "WORKING" and status_data.get("engine", {}).get("state") == "CONNECTED":
        return "<h1>Session 'default' is already connected.</h1>", 200

    # Step 2: Start session
    send_request("POST", "/api/sessions/start", {"name": session_name})

    # Step 3: Configure webhook
    send_request("PUT", f"/api/sessions/{session_name}", {
        "config": {
            "webhooks": [
                {
                    "url": config.webhook_url,
                    "events": ["message.any", "session.status"]
                }
            ]
        }
    })

    # Step 4: Get QR code
    qr_response = send_request("GET", f"/api/{session_name}/auth/qr")
    if isinstance(qr_response, dict) and "error" in qr_response:
        return f"Failed to get QR code: {qr_response['error']}", 500

    qr_image_data = qr_response.content
    if qr_image_data:
        qr_base64 = base64.b64encode(qr_image_data).decode("utf-8")
        html = f"<h1>Scan to Pair WhatsApp</h1><img src='data:image/png;base64,{qr_base64}'>"
        return render_template_string(html)
    else:
        return "QR code not available yet. Please refresh in a few seconds.", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
