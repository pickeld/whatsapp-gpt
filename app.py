import os
from config import config
from dotenv import load_dotenv
import requests
from flask import Flask, request, jsonify, render_template_string
import base64


app = Flask(__name__)

# WAHA settings from environment variables
WAHA_API_URL = config.waha_api_url  # type: ignore




@app.before_request
def log_request():
    print(f"[{request.method}] {request.path} - headers: {dict(request.headers)}", flush=True)
    
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

        # 2. If not connected, ensure the session is started
        start_url = f"{WAHA_API_URL}/api/sessions/start"
        payload = {"name": session_name}
        start_response = requests.post(start_url, json=payload, headers=headers)
        
        # We expect 201 (Created) or 422 (Already started), any other error is a problem.
        if start_response.status_code not in [201, 422]:
            start_response.raise_for_status()

        # 3. Fetch the QR code from the dedicated endpoint
        qr_url = f"{WAHA_API_URL}/api/{session_name}/auth/qr"
        qr_response = requests.get(qr_url, headers=headers)
        qr_response.raise_for_status()
        
        # The response content is the raw PNG image
        qr_image_data = qr_response.content
        
        if qr_image_data:
            # Encode the image data in Base64
            qr_base64 = base64.b64encode(qr_image_data).decode('utf-8')
            # Create an HTML data URI to embed the image
            html = f"<h1>Scan to Pair WhatsApp</h1><img src='data:image/png;base64,{qr_base64}'>"
            return render_template_string(html)
        else:
            return "QR code not available yet. Please refresh in a few seconds.", 200

    except requests.exceptions.RequestException as e:
        return f"Error contacting WAHA API: {e}", 500

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    payload = data.get('payload', {}) # type: ignore
    if payload and payload.get('fromMe') == True:
            # Process only incoming text messages
            if 'body' in payload:
                print(f"payload id: {payload.get('id')}, body: {payload.get('body')}", flush=True)

    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True if config.log_level else False)
