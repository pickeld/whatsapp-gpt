from config import config
from openai import OpenAI
from utiles.logger import Logger

logger = Logger(__name__)

class Dalle:
    def __init__(self):
        self.model = config.dalle_model
        self.client = OpenAI(api_key=config.openai_api_key)
    def dalle(self, prompt: str):
        logger.info(f"Sending prompt to OpenAI DALL-E: {prompt}")
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt
        )
        image_url = response.data[0].url
        return image_url