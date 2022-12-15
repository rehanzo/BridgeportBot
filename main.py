# -*- coding: UTF-8 -*-

from fbchat import log, Client, MessageReaction
from sqlitedict import SqliteDict
from fbchat.models import *
import dotenv
import os

import json

def save(key, value, cache_file="cache.sqlite3"):
    try:
        with SqliteDict(cache_file) as db:
            db[key] = value # Using dict[key] to store
            db.commit() # Need to commit() to actually flush the data
    except Exception as ex:
        print("Error during storing data (Possibly unsupported):", ex)

def load(key, cache_file="cache.sqlite3"):
    try:
        with SqliteDict(cache_file) as db:
            value = db[key] # No need to use commit(), since we are only loading data!
        return value
    except Exception as ex:
        print("Error during loading data:", ex)

def namesStr(cache_file="cache.sqlite3"):
    try:
        with SqliteDict(cache_file) as db:
            pre = "  - "
            finalStr = pre + ("\n" + pre).join(db.keys())
        return finalStr
    except Exception as ex:
        print("Error during loading data:", ex)

# Subclass fbchat.Client and override required methods
class EchoBot(Client):
    def onMessage(self, author_id, message_object, thread_id, thread_type, **kwargs):
        self.markAsDelivered(thread_id, message_object.uid)
        self.markAsRead(thread_id)

        log.info("{} from {} in {}".format(message_object, thread_id, thread_type.name))
        # client.reactToMessage(message_object.uid, MessageReaction.LOVE)

        # If you're not the author, echo
        if author_id != self.uid:
            #if "heart" in message_object.text:
            #    client.reactToMessage(message_object.uid, MessageReaction.LOVE)
            # self.send(message_object, thread_id=thread_id, thread_type=thread_type)
            message = message_object.text
            if message.startswith("!notes set"):
                words = message.split()
                words.pop(0)
                words.pop(0)

                note_name = words.pop(0)
                note_content = " ".join(words)
                save(note_name, note_content, "notes.sqlite3")
            if message.startswith("!notes get"):
                words = message.split()
                words.pop(0)
                words.pop(0)

                note_name = words.pop(0)
                send = load(note_name, "notes.sqlite3")
                self.send(Message(text=send), thread_id=thread_id, thread_type=thread_type)
            if message.startswith("!notes list"):
                send = namesStr("notes.sqlite3")
                send = "Notes:\n" + send
                self.send(Message(text=send), thread_id=thread_id, thread_type=thread_type)


cookies = {}
try:
    # Load the session cookies
    with open('session.json', 'r') as f:
        cookies = json.load(f)
except:
    # If it fails, never mind, we'll just login again
    pass

dotenv.load_dotenv()

hanzouser = os.environ["HANZOUSER"]
hanzopass = os.environ["HANZOPASS"]
client = EchoBot(hanzouser, hanzopass, session_cookies=cookies)
with open('session.json', 'w') as f:
    json.dump(client.getSession(), f)

client.listen()
