#!/usr/bin/env python3
import threading
import ui
import logging
import args

from chat import Chat


parser = args.create_parser()
options = parser.parse_args()

logging.basicConfig(level=logging.DEBUG, filename=options.log_file)

chat = Chat(parser.parse_args())
App = ui.ChatApp(chat)

t = threading.Thread(target=chat.connect)
t.daemon = True
t.start()

try:
    App.run()
except KeyboardInterrupt as e:
    pass
