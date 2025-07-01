from config import config
from openai import OpenAI
from utiles.logger import Logger
from providers.prompts import build_system_prompt

logger = Logger(__name__)


class GPT:
    def __init__(self):
        self.openai_model = config.openai_model
        self.embedding_model = config.embedding_model
        self.client = OpenAI(api_key=config.openai_api_key)

    def chat(self, prompt: str):
        response = self.client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": prompt}
                ],
            temperature=float(config.openai_temperature),
        )
        reply = response.choices[0].message.content
        return reply

    def generate_embedding(self, text: str):
        """
        Generate embeddings for the given text using OpenAI's embedding endpoint.
        """
        logger.info(f"Generating embedding for text: {text}")
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        embedding = response.data[0].embedding
        return embedding

if __name__ == "__main__":
    chatgpt = GPT()
    chatgpt.chat("Hello, how are you?")