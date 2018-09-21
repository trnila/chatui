import paho.mqtt.client as mqtt
import time
import threading
import datetime
import argparse
import random
import ui
import logging


class Chat:
    def __init__(self, options):
        self.username = options.username


        self.client = mqtt.Client(client_id=self.username)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message


    def connect(self):
        time.sleep(1)
        # pcfeib425t.vsb.cz
        self.client.connect("localhost", 1883, 60)
        self.client.loop_forever()

    def send(self, msg, dst):
        msg = "{} {}".format(int(time.time()), msg)
        self.client.publish(f'/mschat/{dst}/{self.username}', msg)

    def _on_connect(self, client, userdata, flags, rc):
        try:
            logging.debug("Connected")
            client.subscribe("/mschat/#")
            client.will_set(f'/mschat/status/{self.username}', 'offline', qos=2, retain=True)
            client.publish(f'/mschat/status/{self.username}', 'online')
            self.send("cus", "all")
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
                    'timestamp': timestamp,
                    'author': author,
                    'text': text
                })
            elif msg.topic.startswith('/mschat/status/'):
                author = msg.topic.replace('/mschat/status/', '')
                status = msg.payload.decode('utf-8')
                logging.debug("**** User {} is now {}".format(author, status))
                self.subscriber.send("status", {
                    'user': author,
                    'status': status
                })
            else:
                logging.debug(msg.topic, msg.payload)
        except Exception as e:
            logging.exception(e)

logging.basicConfig(level=logging.DEBUG, filename='/tmp/log')



parser = argparse.ArgumentParser()
parser.add_argument('--username', default='daniel_' + str(random.randint(0, 10000)))
parser.add_argument('--server', default='localhost')

options = parser.parse_args()

chat = Chat(options)
App = ui.TestApp()
chat.subscriber = App
App.x = chat

t = threading.Thread(target=chat.connect)
t.start()

App.run()
