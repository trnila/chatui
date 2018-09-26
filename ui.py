#!/usr/bin/env python
import npyscreen
import curses
import logging
import os

import patches


class TabWidget(npyscreen.widget.Widget):
    def __init__(self, screen, **keywords):
        super().__init__(screen, **keywords)
        
    def set_up_handlers(self):
        super(TabWidget, self).set_up_handlers()
        del self.handlers['^P']

    def update(self, clear=True):
        x = 0

        app: ChatApp = self.find_parent_app()

        for item in app.opened_chats:
            color = 0
            if app.opened_chats[app.current_chat] == item:
                color = self.parent.theme_manager.findPair(self, 'IMPORTANT') | curses.A_BOLD

            label = item
            if label == 'MAIN':
                label = '#all'
            else:
                label = item.replace('CHAT/', '')

            self.parent.curses_pad.addstr(0, x, label, color)
            x += len(label) + 2


class UsersInRoomWidget(npyscreen.wgmultiline.MultiLine):
    def _print_line(self, line, value_indexer):
        super(UsersInRoomWidget, self)._print_line(line, value_indexer)
        if not self.do_colors() or not line.value:
            return

        status, username = line.value.split(' ', 2)

        line.show_bold = True
        if status == '[online]':
            line.color = 'IMPORTANT'
            line.value = username
        elif status == '[offline]':
            line.color = 'DANGER'
            line.value = username
        else:
            logging.warning("Unknown user %s status %s", username, status)

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

        if not self.users.hidden:
            self.curses_pad.vline(1, MAXX - self.USERS_COLUMNS - 1, curses.ACS_VLINE, MAXY - 3)

    def create(self):
        MAXY, MAXX = self.lines, self.columns
        self.add(TabWidget, editable=False)

        self.wMain = self.add(
            npyscreen.wgmultiline.BufferPager,
            rely=1,
            relx=0,
            max_height=-2,
            max_width=self.columns - self.USERS_COLUMNS - 1,
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
            UsersInRoomWidget,
            rely=1,
            relx=self.columns - self.USERS_COLUMNS,
            max_height=-2
        )

        self.wStatus2.important = True
        self.nextrely = 2

    def resize(self):
        super(ChatForm, self).resize()
        size = os.get_terminal_size()
        self.lines = size.lines
        self.columns = size.columns

        self.wMain.max_width = self.columns - self.USERS_COLUMNS - 1
        self.wStatus2.rely = self.lines - 2 - self.BLANK_LINES_BASE
        self.wCommand.rely = self.lines - 1 - self.BLANK_LINES_BASE
        self.users.relx = self.columns - self.USERS_COLUMNS


class User:
    def __init__(self, user, status):
        self.user = user
        self.status = status

    def __str__(self):
        return f"[{self.status}] {self.user}"


class ChatApp(npyscreen.StandardApp):
    MESSAGE_FORMAT = "{datetime:%H:%M:%S} {author}: {text}"

    MAINQUEUE_TYPE = patches.NPSEventQueue

    def __init__(self, chat):
        super().__init__()
        self.chat = chat
        self.chat.subscriber = self.send
        self.opened_chats = ['MAIN']
        self.current_chat = 0

    def onStart(self):
        F = self.addForm("MAIN", ChatForm)
        self.setup_chat(F, "#all")

        self.add_event_hander("new_message", self.on_message)
        self.add_event_hander("status", self.on_status)
        self.add_event_hander("private_message", self.on_private_message)

    def setup_chat(self, F, channel):
        F.wCommand.add_handlers({curses.ascii.NL: lambda x: self.entered()})
        del F.wCommand.handlers['^P']
        del F.users.handlers['^P']

        if channel != '#all':
            F.users.hidden = True

        F.users.add_handlers({curses.ascii.NL: self.open_chat})
        F.add_handlers({
            "^P": lambda x: self.next_chat(),
            '^W': lambda x: self.close_current_window()
        })
        F.wStatus2.value = f"({self.chat.username}) "

    def entered(self):
        try:
            F = self.get_active_chat()
            message = F.wCommand.value.strip()
            if not message:
                return

            if message.startswith('/'):
                args = message.split(' ')
                cmd = args.pop(0)

                if cmd == '/msg':
                    self.chat.send(' '.join(args[1:]), args[0])
                elif cmd == '/close':
                    self.close_current_window()
                else:
                    logging.info("Unknown command %s", cmd)
            else:
                dst = self.opened_chats[self.current_chat]
                if dst == 'MAIN':
                    dst = 'all'
                else:
                    dst = dst.replace('CHAT/', '')
                self.chat.send(message, dst)
            F.wCommand.value = ""
            F.wMain.update()
        except Exception as e:
            logging.exception(e)

    def get_active_chat(self):
        return self.getForm(self.opened_chats[self.current_chat])

    def next_chat(self):
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
            form = self.addForm(name, ChatForm)
            self.opened_chats.append(name)
            self.setup_chat(form, user)
            return form

    def on_status(self, evt):
        F = self.getForm("MAIN")
        F.users.values = [User(user, status) for user, status in self.chat.users.items()]
        F.users.update()

    def on_message(self, evt):
        F = self.getForm("MAIN")
        F.wMain.buffer([self.MESSAGE_FORMAT.format(**evt.payload)], True, True)
        F.wMain.update()

    def on_private_message(self, evt):
        F = self.get_chat(evt.payload['channel'])
        F.wMain.buffer([self.MESSAGE_FORMAT.format(**evt.payload)], True, True)
        F.wMain.update()

    def send(self, event, payload):
        self.queue_event(npyscreen.Event(event, payload))

    def close_current_window(self):
        channel_name = self.opened_chats[self.current_chat]
        if channel_name == 'MAIN':
            return

        self.removeForm(channel_name)
        del self.opened_chats[self.current_chat]

        self.next_chat()
