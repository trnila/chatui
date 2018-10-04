import threading
import time
import datetime
import logging
import pickle
import paho.mqtt.client as mqtt


class Event:
    STATUS = 'status'
    PM = 'private_message'
    NEW_MESSAGE = 'new_message'


class Chat:
    def __init__(self, options):
        self.username = options.username
        self.options = options

        self.connected = True
        self.users_path = '/tmp/users'

        try:
            with open(self.users_path, "rb") as f:
                self.users = pickle.load(f)
        except:
            self.users = {}

        self.client = mqtt.Client(client_id=self.username, clean_session=False)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self.client.will_set(f'/mschat/status/{self.username}', 'offline', qos=2, retain=True)
        self.subscriber = None

        self.queue = []

        self.disconnect_timer = None

    def connect(self):
        for user, status in self.users.items():
            self.subscriber(Event.STATUS, {
                'user': user,
                'status': status
            })

        try:
            self.client.connect(self.options.server, self.options.port, 60)
        except ConnectionRefusedError as e:
            logging.exception(e)
        self.client.loop_forever()

    def disconnect(self):
        self.client.publish(f'/mschat/status/{self.username}', 'offline', qos=2, retain=True).wait_for_publish()
        self.client.disconnect()

    def send(self, text, dst = 'all'):
        if not self.connected:
            logging.info("Offline, will send on reconnect")
            self.queue.append((text, dst))
        else:
            if dst != 'all':
                self.subscriber(Event.PM, {
                    'datetime': datetime.datetime.now(),
                    'channel': dst,
                    'author': self.username,
                    'text': text
                })
                dst = f'user/{dst}'
            msg = "{} {}".format(int(time.time()), text)
            self.client.publish(f'/mschat/{dst}/{self.username}', msg)

    def _on_connect(self, client, userdata, flags, rc):
        try:
            logging.debug("Connected")
            if self.disconnect_timer:
                self.disconnect_timer.cancel()
            client.subscribe("/mschat/#")
            client.publish(f'/mschat/status/{self.username}', 'online', qos=2, retain=True)
            self.connected = True

            for (text, dst) in self.queue:
                logging.info("Resending %s after reconnect", text)
                self.send(text, dst)

        except Exception as e:
            logging.exception(e)

    def disconnect_all(self):
        for username in self.users.keys():
            if self.users[username] != 'offline':
                self.users[username] = 'offline'
                self.subscriber(Event.STATUS, {
                    'user': username,
                    'status': 'offline'
                })

        self.persist_users()

    def _on_disconnect(self, client, userdata, rc):
        logging.debug("Disconnected")
        self.connected = False
        self.disconnect_timer = threading.Timer(3, self.disconnect_all)
        self.disconnect_timer.start()

    def _on_message(self, client, userdata, msg):
        try:
            if msg.topic.startswith("/mschat/all"):
                author = msg.topic.replace('/mschat/all/', '')
                date, text = self.parse_message(msg)
                logging.debug("{:%H:%M:%S} <{}>: {}".format(date, author, text))

                self.subscriber(Event.NEW_MESSAGE, {
                    'datetime': date,
                    'author': author,
                    'text': text
                })
            elif msg.topic.startswith('/mschat/status/'):
                author = msg.topic.replace('/mschat/status/', '')
                status = msg.payload.decode('utf-8')
                logging.debug("**** User {} is now {}".format(author, status))

                self.users[author] = status
                self.persist_users()

                self.subscriber(Event.STATUS, {
                    'user': author,
                    'status': status
                })
            elif msg.topic.startswith('/mschat/user/'):
                topic = msg.topic.replace('/mschat/user/', '')
                receiver, sender = topic.split('/', 2)

                if receiver == self.username:
                    author = sender
                elif sender == self.username:
                    author = receiver
                else:
                    # msg not for me
                    return

                date, text = self.parse_message(msg)
                logging.debug("{:%H:%M:%S} <{}>: {}".format(date, author, text))

                self.subscriber(Event.PM, {
                    'datetime': date,
                    'channel': author,
                    'author': sender,
                    'text': text
                })
            else:
                logging.debug(msg.topic, msg.payload)
        except Exception as e:
            logging.exception(e)

    def parse_message(self, line):
        try:
            timestamp, text = line.payload.decode('utf-8').split(' ', 1)
            date = datetime.datetime.fromtimestamp(int(timestamp))
            return date, text
        except ValueError as e:
            return datetime.datetime.now(), line.payload.decode('utf-8')

    def persist_users(self):
        with open(self.users_path, 'wb') as f:
            pickle.dump(self.users, f)