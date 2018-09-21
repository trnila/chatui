import paho.mqtt.client as mqtt
import time
import threading
import datetime
import sys

user = sys.argv[1]

def on_connect(client, userdata, flags, rc):
    client.will_set(f'/mschat/status/{user}', 'offline')
    client.subscribe("/mschat/#")
    client.publish(f'/mschat/status/{user}', 'online')

def on_message(client, userdata, msg):
    try:
        if msg.topic.startswith("/mschat/all"):
            author = msg.topic.replace('/mschat/all/', '')
            timestamp, text = msg.payload.decode('utf-8').split(' ', 2)
            date = datetime.datetime.fromtimestamp(int(timestamp))
            print("{:%H:%M:%S} <{}>: {}".format(date, author, text))
        elif msg.topic.startswith('/mschat/status/'):
            author = msg.topic.replace('/mschat/status/', '')
            print("**** User {} is now {}".format(author, msg.payload.decode('utf-8')))
        else:
            print(msg.topic, msg.payload)
    except Exception as e:
        print(e)
        print(msg.payload)

def send(msg, dst):
    msg = "{} {}".format(int(time.time()), msg)
    client.publish(f'/mschat/{dst}/{user}', msg)

client = mqtt.Client(client_id=user)
client.on_connect = on_connect
client.on_message = on_message
client.connect("pcfeib425t.vsb.cz", 1883, 60)

def sender():
    while True:
        msg = input("> ")
        dst = 'all'
        if msg.startswith('/msg'):
            dst = msg.split(' ')[1]

        send(msg, dst)

t = threading.Thread(target=sender)
t.start()

client.loop_forever()
