from easychatgpt import ChatClient
import os
import dotenv

class ChatGPT():
    OPENAI_EMAIL = None
    OPENAI_PASSWORD = None
    chat = None

    def __init__(self):
        self.OPENAI_EMAIL = os.getenv("OPENAI_EMAIL")
        self.OPENAI_PASSWORD = os.getenv("OPENAI_PASSWORD")

        self.chat = ChatClient(self.OPENAI_EMAIL,self.OPENAI_PASSWORD)

    def gptResponse(self, query):
        return self.chat.interact(query)
    def switchThread(self, name):
        self.chat.switch_thread(name)
