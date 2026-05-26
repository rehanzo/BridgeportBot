import asyncio
import os
import pickle
from datetime import datetime

from ctparse import ctparse
from fbchat_muqit import Mention

PERSONA = "Reminder"
GC_THREAD_ID = os.environ["GROUPID"]


class Reminders:
    def __init__(self):
        filename = "datetimes.pkl"
        try:
            with open(filename, "rb") as f:
                self.reminders = pickle.load(f)
        except Exception:
            self.reminders = []

    async def check_reminders(self, client, persona_send):
        while True:
            now = datetime.now()
            for reminder in self.reminders.copy():
                user_id, user_name, reminder_text, trigger_time = reminder
                if now >= trigger_time:
                    mention_text = f"@{user_name}"
                    mention = Mention(
                        user_id=str(user_id),
                        offset=len(PERSONA) + 2,
                        length=len(mention_text),
                    )
                    await persona_send(
                        PERSONA,
                        f"{mention_text}, {reminder_text}",
                        mention=mention,
                    )
                    self.reminders.remove(reminder)
            await asyncio.sleep(10)

    def start(self, client, persona_send):
        return asyncio.create_task(self.check_reminders(client, persona_send))

    async def parse_command(self, persona_send, user_id, user_name, reminder, time_str):
        result = ctparse(time_str)
        if result and result.resolution:
            trigger_time = result.resolution.dt
            self.reminders.append((user_id, user_name, reminder, trigger_time))
            await persona_send(PERSONA, f"'{reminder}' has been set for {trigger_time}")
        else:
            await persona_send(PERSONA, "No valid time information found.")

    def list_reminders(self):
        reminder_list = ""
        for i, reminder in enumerate(self.reminders.copy()):
            _, user_name, reminder_text, trigger_time = reminder
            reminder_list += f"{i} - {user_name}, {reminder_text}, {trigger_time}\n"
        return reminder_list

    def clear_reminder(self, num):
        self.reminders.pop(num)

    def save_quit_reminders(self, signal=None, frame=None):
        filename = "datetimes.pkl"
        with open(filename, "wb") as f:
            pickle.dump(self.reminders, f)
        print("Data saved. Exiting.")
