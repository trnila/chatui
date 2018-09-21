#!/usr/bin/env python
import npyscreen
import curses
import logging


class ChatForm(npyscreen.fmForm.FormBaseNew):
    BLANK_LINES_BASE = 0
    BLANK_COLUMNS_RIGHT = 0

    USERS_COLUMNS = 20

    def __init__(self, cycle_widgets=True, *args, **keywords):
        super(ChatForm, self).__init__(cycle_widgets=cycle_widgets, *args, **keywords)

    def draw_form(self):
        MAXY, MAXX = self.lines, self.columns  # self.curses_pad.getmaxyx()
        self.curses_pad.hline(0, 0, curses.ACS_HLINE, MAXX - 1)
        self.curses_pad.hline(MAXY - 2 - self.BLANK_LINES_BASE, 0, curses.ACS_HLINE, MAXX - 1)

    def create(self):
        MAXY, MAXX = self.lines, self.columns

        self.wStatus1 = self.add(npyscreen.wgtextbox.Textfield, editable=False)

        self.wMain = self.add(
            npyscreen.wgmultiline.BufferPager,
            rely=1,
            relx=0,
            max_height=-2,
            max_width=self.columns - self.USERS_COLUMNS,
            autowrap=True
        )

        self.wStatus2 = self.add(
            npyscreen.Textfield, rely=MAXY - 2 - self.BLANK_LINES_BASE,
            relx=0,
            editable=False,
        )

        self.wCommand = self.add(
            npyscreen.wgtextbox.Textfield,
            rely=MAXY - 1 - self.BLANK_LINES_BASE,
            relx=0
        )

        self.users = self.add(
            npyscreen.wgmultiline.MultiLine,
            rely=0,
            relx=self.columns - self.USERS_COLUMNS, max_height=-2, )

        self.wStatus1.important = True
        self.wStatus2.important = True
        self.nextrely = 2

    def resize(self):
        super(ChatForm, self).resize()
        MAXY, MAXX = self.lines, self.columns
        self.wStatus2.rely = MAXY - 2 - self.BLANK_LINES_BASE
        self.wCommand.rely = MAXY - 1 - self.BLANK_LINES_BASE


class User:
    def __init__(self, user, status):
        self.user = user
        self.status = status

    def __str__(self):
        return f"[{self.status}] {self.user}"


class ChatApp(npyscreen.StandardApp):
    def __init__(self):
        super().__init__()
        self.opened_chats = ['MAIN']
        self.current_chat = 0

    def onStart(self):
        F = self.addForm("MAIN", ChatForm)
        self.setup_chat(F, "#all")

        self.add_event_hander("new_message", self.on_message)
        self.add_event_hander("status", self.on_status)
        self.add_event_hander("private_message", self.on_private_message)

    def setup_chat(self, F, channel):
        F.wStatus1.value = channel
        F.wCommand.add_handlers({curses.ascii.NL: self.entered})
        F.users.add_handlers({curses.ascii.NL: self.open_chat})
        F.add_handlers({
            "^P": self.next_chat,
            "^C": self.next_chat
        })
        F.wStatus2.value = f"({self.x.username}) "

    def entered(self, nop):
        try:
            F = self.get_active_chat()
            message = F.wCommand.value

            if message.startswith('/'):
                args = message.split(' ')
                cmd = args.pop(0)

                if cmd == '/msg':
                    self.x.send(' '.join(args[1:]), args[0])
                else:
                    logging.info("Unknown command %s", cmd)
            else:
                self.x.send(message, F.wStatus1.value.replace('#', ''))
            F.wCommand.value = ""
            F.wMain.update()
        except Exception as e:
            logging.exception(e)

    def get_active_chat(self):
        return self.getForm(self.opened_chats[self.current_chat])

    def next_chat(self, nop):
        self.current_chat = (self.current_chat + 1) % len(self.opened_chats)
        self.switchForm(self.opened_chats[self.current_chat])

    def open_chat(self, nop):
        F = self.getForm("MAIN")
        selected = F.users.values[F.users.cursor_line]
        self.get_chat(selected.user)
        name = f"CHAT/{selected.user}"
        self.current_chat = self.opened_chats.index(name)
        self.switchForm(name)

    def get_chat(self, user):
        name = f"CHAT/{user}"
        try:
            return self.getForm(name)
        except KeyError as e:
            self.opened_chats.append(name)
            form = self.addForm(name, ChatForm)
            self.setup_chat(form, user)
            return form

    def on_status(self, evt):
        F = self.getForm("MAIN")
        F.users.values.append(User(evt.payload['user'], evt.payload['status']))
        F.users.display()

    def on_message(self, evt):
        F = self.getForm("MAIN")
        F.wMain.buffer(["{datetime:%H:%M:%S} {author}: {text}".format(**evt.payload)], True, True)
        F.wMain.update()
        F.wMain.display()

    def on_private_message(self, evt):
        F = self.get_chat(evt.payload['channel'])
        F.wMain.buffer(["{datetime} {author}: {text}".format(**evt.payload)], True, True)
        F.wMain.display()

    def send(self, event, payload):
        self.queue_event(npyscreen.Event(event, payload))
