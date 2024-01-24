from openai import OpenAI
import os

class Chat():
    client = None

    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def gptResponse(self, query: str) -> str:

        completion = self.client.chat.completions.create(
            model="mistralai/mistral-medium",
            messages=[
              {"role": "system", "content": f"You are Bridgeport Bot, a chatbot based on a large language model trained by Mistral. Carefully heed the user's instructions. Respond in plaintext"},
              {"role": "user", "content": f"{query}"}
            ],
            max_tokens=1000
        )

        return completion.choices[0].message.content
