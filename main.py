#!/usr/bin/env python3
import threading
import argparse
import random
import ui
import logging
import args

from chat import Chat

logging.basicConfig(level=logging.DEBUG, filename='/tmp/log')


parser = args.create_parser()
chat = Chat(parser.parse_args())
App = ui.ChatApp(chat)

t = threading.Thread(target=chat.connect)
t.daemon = True
t.start()

try:
    App.run()
except KeyboardInterrupt as e:
    pass
