import asyncio
import os
import re
import signal
from concurrent.futures import ThreadPoolExecutor

from fbchat_muqit import (
    Client,
    EventType,
    ImageAttachment,
    Mention,
    Message,
    MessageReaction,
)

import db
from chat import Chat
from kagi import search, summarize
from reminders import Reminders
from spotify import add_to_playlist

COOKIES_PATH = os.environ.get("FB_COOKIES_PATH", "ufc-facebook.json")
GC_THREAD_ID = os.environ["GROUPID"]

chat: Chat
client: Client
reminders: Reminders
last_persona = db.load("last_persona", "misc.sqlite3")


async def async_wrapper(sync_func, *args, timeout_duration=20, **kwargs) -> str:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(pool, lambda: sync_func(*args, **kwargs)),
                timeout=timeout_duration,
            )
        except asyncio.TimeoutError:
            return "Request timed out"


def get_image_attachment(message_object):
    if message_object is None:
        return None
    for attachment in (message_object.attachments or []):
        if isinstance(attachment, ImageAttachment) and not getattr(attachment, "render_as_sticker", False):
            return attachment
    return None


def image_url(attachment: ImageAttachment) -> str:
    return attachment.large_preview.url


async def persona_send(persona: str, message: str, mention: Mention | None = None):
    text = f"{persona}:\n{message}"
    mentions = [mention] if mention else None
    await client.send_message(text, GC_THREAD_ID, mentions=mentions)


async def id_to_username_dict() -> dict[str, str]:
    threads = await client.fetch_thread_info([GC_THREAD_ID])
    group = threads[0]
    return {str(u.id): u.name for u in (group.all_participants or ())}


async def get_context(words=None, message_object: Message | None = None, persona: str | None = None):
    for_persona: bool = bool(words and message_object and persona)
    user_dict = await id_to_username_dict()
    messages = await client.fetch_thread_messages(GC_THREAD_ID, message_limit=30) or []

    query = ""
    if for_persona:
        query = " ".join(word for word in words if not word.startswith("!"))
        query = "{}: {}".format(user_dict.get(str(message_object.sender_id), "?"), query)
        for i, m in enumerate(messages):
            if m.text and m.text.startswith("!reset"):
                messages = messages[:i]
                break

    messages.reverse()

    context_messages = []
    for m in messages:
        attachment = get_image_attachment(m)
        if attachment:
            url = image_url(attachment)
            description = db.load(url, "image_descs.sqlite3")
            if not description:
                description = await async_wrapper(chat.imageResponse, url, "Describe this image in detail")
                db.save(url, description, "image_descs.sqlite3")
            m_text = "[IMAGE]: " + description
        else:
            if m.text is not None:
                m_text = " ".join(w for w in m.text.split() if not (w.startswith("!") or w.startswith("@")))
            else:
                m_text = "[NON-TEXT MESSAGE]"

        if len(m_text) == 0:
            continue

        sender_id = str(m.sender_id)
        user_name = user_dict.get(sender_id, "?")

        if for_persona and sender_id == client.uid:
            m_split = m_text.split(":")
            user_name = m_split.pop(0)
            m_text = " ".join(m_split)
            if user_name != persona:
                context_messages.append({"role": "user", "content": f"{user_name}: {m_text}"})
            else:
                context_messages.append({"role": "assistant", "content": m_text})
        else:
            context_messages.append({"role": "user", "content": f"{user_name}: {m_text}"})

    context_messages = context_messages[: len(context_messages) - 1]
    return (query, context_messages) if for_persona else context_messages


async def handle_message(message_object: Message):
    global last_persona

    author_id = str(message_object.sender_id)
    thread_id = str(message_object.thread_id)

    await client.mark_as_read(thread_id)

    if author_id == client.uid or thread_id != GC_THREAD_ID:
        return

    message = message_object.text or ""
    if not message:
        return

    words = message.split()
    if not words:
        return
    persona = "BP Bot"
    cmd = words.pop(0)
    first_char_of_cmd = cmd[0]

    replied = message_object.replied_to_message

    match cmd:
        case "!notes":
            persona = "Notes"
            try:
                notes_cmd = words.pop(0)
            except IndexError:
                notes_cmd = "list"
            match notes_cmd:
                case "set":
                    reply = ""
                    if replied:
                        if replied.text:
                            note_name = " ".join(words)
                            db.save(note_name, replied.text, "notes.sqlite3")
                            reply = note_name + " has been set."
                        else:
                            reply = "Cannot get responded message text"
                    else:
                        reply = "Repond to the note you'd like to save"
                    await persona_send(persona, reply)
                case "get":
                    note_name = " ".join(words)
                    response = db.load(note_name, "notes.sqlite3")
                    await persona_send(persona, response)
                case "list":
                    response = db.keysList("notes.sqlite3")
                    await persona_send(persona, response)
                case "clear":
                    note_name = words.pop(0)
                    db.clear(note_name, "notes.sqlite3")
                    await persona_send(persona, note_name + " has been cleared.")
                case "help":
                    help_list = ["Commands:", "- set", "- get", "- list", "- clear"]
                    await persona_send(persona, "\n".join(help_list))

        case "!c" | "!chat":
            response = ""
            limit = 1000
            query = " ".join(words)
            if len(words) >= limit:
                response = f"Prompt too long (over {limit} words)"
            else:
                attachment = get_image_attachment(replied)
                if attachment:
                    response = await async_wrapper(chat.imageResponse, image_url(attachment), query)
                else:
                    response = await async_wrapper(chat.chatResponse, query)
            await persona_send(persona, response)

        case "!f" | "!fast":
            (query, context) = await get_context(words, message_object, persona)
            response = await async_wrapper(chat.fastResponse, query, context)
            await persona_send(persona, response)

        case "!t" | "!tyco":
            persona = "Tyco"
            (query, context) = await get_context(words, message_object, persona)
            response = await async_wrapper(chat.tycoResponse, query, context)
            await persona_send(persona, response)

        case "!summarize":
            if replied and replied.text:
                url = replied.text
            else:
                url = " ".join(words)
            response = await async_wrapper(summarize, url)
            await persona_send(persona, response)

        case "!s" | "!search":
            url = " ".join(words)
            response = await async_wrapper(search, url)
            response = response.replace("*", "")
            await persona_send(persona, response)

        case "!refs":
            response = db.load("references", "refs.sqlite3")
            await persona_send(persona, response)

        case "!test":
            persona = "Test"
            await persona_send(persona, "Hello")

        case "!remind":
            persona = "Reminder"
            try:
                reminder_cmd = words.pop(0)
            except IndexError:
                reminder_cmd = "list"
            match reminder_cmd:
                case "set":
                    reminder_text = ""
                    if replied and replied.text:
                        reminder_text = replied.text
                    time_str = " ".join(words)
                    user_dict = await id_to_username_dict()
                    await reminders.parse_command(
                        persona_send,
                        author_id,
                        user_dict.get(author_id, "?"),
                        reminder_text,
                        time_str,
                    )
                case "list":
                    await persona_send(persona, reminders.list_reminders())
                case "clear":
                    rid = int(words.pop(0))
                    reminders.clear_reminder(rid)
                    await persona_send(persona, f"{rid} has been cleared.")
                case "help":
                    help_list = ["Commands:", "- set", "- list", "- clear"]
                    await persona_send(persona, "\n".join(help_list))

        case "!personas":
            try:
                personas_cmd = words.pop(0)
            except IndexError:
                personas_cmd = "list"
            match personas_cmd:
                case "create":
                    persona_name = words.pop(0)
                    db.save(persona_name.lower(), " ".join(words), "personas.sqlite3")
                    await persona_send(persona, f"{persona_name} is now alive. Type '@{persona_name} [your message]' to call them.")
                case "get":
                    persona_name = " ".join(words)
                    response = db.load(persona_name.lower(), "personas.sqlite3")
                    await persona_send(persona_name, response)
                case "list":
                    response = db.keysList("personas.sqlite3")
                    await persona_send("All personas", response)
                case "clear":
                    persona_name = words.pop(0)
                    db.clear(persona_name.lower(), "personas.sqlite3")
                    await persona_send(persona, persona_name + " has been cleared.")
                case "help":
                    help_list = ["Commands:", "- create", "- get", "- list", "- clear"]
                    await persona_send(persona, "\n".join(help_list))

        case "!help":
            help_list = [
                "Commands:",
                "- !(c)hat",
                "- !(t)yco",
                "- !(s)earch",
                "- !refs",
                "- !personas",
                "- !notes",
                "- !summarize",
                "- !remind",
                "- !test",
                "- @[persona]",
            ]
            await persona_send(persona, "\n".join(help_list))

        case _:
            if match := re.search(r"https:\/\/open\.spotify\.com\/track\/[a-zA-Z0-9]{22}", message):
                add_to_playlist(match.group())
            elif re.search(r"https?://(www\.)?instagram\.com/reel/[A-Za-z0-9-_]+/?", message) or re.search(r"https?://(www\.)?youtube\.com/shorts/[A-Za-z0-9-_]+", message):
                await client.react("😡", message_object.id, thread_id)

    if first_char_of_cmd == "@" and not (message_object.mentions or []):
        if cmd == "@" and last_persona is not None:
            persona_name = last_persona
        else:
            persona_name = cmd[1:]
            last_persona = persona_name
            if persona_name.isnumeric():
                persona_name = db.numberToKey(persona_name, "personas.sqlite3")
            db.save("last_persona", last_persona, "misc.sqlite3")
        (query, context) = await get_context(words, message_object, persona_name)
        persona_prompt = db.load(persona_name.lower(), "personas.sqlite3")
        if persona_prompt is None:
            await persona_send(persona, f"{persona_name} does not exist")
        else:
            response = await async_wrapper(chat.personaResponse, persona_prompt, query, context)
            await persona_send(persona_name, response)


async def handle_reaction(reaction: MessageReaction):
    if reaction.reaction == "😡":
        await client.unsend(reaction.id, str(reaction.thread_id))


async def main():
    global chat, client, reminders

    chat = Chat()
    reminders = Reminders()

    async with Client(COOKIES_PATH) as c:
        client = c

        @client.event(EventType.MESSAGE)
        async def _on_message(message_object: Message):
            try:
                await handle_message(message_object)
            except Exception as e:
                print(f"handle_message error: {e!r}")

        @client.event(EventType.MESSAGE_REACTION)
        async def _on_reaction(reaction: MessageReaction):
            try:
                await handle_reaction(reaction)
            except Exception as e:
                print(f"handle_reaction error: {e!r}")

        reminders.start(client, persona_send)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, reminders.save_quit_reminders)

        await client.listen()


if __name__ == "__main__":
    asyncio.run(main())
