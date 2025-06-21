import base64
import requests
from flask import render_template_string
from config import config

WAHA_API_URL = config.waha_api_url  # type: ignore
WEBHOOK_URL = config.webhook_url  # Define this in your config

def register_routes(app):
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
