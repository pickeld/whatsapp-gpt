# Configuration Documentation

This document provides an overview of the environment variables used in the project.

## Environment Variables

### LOG_LEVEL
- **Description**: Specifies the logging level for the application.
- **Example**: `DEBUG`

### WAHA_API_URL
- **Description**: The base URL for the WAHA API.
- **Example**: `http://localhost:3000`

### WAHA_API_KEY
- **Description**: API key for authenticating with the WAHA API.
- **Example**: `your-waha-api-key`

### WAHA_WEBHOOK_URL
- **Description**: URL for the WAHA webhook.
- **Example**: `http://host.docker.internal:5002/webhook`

### WAHA_PRINT_QR
- **Description**: Flag to enable or disable QR code printing.
- **Example**: `false`

### OPENAI_API_KEY
- **Description**: API key for accessing OpenAI services.
- **Example**: `your-openai-api-key`

### OPENAI_MODEL
- **Description**: Specifies the OpenAI model to use.
- **Example**: `gpt-3.5-turbo`

### EMBEDDING_MODEL
- **Description**: Specifies the embedding model for semantic operations.
- **Example**: `paraphrase-multilingual-MiniLM-L12-v2`

### dalle_model
- **Description**: Specifies the DALL-E model to use.
- **Example**: `dall-e-3`

### WEBHOOK_URL
- **Description**: URL for the webhook.
- **Example**: `http://host.docker.internal:5002/webhook`

### REDIS_URL
- **Description**: URL for connecting to the Redis database.
- **Example**: `redis://localhost:6379`

### DALLE_PREFIX
- **Description**: Prefix for DALL-E commands.
- **Example**: `!!`

### GPT_PREFIX
- **Description**: Prefix for GPT commands.
- **Example**: `??`

### TOKENIZERS_PARALLELISM
- **Description**: Flag to enable or disable tokenizers parallelism.
- **Example**: `false`

### QDRANT_COLLECTION_NAME
- **Description**: Name of the Qdrant collection for semantic memory.
- **Example**: `semantic_memory`