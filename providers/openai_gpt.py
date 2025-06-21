from config import config
from openai import OpenAI


class OpenAIChatGPT:
    def __init__(self):
        self.model = config.openai_model
        self.client = OpenAI(api_key=config.openai_api_key)

    def chat(self, prompt: str):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        print(reply)
        return reply

if __name__ == "__main__":
    chatgpt = OpenAIChatGPT()
    chatgpt.chat("Hello, how are you?")