from datetime import datetime
import threading
import time
from ctparse import ctparse
import pickle
from fbchat.models import Mention
PERSONA = "Reminder"

class Reminders:
    def __init__(self):
        filename = 'datetimes.pkl'

        try:
            with open(filename, 'rb') as f:
                self.reminders = pickle.load(f)
        except Exception as e:
            self.reminders = []

    def check_reminders(self, client):
        while True:
            now = datetime.now()
            for reminder in self.reminders.copy():  # Use a copy of the list for safe removal
                user_id, user_name, reminder_text, trigger_time = reminder
                if now >= trigger_time:
                    mention = f"@{user_name}"
                    mention_obj = Mention(thread_id=user_id, offset=len(PERSONA) + 1, length=len(mention)+2)
                    client.personaSend(PERSONA, f"{mention}, {reminder_text}", mention=mention_obj)
                    self.reminders.remove(reminder)
            time.sleep(10)  # Check every 10 seconds

    def start(self, client):
        threading.Thread(target=self.check_reminders, args=[client], daemon=True).start()

    def parse_command(self, client, user_id, user_name, reminder, time):
        # Assuming command format: "Remind me to <task> at <natural language time>"
        result = ctparse(time)
        if result and result.resolution:
            # Assuming the result's resolution is a datetime object
            trigger_time = result.resolution.dt
            self.reminders.append((user_id, user_name, reminder, trigger_time))
            client.personaSend(PERSONA, f"'{reminder}' has been set for {trigger_time}")
        else:
            return "No valid time information found."

    def list_reminders(self):
        reminder_list = ""
        i = 0
        for reminder in self.reminders.copy():  # Use a copy of the list for safe removal
            user_id, user_name, reminder_text, trigger_time = reminder
            reminder_list += "{} - {}, {}, {}\n".format(i, user_name, reminder_text, trigger_time)
            i += 1
        return reminder_list

    def clear_reminder(self, num):
        self.reminders.pop(num)

    def save_quit_reminders(self, signal, frame):
        filename = 'datetimes.pkl'
        with open(filename, 'wb') as f:
            pickle.dump(self.reminders, f)
        print("Data saved. Exiting.")
        exit(0)

    def load_datetimes(self):
        with open('datetimes.pkl', 'rb') as f:
            loaded_datetimes = pickle.load(f)
        return loaded_datetimes
