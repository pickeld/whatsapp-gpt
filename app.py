import os
from config import config
from flask import Flask, request, jsonify, render_template_string
from utiles.logger import Logger
from utiles.classes import Providers
from memory import MemoryManager
import base64
import requests
from providers.gpt import GPT
from providers.dalle import Dalle


logger = Logger()
app = Flask(__name__)
memory = MemoryManager()

WAHA_API_URL = config.waha_api_url
WEBHOOK_URL = config.webhook_url

@app.route('/pair', methods=['GET'])
def pair():
    session_name = "default"
    headers = {"X-Api-Key": config.waha_api_key}
    status_url = f"{WAHA_API_URL}/api/sessions/{session_name}"
    
    try:
        # 1. Check session status first
        status_response = requests.get(status_url, headers=headers)
        if status_response.status_code == 200:
            status_data = status_response.json()
            service_status = status_data.get("status")
            engine_state = status_data.get("engine", {}).get("state")

            if service_status == "WORKING" and engine_state == "CONNECTED":
                return "<h1>Session 'default' is already connected.</h1>", 200

        # 2. Start the session
        start_url = f"{WAHA_API_URL}/api/sessions/start"
        payload = {"name": session_name}
        start_response = requests.post(start_url, json=payload, headers=headers)

        if start_response.status_code not in [201, 422]:
            start_response.raise_for_status()

        # 3. Set webhook for the session
        webhook_url = f"{WAHA_API_URL}/api/sessions/{session_name}"
        config_payload = {
            "config": {
                "webhooks": [
                    {
                        "url": WEBHOOK_URL,
                        "events": ["message.any", "session.status"]
                    }
                ]
            }
        }
        webhook_response = requests.put(webhook_url, json=config_payload, headers=headers)
        webhook_response.raise_for_status()

        # 4. Get the QR code
        qr_url = f"{WAHA_API_URL}/api/{session_name}/auth/qr"
        qr_response = requests.get(qr_url, headers=headers)
        qr_response.raise_for_status()
        
        qr_image_data = qr_response.content
        
        if qr_image_data:
            qr_base64 = base64.b64encode(qr_image_data).decode('utf-8')
            html = f"<h1>Scan to Pair WhatsApp</h1><img src='data:image/png;base64,{qr_base64}'>"
            return render_template_string(html)
        else:
            return "QR code not available yet. Please refresh in a few seconds.", 200

    except requests.exceptions.RequestException as e:
        return f"Error contacting WAHA API: {e}", 500


def msg_router(payload):
    if not payload.get('fromMe'):
        logger.debug("Message is not from me, ignoring.")
        return Providers.UNKNOWN
    if "body" not in payload:
        logger.debug("Payload does not contain 'body', ignoring.")
        return Providers.UNKNOWN
    
    msg = payload.get('body', '').strip()
    if not msg:
        return Providers.UNKNOWN
    if msg.startswith(config.gpt_prefix):
        return Providers.GPT
    elif msg.startswith(config.dalle_prefix):
        return Providers.DALLE
    else:
        return Providers.UNKNOWN


def gpt_handler(payload):
    gpt = GPT()
    chat_id = payload.get('to')
    message = payload.get('body', '').strip()
    
    if not chat_id or not message:
        logger.error("Invalid payload for GPT handler")
        return
    
    semantic = memory.retrieve_from_long_term_memory(message, chat_id, k=5)
    buffer = memory.get_recent_short_term_history(chat_id, max_chars=1500)
    
    context = "\n".join([str(msg.content) for msg in buffer]) + "\n" + "\n".join(semantic)

    logger.debug(f"Context for chat {chat_id}: {context}")
    prompt = f"{context}\n{message}"
    response = gpt.chat(prompt)
    
    if not response:
        logger.error("GPT returned no response")
        return

    memory.append_user_message(chat_id, message)
    memory.append_ai_message(chat_id, response)
    
    headers = {"X-Api-Key": config.waha_api_key}
    send_url = f"{WAHA_API_URL}/api/sendText"
    send_payload = {
        "chatId": chat_id,
        "text": response,
        "session": "default"
    }
    try:
        response = requests.post(send_url, json=send_payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError occurred: {e}, Response: {response.text}")
        return {"error": "Failed to send request to API"}
    

def dalle_handler(payload):
    dalle = Dalle()
    chat_id = payload.get('to')
    message = payload.get('body', '').strip()
    
    if not chat_id or not message:
        logger.error("Invalid payload for DALL-E handler")
        return
    
    buffer = memory.get_recent_short_term_history(chat_id, max_chars=3500, exclude_prefixes=["!!"])
    context = "\n".join([str(msg.content) for msg in buffer])

    logger.debug(f"Context for chat {chat_id}: {context}")
    prompt = f"{context}\n{message}"
    
    image_url = dalle.dalle(prompt)
    
    memory.append_user_message(chat_id, message)
    if image_url:
        memory.append_ai_message(chat_id, "[DALLE_IMAGE]")
    
    headers = {"X-Api-Key": config.waha_api_key}
    send_url = f"{WAHA_API_URL}/api/sendImage"
    send_payload = {
        "chatId": chat_id,
        "file": {"url": image_url},
        "session": "default"
    }
    try:
        response = requests.post(send_url, json=send_payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError occurred: {e}, Response: {response.text}")
        return {"error": "Failed to send request to API"}
    

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    payload = data.get('payload', {})
    handler = msg_router(payload)
    
    if handler == Providers.GPT:
        gpt_handler(payload)
    elif handler == Providers.DALLE:
        logger.debug("Handling DALL-E request")
        dalle_handler(payload)
    else:
        logger.warning("Received unknown handler request")

    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
