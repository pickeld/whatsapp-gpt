import base64
import requests

from typing import Dict, Union
from flask import Flask, request, jsonify, render_template_string
import httpx
import base64
import requests

from config import config
from utiles.logger import Logger
from memory_agent import MemoryAgent
from providers.dalle import Dalle


logger = Logger()
app = Flask(__name__)


_memory_agents = {}

def get_memory_agent(recipient: str) -> MemoryAgent:
    if recipient not in _memory_agents:
        _memory_agents[recipient] = MemoryAgent(recipient)
    return _memory_agents[recipient]

def send_request(method: str, endpoint: str, payload: Union[Dict,None] = None):
    payload = payload or {}
    headers = {"X-Api-Key": config.waha_api_key}
    url = f"{config.waha_api_url}{endpoint}"
    method_map = {
        "GET": requests.get,
        "POST": requests.post,
        "PUT": requests.put,
    }

    # try:
    func = method_map[method.upper()]
    response = func(url, headers=headers, stream=True, **({"json": payload} if method != "GET" else {}))
    response.raise_for_status()
    logger.debug(f"Request to {url} completed with status code {response.status_code}")
    return response
    # except Exception as e:
    #     if "/api/sessions/" in endpoint:
    #         return {"error": str(e)}
    #     logger.error(f"Request failed: {e}")
    #     return {"error": str(e)}


class MediaMessage:
    def __init__(self, data):
        # logger.debug(f"Message has media: {payload}")
        self.url = data.get('url')
        self.type = data.get('mimetype')
        self.base64 = base64.standard_b64encode(httpx.get(self.url, headers={"X-Api-Key": config.waha_api_key}).content).decode("utf-8")

class QuotedMessage:
    def __init__(self, quoted_data, recipient):
        self.quoted_data = quoted_data
        self.quoted_msg = quoted_data.get("quotedMsg", {})
        self.type = self.quoted_msg.get("type", "")
        self.body = self.quoted_msg.get("body", "").strip()
        self.kind = self.quoted_msg.get("kind", "")
        self.quoted_stanza_id = quoted_data.get("quotedStanzaID", "")
        self.quoted_participant = quoted_data.get("quotedParticipant", "")
        self.mimetype = self.quoted_msg.get("mimetype", "")
        self.caption = self.quoted_msg.get("caption", "").strip()
        if self.type == "image":
            self.file_extension = self.mimetype.split("/")[-1]
            self.filename = f"true_{recipient}_{self.quoted_stanza_id}_{self.quoted_participant}.{self.file_extension}"
            endpoint = f"/api/files/default/{self.filename}"
            response = send_request(method="GET", endpoint=endpoint)
            self.base64_data = base64.b64encode(response.content).decode("ascii")

class WhatsappMSG:
    def __init__(self, payload):
        logger.debug(f"Initializing WhatsappMSG with payload: {payload}")
        self.message = payload.get("body", "").strip()
        self.sender = "me" if payload.get("fromMe") else payload.get("from", "")
        self.recipient = payload.get("to", "")
        self.has_media = payload.get("hasMedia", False)
        if self.has_media:
            self.media = MediaMessage(payload.get("media"))
        self.has_quote = payload.get("_data", {}).get("quotedMsg", {})
        if self.has_quote:
            try:
                self.quoted = QuotedMessage(quoted_data=payload.get("_data", {}), recipient=self.recipient)
            except Exception as e:
                logger.error(f"Error processing quoted message: {e}")
                self.quoted = None
        else:
            self.quoted = None
            

        
    def is_valid (self) -> bool:
        allowed_senders = []
        if self.sender not in ["me",allowed_senders]:
            
            return False
        if not self.message.startswith(config.chat_prefix) and not self.message.startswith(config.dalle_prefix):
            return False
        return True

    def startswith(self, prefix: str) -> bool:
        return self.message.startswith(prefix)

    def route(self):
        if self.message.startswith(config.chat_prefix):
            return "chat"
        elif self.message.startswith(config.dalle_prefix):
            return "dalle"
        else:
            return "unknown"
    
    def reply(self, response: str):
        send_request(method="POST",
                     endpoint="/api/sendText",
                     payload={
                              "chatId": self.recipient,
                              "text": response,
                              "session": "default"
                              }
                     )

    def __str__(self):
        return f"From: {self.sender}, To: {self.recipient}, Message: '{self.message}'"
    

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "up"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.json.get("payload", {}) if request.json else {}
    whatsapp_msg = WhatsappMSG(payload)
    mem_agent: MemoryAgent = get_memory_agent(whatsapp_msg.recipient)
    mem_agent.remember(whatsapp_msg.message)
    
    if not whatsapp_msg.is_valid():
        return jsonify({"status": "ignored"}), 200

    try:
        route = whatsapp_msg.route()
        if route == "chat":
            response = mem_agent.send_message(whatsapp_msg)
            whatsapp_msg.reply(str(response))
        elif route == "dalle":
            dalle = Dalle()
            dalle.context = mem_agent.get_recent_text_context()
            
            dalle.prompt = whatsapp_msg.message[len(config.dalle_prefix):].strip()
            image_url = dalle.request()
            
            send_request(method="POST", 
                         endpoint="/api/sendImage", 
                         payload={
                             "chatId": payload.get("to"),
                             "file": {"url": image_url},
                             "session": "default"
                             })
            
        else:
            logger.debug(f"Message did not match any route: {whatsapp_msg.message}")
            return jsonify({"status": "no matching handler"}), 200
        return jsonify({"status": "ok"}), 200
    
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        raise
        return jsonify({"error": str(e)}), 400

    


@app.route("/pair", methods=["GET"])
def pair():
    session_name = "default"

    response = send_request("GET", f"/api/sessions/{session_name}")
    # print(f"Response: {response.json()}")
    # logger.debug(f"Session status response: {response}")


    status_data = response.json()
    logger.debug(f"Status data: {status_data}")
    
    if status_data.get("status") == "WORKING" and status_data.get("engine", {}).get("state") == "CONNECTED":
        return "<h1>Session 'default' is already connected.</h1>", 200

    if status_data.get("status") != "SCAN_QR_CODE":
        send_request(method="POST", endpoint="/api/sessions/start", payload={"name": session_name})

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
