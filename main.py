from fbchat import log, Client, MessageReaction
from fbchat.models import *
from chat import *
from kagi import summarize, search
import os
import db
import json
import time
import re
from spotify import add_to_playlist
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor

chat = None
THREAD_ID = None
THREAD_TYPE = None
GC_THREAD_ID = None

async def async_wrapper(sync_func, *args, timeout_duration=20, **kwargs) -> str:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        try:
            # Use asyncio.wait_for to apply a timeout
            return await asyncio.wait_for(loop.run_in_executor(pool, lambda: sync_func(*args, **kwargs)), timeout=timeout_duration)
        except asyncio.TimeoutError:
            return "Request timed out"

def getImageAttachment(message_object):
    if message_object is not None:
        # Iterate over the attachments of the replied message
        for attachment in message_object.attachments:
            # Check if the attachment is an image
            if isinstance(attachment, ImageAttachment):
                return attachment
    return None
    
# Subclass fbchat.Client and override required methods
class BPBot(Client):
    def personaSend(self, persona, message):
        self.send(Message(text=persona + ":\n" + message), thread_id=THREAD_ID, thread_type=THREAD_TYPE)

    def getContext(self, words, message_object, persona) -> (str, str):
        # Gets the last x messages sent to the thread
        messages = client.fetchThreadMessages(thread_id=THREAD_ID, limit=40)
        # cut context based on reset
        for i in range(len(messages)):
            m = messages[i]
            if m.text and m.text.startswith('!reset'):
                messages = messages[:i]
                break
        # Since the message come in reversed order, reverse them
        messages.reverse()

        # create 'user_id to username' dict
        # fetchUserInfo works weird for groupchats, gotta run this workaround
        group = client.fetchGroupInfo(GC_THREAD_ID)[GC_THREAD_ID]
        participant_ids = group.participants
        users = [client.fetchThreadInfo(user_id)[user_id] for user_id in participant_ids]
        user_dict = {user.uid: user.name for user in users}
        context_messages = []

        # remove commands from messages
        query = " ".join(word for word in words if not word.startswith('!'))
        query = "{}: {}".format(user_dict[message_object.author], query)

        for m in messages:
            # remove commands
            # text is None for some messages, replace with empty message
            if getImageAttachment(m):
                m_text = "[IMAGE]"
            else:
                # filter command word if theres message text
                m_text = " ".join(word for word in m.text.split() if not word.startswith('!')) if m.text is not None else "[NON-TEXT MESSAGE]"
            # .author returns id, convert to username
            user_name = user_dict[m.author]
            if m.author == self.uid:
                m_split = m_text.split(":")
                user_name = m_split[0]
                m_split.pop(0)
                m_text = " ".join(m_split)
                # if not us, it was another persona, treat it as seperate user
                if user_name != persona:
                    context_messages.append({"role": "user", "content": "{}: {}".format(user_name, m_text)})
                else:
                    context_messages.append({"role": "assistant", "content": m_text})
            else:
                context_messages.append({"role": "user", "content": "{}: {}".format(user_name, m_text)})
        return (query, context_messages)

    def onMessage(self, author_id, message_object, thread_id, thread_type, **kwargs):
        global chat
        global THREAD_ID
        global THREAD_TYPE
        global GC_THREAD_ID
        THREAD_ID = thread_id
        THREAD_TYPE = thread_type
        GC_THREAD_ID = os.environ["GROUPID"]

        self.markAsDelivered(THREAD_ID, message_object.uid)
        self.markAsRead(THREAD_ID)


        log.info("{} from {} in {}".format(message_object, THREAD_ID, THREAD_TYPE.name))
        # client.reactToMessage(message_object.uid, MessageReaction.LOVE)

        # if message isn't text or doesn't start with '!', its none of our business (for now, anyways)
        if not (message_object.text and message_object.text[0] == '!'):
            return

        if author_id != self.uid and THREAD_ID == GC_THREAD_ID:
            #if "heart" in message_object.text:
            #    client.reactToMessage(message_object.uid, MessageReaction.LOVE)
            # self.send(message_object, thread_id=thread_id, thread_type=thread_type)
            message = message_object.text
            words = message.split()
            persona = "BP Bot"
            cmd = words.pop(0)

            match cmd:
                case "!notes":
                    persona = "Notes"
                    notes_cmd = words.pop(0)
                    match notes_cmd:
                        case "set":
                            reply = ""
                            if message_object.replied_to:
                                if message_object.replied_to.text:
                                    note_name = " ".join(words)
                                    note_content = message_object.replied_to.text
                                    db.save(note_name, note_content, "notes.sqlite3")
                                    reply = note_name + " has been set."
                                else:
                                    reply = "Cannot get responded message text"
                            else:
                                reply = "Repond to the note you'd like to save"

                            self.personaSend(persona, reply)
                    

                        case "get":
                            note_name = " ".join(words)
                            response = db.load(note_name, "notes.sqlite3")
                            self.personaSend(persona, response)

                        case "list":
                            response = db.keysList("notes.sqlite3")
                            self.personaSend(persona, response)

                        case "clear":
                            note_name = words.pop(0)
                            db.clear(note_name, "notes.sqlite3")

                            self.personaSend(persona, note_name + " has been cleared.")

                case "!chat":
                    if chat == None:
                        chat = Chat()

                    response = ""
                    limit = 1000
                    query = " ".join(words)

                    if len(words) >= limit:
                        message = "Prompt too long (over {} words)".format(limit)
                    else:
                        if attachment := getImageAttachment(message_object.replied_to):
                            image_url = client.fetchImageUrl(attachment.uid)
                            response = asyncio.run(async_wrapper(chat.imageResponse, image_url, query))
                        else:
                            response = asyncio.run(async_wrapper(chat.mistralResponse, query))
                        
                    self.personaSend(persona, response)

                case "!tyco":
                    persona = "Tyco"

                    if chat == None:
                        chat = Chat()
                    (query, context) = self.getContext(words, message_object, persona)

                    response = asyncio.run(async_wrapper(chat.tycoResponse, query, context))
                    self.personaSend(persona, response)

                case "!summarize":
                    url = " ".join(words)
                    response = asyncio.run(async_wrapper(summarize, url))
                    self.personaSend(persona, response)

                case "!search":
                    url = " ".join(words)
                    response = asyncio.run(async_wrapper(search, url))
                    # reponse comes back in markdown, using asterisks to bold and italicize
                    # this shows up properly on web messenger, but not on mobile, so let just remove it
                    response = response.replace('*', '')
                    self.personaSend(persona, response)

                case "!refs":
                    note_name = "references"
                    response = db.load(note_name, "refs.sqlite3")
                    self.personaSend(persona, response)

                case "!test":
                    persona = "Test"
                    self.personaSend(persona, "Hello")

                case _:
                    # auto add spotify links to group playlist
                    if match := re.search(r"https:\/\/open\.spotify\.com\/track\/[a-zA-Z0-9]{22}", message):
                        add_to_playlist(match.group())

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
