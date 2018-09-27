import logging
import subprocess


class NullNotifications:
    def send(self, message):
        pass


class NotifySendNotification(NullNotifications):
    def __init__(self):
        self.enabled = True

    def send(self, message):
        if not self.enabled:
            return False

        try:
            subprocess.Popen(['notify-send', message])
        except Exception as e:
            logging.exception(e)
            self.enabled = False
