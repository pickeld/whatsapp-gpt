import os
from config import config
from flask import Flask, request, jsonify, render_template_string
from utiles.logger import Logger
from memory import MemoryManager
import base64
import requests
from providers.gpt import GPT

logger = Logger()
app = Flask(__name__)
memory = MemoryManager(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))


WAHA_API_URL = config.waha_api_url  # type: ignore
WEBHOOK_URL = config.webhook_url  # type: ignore

@app.route('/pair', methods=['GET'])
def pair():
    session_name = "default"
    headers = {"X-Api-Key": config.waha_api_key}  # type: ignore
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

        # ✅ 3. Set webhook for the session
        webhook_url = f"{WAHA_API_URL}/api/sessions/{session_name}"
        config_payload = {
            "config": {
                "webhooks": [
                    {
                        "url": WEBHOOK_URL,  # from config or env
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
        return {}
    if "body" not in payload:
        return {}
    
    msg = payload.get('body', '').strip()
    if not msg:
        return {}
    if msg.startswith(config.gpt_prefix):
        return {"handler": "chatgpt", "payload": payload}
    elif msg.startswith(config.dalle_prefix):
        return {"handler": "dalle", "payload": payload}
    else:
        logger.warning("Unknown message prefix, routing to default handler")
        return {"handler": "unknown", "payload": payload}
    

    
def gpt_handler(payload):
    gpt = GPT()
    
    
def dalle_handler(payload):
    ...
    

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    payload = data.get('payload', {})  # type: ignore
    handler = msg_router(payload)
    logger.debug(f"Sending payload to handler: {handler.get('handler')}")
    # #####
    # if payload and payload.get('fromMe') == True:
    #     # Process only incoming text messages
    #     if 'body' in payload:
    #         chatid = payload.get('id')
    #         message = payload.get('body')
    #         timestamp = payload.get('timestamp')
    #         print(f"ChatID: {chatid}, Message: {message}, Timestamp: {timestamp}", flush=True)

    #         # Check if message starts with GPT prefix
    #         if message.startswith(config.gpt_prefix):
    #             # Retrieve context from Redis
    #             context = "\n".join(
    #                 [msg.content for msg in memory.get_history(chatid) if hasattr(msg, 'content') and isinstance(msg.content, str)]
    #             )

    #             # Initialize ChatGPT
    #             from providers.openai_gpt import OpenAIChatGPT
    #             chatgpt = OpenAIChatGPT()

    #             # Send message and context to ChatGPT
    #             prompt = f"{context}\n{message}"
    #             response = chatgpt.chat(prompt)

    #             # Update Redis context
    #             memory.append_user(chatid, message)
    #             if response:
    #                 memory.append_ai(chatid, response)

    #             # Send response back to user
    #             headers = {"X-Api-Key": config.waha_api_key}  # type: ignore
    #             send_url = f"{WAHA_API_URL}/api/messages"
    #             send_payload = {
    #                 "chatId": chatid,
    #                 "body": response
    #             }
    #             requests.post(send_url, json=send_payload, headers=headers)

    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
