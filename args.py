import argparse
import random


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', default='daniel_' + str(random.randint(0, 10)))
    parser.add_argument('--server', default='localhost')
    parser.add_argument('--port', default=1883, type=int)
    parser.add_argument('--log-file', default='/tmp/log', help='path to logfile')

    return parser