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

chat = None
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
            persona = "BP Bot"

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
                    if attachment := getImageAttachment(message_object.replied_to):
                        image_url = client.fetchImageUrl(attachment.uid)
                        response = chat.imageResponse(image_url, query)
                        message = Message(text=persona + ":\n" + response)
                    else:
                        response = chat.mistralResponse(query)
                        message = Message(text=persona + ":\n" + response)
                        

                self.send(message, thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!tyco"):
                persona = "Tyco"
                words.pop(0)

                if chat == None:
                    chat = Chat()

                # Gets the last x messages sent to the thread
                messages = client.fetchThreadMessages(thread_id=thread_id, limit=40)
                # cut context based on reset
                for i in range(len(messages)):
                    m = messages[i]
                    if m.text.startswith('!reset'):
                        messages = messages[:i]
                        break
                # Since the message come in reversed order, reverse them
                messages.reverse()

                # create 'user_id to username' dict
                # fetchUserInfo works weird for groupchats, gotta run this workaround
                group = client.fetchGroupInfo(gc_thread_id)[gc_thread_id]
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
                        if user_name != "Tyco":
                            context_messages.append({"role": "user", "content": "{}: {}".format(user_name, m_text)})
                        else:
                            context_messages.append({"role": "assistant", "content": m_text})
                    else:
                        context_messages.append({"role": "user", "content": "{}: {}".format(user_name, m_text)})

                response = chat.tycoResponse(query, context_messages)
                message = Message(text=persona + ": " + response)

                self.send(message, thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!summarize"):
                words.pop(0)

                url = " ".join(words)

                response = summarize(url)
                message = Message(text=persona + ":\n" + response)

                self.send(message, thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!search"):
                words.pop(0)

                url = " ".join(words)

                response = search(url)
                # reponse comes back in markdown, using asterisks to bold and italicize
                # this shows up properly on web messenger, but not on mobile, so let just remove it
                response = response.replace('*', '')
                message = Message(text=persona + ":\n" + response)

                self.send(message, thread_id=thread_id, thread_type=thread_type)

            elif message.startswith("!refs"):
                note_name = "references"
                send = db.load(note_name, "refs.sqlite3")
                self.send(Message(text=persona + ":" + send), thread_id=thread_id, thread_type=thread_type)

            # auto add spotify links to group playlist
            elif match := re.search(r"https:\/\/open\.spotify\.com\/track\/[a-zA-Z0-9]{22}", message):
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
