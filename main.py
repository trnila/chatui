#!/usr/bin/env python3
import threading
import argparse
import random
import ui
import logging

from chat import Chat

logging.basicConfig(level=logging.DEBUG, filename='/tmp/log')

parser = argparse.ArgumentParser()
parser.add_argument('--username', default='daniel_' + str(random.randint(0, 10)))
parser.add_argument('--server', default='localhost')
parser.add_argument('--port', default=1883, type=int)

options = parser.parse_args()

chat = Chat(options)
App = ui.ChatApp(chat)

t = threading.Thread(target=chat.connect)
t.daemon = True
t.start()

try:
    App.run()
except KeyboardInterrupt as e:
    pass
