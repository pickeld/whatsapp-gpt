import os
from config import config
from flask import Flask, request, jsonify, render_template_string
from memory import MemoryManager
from routes.pairing import register_routes


app = Flask(__name__)
memory = MemoryManager(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))


WAHA_API_URL = config.waha_api_url  # type: ignore


register_routes(app)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    payload = data.get('payload', {}) # type: ignore
    if payload and payload.get('fromMe') == True:
        # Process only incoming text messages
        if 'body' in payload:
            chatid = payload.get('id')
            message = payload.get('body')
            timestamp = payload.get('timestamp')
            print(f"ChatID: {chatid}, Message: {message}, Timestamp: {timestamp}", flush=True)

    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
