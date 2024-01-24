from fbchat import log, Client, MessageReaction
from fbchat.models import *
from chat import *
from summarizer import summarize
import os
import db
import json
import time

chat = None
# Subclass fbchat.Client and override required methods
class BPBot(Client):
    def onMessage(self, author_id, message_object, thread_id, thread_type, **kwargs):
        self.markAsDelivered(thread_id, message_object.uid)
        self.markAsRead(thread_id)
        global chat

        log.info("{} from {} in {}".format(message_object, thread_id, thread_type.name))
        # client.reactToMessage(message_object.uid, MessageReaction.LOVE)

        # If you're not the author, echo
        gc_thread_id = os.environ["GROUPID"]
        if author_id != self.uid and thread_id == gc_thread_id:
            #if "heart" in message_object.text:
            #    client.reactToMessage(message_object.uid, MessageReaction.LOVE)
            # self.send(message_object, thread_id=thread_id, thread_type=thread_type)
            message = message_object.text
            words = message.split()

            if message.startswith("!notes set"):
                words.pop(0)
                words.pop(0)

                note_name = words.pop(0)
                note_content = " ".join(words)
                db.save(note_name, note_content, "notes.sqlite3")
                self.send(Message(text=(note_name + " has been set.")), thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!notes get"):
                words.pop(0)
                words.pop(0)

                note_name = words.pop(0)
                send = db.load(note_name, "notes.sqlite3")
                self.send(Message(text=send), thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!notes list"):
                send = db.keysList("notes.sqlite3")
                send = "Notes:\n" + send
                self.send(Message(text=send), thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!notes clear"):
                words.pop(0)
                words.pop(0)

                note_name = words.pop(0)
                db.clear(note_name, "notes.sqlite3")

                self.send(Message(text=(note_name + " has been cleared.")), thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!chat"):
                words.pop(0)

                if chat == None:
                    chat = Chat()

                message = ""
                limit = 1000
                query = " ".join(words)

                if len(words) >= limit:
                    message = "Prompt too long (over {} words)".format(limit)
                else:
                    response = chat.gptResponse(query)
                    message = Message(text=response)

                self.send(message, thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!summarize"):
                words.pop(0)

                url = " ".join(words)
                # print("IN!")
                # print("{}".format(url))

                response = summarize(url)
                message = Message(text=response)

                self.send(message, thread_id=thread_id, thread_type=thread_type)

            # elif message.startswith("!timeout"):
            #     thread = self.fetchThreadInfo(thread_id)[thread_id]
            #     print("thread's name: {}".format(thread.name))
            #     print("thread's type: {}".format(thread.type))

            #     print(thread)
            #     users = self.fetchAllUsersFromThreads([thread])
            #     print(users)


cookies = {}
try:
    # Load the session cookies
    with open('session.json', 'r') as f:
        cookies = json.load(f)
except:
    # If it fails, never mind, we'll just login again
    pass

bpuser = os.environ["BPBOTUSER"]
bppass = os.environ["BPBOTPASS"]
client = BPBot(bpuser, bppass, session_cookies=cookies)
with open('session.json', 'w') as f:
    json.dump(client.getSession(), f)

client.listen()
