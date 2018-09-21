#!/usr/bin/env python
import npyscreen
import curses
import logging
import os
import threading
import queue
import re

class FormMutt(npyscreen.fmForm.FormBaseNew):
    BLANK_LINES_BASE     = 0
    BLANK_COLUMNS_RIGHT  = 0
    DEFAULT_X_OFFSET = 2
    FRAMED = False
    #MAIN_WIDGET_CLASS   = npyscreen.wgmultiline.MultiLine
    MAIN_WIDGET_CLASS   = npyscreen.wgmultiline.BufferPager
    MAIN_WIDGET_CLASS_START_LINE = 1
    STATUS_WIDGET_CLASS = npyscreen.wgtextbox.Textfield
    STATUS_WIDGET_X_OFFSET = 0
    COMMAND_WIDGET_CLASS= npyscreen.wgtextbox.Textfield
    COMMAND_WIDGET_NAME = None
    COMMAND_WIDGET_BEGIN_ENTRY_AT = None
    COMMAND_ALLOW_OVERRIDE_BEGIN_ENTRY_AT = True

    USERS_COLUMNS = 20
    #MAIN_WIDGET_CLASS = grid.SimpleGrid
    #MAIN_WIDGET_CLASS = editmultiline.MultiLineEdit
    def __init__(self, cycle_widgets = True, *args, **keywords):
        super(FormMutt, self).__init__(cycle_widgets=cycle_widgets, *args, **keywords)


    def draw_form(self):
        MAXY, MAXX = self.lines, self.columns #self.curses_pad.getmaxyx()
        self.curses_pad.hline(0, 0, curses.ACS_HLINE, MAXX-1)
        self.curses_pad.hline(MAXY-2-self.BLANK_LINES_BASE, 0, curses.ACS_HLINE, MAXX-1)

    def create(self):
        MAXY, MAXX    = self.lines, self.columns

        self.wStatus1 = self.add(self.__class__.STATUS_WIDGET_CLASS,  rely=0,
                                        relx=self.__class__.STATUS_WIDGET_X_OFFSET,
                                        editable=False,
                                        )

        self.wMain = self.add(self.__class__.MAIN_WIDGET_CLASS,
                                            rely=self.__class__.MAIN_WIDGET_CLASS_START_LINE,
                                            relx=0,     max_height = -2,
                                            max_width = self.columns - self.USERS_COLUMNS,
                                            autowrap=True
                                            )
        self.wStatus2 = self.add(npyscreen.Textfield,  rely=MAXY-2-self.BLANK_LINES_BASE,
                                        relx=self.__class__.STATUS_WIDGET_X_OFFSET,
                                        editable=False,
                                        )



        if not self.__class__.COMMAND_WIDGET_BEGIN_ENTRY_AT:
            self.wCommand = self.add(self.__class__.COMMAND_WIDGET_CLASS, name=self.__class__.COMMAND_WIDGET_NAME,
                                    rely = MAXY-1-self.BLANK_LINES_BASE, relx=0,)
        else:
            self.wCommand = self.add(
                self.__class__.COMMAND_WIDGET_CLASS, name=self.__class__.COMMAND_WIDGET_NAME,
                                    rely = MAXY-1-self.BLANK_LINES_BASE, relx=0,
                                    begin_entry_at = self.__class__.COMMAND_WIDGET_BEGIN_ENTRY_AT,
                                    allow_override_begin_entry_at = self.__class__.COMMAND_ALLOW_OVERRIDE_BEGIN_ENTRY_AT
                                    )

        self.users = self.add(npyscreen.wgmultiline.MultiLine,
               rely=self.__class__.MAIN_WIDGET_CLASS_START_LINE,
               relx=self.columns - self.USERS_COLUMNS,     max_height = -2,)


        self.wStatus1.important = True
        self.wStatus2.important = True
        self.nextrely = 2

    def h_display(self, input):
        super(FormMutt, self).h_display(input)
        if hasattr(self, 'wMain'):
            if not self.wMain.hidden:
                self.wMain.display()

    def resize(self):
        super(FormMutt, self).resize()
        MAXY, MAXX    = self.lines, self.columns
        self.wStatus2.rely = MAXY-2-self.BLANK_LINES_BASE
        self.wCommand.rely = MAXY-1-self.BLANK_LINES_BASE


class TestForm(FormMutt):
    #MAIN_WIDGET_CLASS = TestListClass
    pass

class User:
    def __init__(self, user, status):
        self.user = user
        self.status = status

    def __str__(self):
        return f"[{self.status}] {self.user}"

class TestApp(npyscreen.StandardApp):
    def __init__(self):
        super().__init__()
        self.opened_chats = ['MAIN']
        self.current_chat = 0

    def onStart(self):
        logging.info(threading.current_thread())

        F = self.addForm("MAIN", TestForm)
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
            form = self.addForm(name, TestForm)
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


if __name__ == "__main__":
    App = TestApp()
    App.run()
