from datetime import datetime
import threading
import time
from ctparse import ctparse
import pickle

class Reminders:
    def __init__(self):
        filename = 'datetimes.pkl'

        try:
            with open(filename, 'rb') as f:
                self.reminders = pickle.load(f)
        except FileNotFoundError:
            self.reminders = []

    def add_reminder(self, reminder_text, trigger_time):
        self.reminders.append((reminder_text, trigger_time))
        return f"Reminder set for: {trigger_time}"

    def check_reminders(self, client):
        while True:
            now = datetime.now()
            for reminder in self.reminders.copy():  # Use a copy of the list for safe removal
                reminder_text, trigger_time = reminder
                if now >= trigger_time:
                    client.personaSend("Reminder", f"{reminder_text}")
                    self.reminders.remove(reminder)
            time.sleep(10)  # Check every 10 seconds

    def start(self, client):
        threading.Thread(target=self.check_reminders, args=[client], daemon=True).start()

    def parse_command(self, reminder, time):
        # Assuming command format: "Remind me to <task> at <natural language time>"
        result = ctparse(time)
        if result and result.resolution:
            # Assuming the result's resolution is a datetime object
            trigger_time = result.resolution.dt
            self.add_reminder(reminder, trigger_time)
        else:
            return "No valid time information found."

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
