#!/usr/bin/env python
import npyscreen
import curses
import logging
import os
import threading
import queue

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

class TestApp(npyscreen.StandardApp):
    def onStart(self):
        logging.info(threading.current_thread())

        self.addForm("MAIN", TestForm)
        F = self.getForm("MAIN")
        F.wStatus1.value = "Status Line "
        F.wStatus2.value = "Second Status Line "
        F.wMain.values   = []

        self.add_event_hander("new_message", self.ev_test_event_handler)
        self.add_event_hander("status", self.on_status)

        F.wCommand.add_handlers({curses.ascii.NL: self.entered})

    def entered(self, nop):
        F = self.getForm("MAIN")
        self.x.send(F.wCommand.value, 'all')
        F.wCommand.value = ""
        F.wMain.update()

    def on_status(self, evt):
        F = self.getForm("MAIN")
        F.users.values.append("[{status}] {user}".format(**evt.payload))
        F.users.display()

    def ev_test_event_handler(self, evt):
        F = self.getForm("MAIN")
        F.wMain.buffer(["{timestamp} {author}: {text}".format(**evt.payload)], True, True)
        F.wMain.update()
        F.wMain.display()

    def send(self, event, payload):
        self.queue_event(npyscreen.Event(event, payload))


if __name__ == "__main__":
    App = TestApp()
    App.run()
