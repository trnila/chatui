import collections


class NPSEventQueue(object):
    def __init__(self):
        self.interal_queue = collections.deque()

    def get(self, maximum=None):
        if maximum is None:
            maximum = -1
        counter = 1
        while counter != maximum:
            try:
                yield self.interal_queue.pop()
            except IndexError:
                pass
            counter += 1

    def put(self, event):
        self.interal_queue.append(event)