import time
import datetime
import logging
import paho.mqtt.client as mqtt


class Chat:
    def __init__(self, options):
        self.username = options.username
        self.options = options

        self.users = {}

        self.client = mqtt.Client(client_id=self.username)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        self.client.will_set(f'/mschat/status/{self.username}', 'offline', qos=2, retain=True)

    def connect(self):
        try:
            self.client.connect(self.options.server, self.options.port, 60)
        except ConnectionRefusedError as e:
            logging.exception(e)
        self.client.loop_forever()

    def send(self, text, dst):
        if dst != 'all':
            self.subscriber.send("private_message", {
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
            client.subscribe("/mschat/#")
            client.publish(f'/mschat/status/{self.username}', 'online', qos=2, retain=True)
        except Exception as e:
            logging.exception(e)

    def _on_message(self, client, userdata, msg):
        try:
            if msg.topic.startswith("/mschat/all"):
                author = msg.topic.replace('/mschat/all/', '')
                timestamp, text = msg.payload.decode('utf-8').split(' ', 1)
                date = datetime.datetime.fromtimestamp(int(timestamp))
                logging.debug("{:%H:%M:%S} <{}>: {}".format(date, author, text))

                self.subscriber.send("new_message", {
                    'datetime': date,
                    'author': author,
                    'text': text
                })
            elif msg.topic.startswith('/mschat/status/'):
                author = msg.topic.replace('/mschat/status/', '')
                status = msg.payload.decode('utf-8')
                logging.debug("**** User {} is now {}".format(author, status))

                self.users[author] = status

                self.subscriber.send("status", {
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
                    logging.info("msg not for me!")
                    return

                try:
                    timestamp, text = msg.payload.decode('utf-8').split(' ', 1)
                    date = datetime.datetime.fromtimestamp(int(timestamp))
                except ValueError:
                    text = msg.payload.decode('utf-8')
                    date = datetime.datetime.now()
                logging.debug("{:%H:%M:%S} <{}>: {}".format(date, author, text))

                self.subscriber.send("private_message", {
                    'datetime': date,
                    'channel': author,
                    'author': sender,
                    'text': text
                })
            else:
                logging.debug(msg.topic, msg.payload)
        except Exception as e:
            logging.exception(e)