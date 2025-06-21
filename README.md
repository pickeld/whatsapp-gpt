# whatsapp-gpt

A Flask-based integration between WhatsApp (via the WAHA API) and OpenAI's GPT models. This project allows you to pair your WhatsApp account, receive webhook events, and interact with OpenAI's GPT for chat-based automation.

## Features

- **WhatsApp Pairing:** Easily pair your WhatsApp account using a QR code.
- **Webhook Handling:** Receives and processes incoming WhatsApp messages.
- **OpenAI Integration:** Sends prompts to OpenAI's GPT models and returns responses.
- **Environment Configuration:** Uses `.env` files for easy configuration.
- **Media Support:** For sending files and other media, use the WAHA-Plus Docker image, available only if you donate to the project. The core Docker image does not support receiving media from DALL-E.

## Project Structure

The project is organized as follows:

- **`app.py`**: Main Flask application for WhatsApp integration and webhook handling.
- **`providers/`**: Contains provider-specific integrations, such as `dalle.py` for DALL-E and `gpt.py` for GPT models.
- **`utiles/`**: Utility classes and logging functionality, including `classes.py` and `logger.py`.
- **`config.py`**: Loads environment variables and configuration settings.
- **`docker-compose.yml`**: Sets up the WAHA WhatsApp API service.
- **`.env.example`**: Example environment configuration file.
- **`requirements.txt`**: Lists Python dependencies required for the project.
- **`README.md`**: Documentation for the project.

## Getting Started

### Prerequisites

- Python 3.8+
- Docker (for running WAHA)
- OpenAI API key

### Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/whatsapp-gpt.git
   cd whatsapp-gpt
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in your credentials.

4. **Start WAHA (WhatsApp API) via Docker:**
   ```sh
   docker-compose up -d
   ```

5. **Run the Flask app:**
   ```sh
   python app.py
   ```

6. **Pair WhatsApp:**
   - Visit `http://localhost:5002/pair` in your browser and scan the QR code with your WhatsApp app.

## Usage

- Incoming WhatsApp messages will be received at the `/webhook` endpoint.
- You can extend the webhook handler to process messages and respond using OpenAI.

## Configuration

All configuration is managed via the `.env` file. Example:

```
WAHA_API_URL=http://localhost:3000
WAHA_API_KEY=your-waha-api-key
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo
LOG_LEVEL=DEBUG
```

## Deployment Flow

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/whatsapp-gpt.git
   cd whatsapp-gpt
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in your credentials.

4. **Start WAHA (WhatsApp API) via Docker:**
   ```sh
   docker-compose up -d
   ```

5. **Run the Flask app:**
   ```sh
   python app.py
   ```

6. **Pair WhatsApp:**
   - Visit `http://localhost:5002/pair` in your browser and scan the QR code with your WhatsApp app.

## Project Overview

This project integrates WhatsApp messaging with OpenAI's GPT models using Flask. It enables automated responses and webhook handling for WhatsApp messages. Key components include:
- **WAHA API**: Provides WhatsApp integration.
- **OpenAI GPT**: Handles AI-driven responses.
- **Flask**: Manages the application and webhook endpoints.
- **Semantic Memory**: Utilizes Qdrant for storing and retrieving semantic embeddings, enabling advanced memory-based operations.
- **Ollama Support**: Planned support for Ollama integration.
- **Gemini Support**: Planned support for Gemini integration.
- **TTS and STT**: Planned support for text-to-speech and speech-to-text functionalities.

## License

MIT License

---

**Note:** This project is for educational and prototyping purposes. Use responsibly and comply with WhatsApp and OpenAI.