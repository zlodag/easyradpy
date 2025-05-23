import os
import platform
import sys
from time import sleep

from ahk import AHK

from ..autotriage import AutoTriageError, Request, Priority, Examination, BodyPart
from ..database import Database

class MyAHK:

    DEFAULT_RANK = 3 # todo make this configurable, None if setting rank is disabled
    database = Database()
    def __init__(self, block_forever=False):
        executable_path = os.path.join(
            getattr(sys, "_MEIPASS", os.path.dirname(os.path.realpath(sys.executable))),
            "AutoHotkey.exe",
        ) if getattr(sys, 'frozen', False) else ''
        self.ahk = AHK(executable_path=executable_path, version='v2')
        self.ahk.set_send_mode('Event')
        self.ahk.add_hotkey('^+m', self.show_message)
        self.ahk.add_hotkey('Numpad0', self.triage, self.autotriage_error_handler)  # skips rank entry
        self.ahk.add_hotkey('Numpad1', lambda: self.triage(1), self.autotriage_error_handler)
        self.ahk.add_hotkey('Numpad2', lambda: self.triage(2), self.autotriage_error_handler)
        self.ahk.add_hotkey('Numpad3', lambda: self.triage(3), self.autotriage_error_handler)
        self.ahk.add_hotkey('Numpad4', lambda: self.triage(4), self.autotriage_error_handler)
        self.ahk.add_hotkey('Numpad5', lambda: self.triage(5), self.autotriage_error_handler)
        self.ahk.add_hotkey('MButton', lambda: self.triage(self.DEFAULT_RANK), self.autotriage_error_handler)
        self.ahk.start_hotkeys()  # start the hotkey process thread
        print('Created AHK instance')
        if block_forever:
            self.ahk.block_forever()

    def show_message(self):
        # Show a message box directly using AHK
        self.ahk.msg_box(f'Python version {platform.python_version()}\nAHK version {self.ahk.get_version()}')

    def autotriage_error_handler(self, _: str, e: Exception):
        self.ahk.show_error_traytip(e.__class__.__name__, e.message if isinstance(e, AutoTriageError) else str(e))

    def triage(self, rank: int | None = None):
        print(f'Begin triage with rank: {rank}')
        self.ahk.send('!c') # Close any AMR popup with Alt+C
        self.ahk.send('{F6}{Tab}') # Focus on the tree
        restore_clipboard = self.ahk.get_clipboard()
        self.ahk.set_clipboard('')
        self.ahk.send('^c') # copy to clipboard
        try:
            self.ahk.clip_wait(0.1)
            clipboard = self.ahk.get_clipboard()
        except TimeoutError: # maybe the focus was originally on the pdf viewer, try again
            self.ahk.send('{F6}{Tab}^c')
            try:
                self.ahk.clip_wait(0.1)
                clipboard = self.ahk.get_clipboard()
            except TimeoutError:
                raise AutoTriageError('No request found')
        finally:
            self.ahk.set_clipboard(restore_clipboard)
        request = Request(clipboard)
        # self.ahk.show_traytip('Success', f'{request.modality.name} - {request.exam}')
        self.ahk.send('{Tab}') # Tab to "Radiology Category"
        match request.priority:
            case Priority.UNKNOWN: self.ahk.show_info_traytip('No clinical category', '')
            case Priority.STAT: self.ahk.send('{Home}S')
            case Priority.HOURS_4: self.ahk.send('{Home}4')
            case Priority.HOURS_24: self.ahk.send('{Home}2')
            case Priority.DAYS_2: self.ahk.send('{Home}22')
            case Priority.WEEKS_2: self.ahk.send('{Home}222')
            case Priority.WEEKS_4: self.ahk.send('{Home}44')
            case Priority.WEEKS_6: self.ahk.send('{Home}6')
            case Priority.PLANNED: self.ahk.send('{Home}P')
        self.ahk.send('{Tab 7}') # Tab to "Rank"
        if rank is not None:
            self.ahk.send(f'^a{rank}') # select all, enter rank
        self.ahk.send('{Tab 2}') # Tab to "Body Part"
        exam = self.database.get_examination(request)
        match exam.body_part:
            case BodyPart.CHEST: self.ahk.send('{Home}C')
            case BodyPart.CHEST_ABDO: self.ahk.send('{Home}CC')
            case body_part:
                self.ahk.send(body_part[:2 if body_part[0] in ('A','N','O','S') else 1])
        self.ahk.send(
            '{Tab 7}' # Tab to table (need 7 rather than 6 if CONT_SENST is showing)
            + '{Home}{Tab}' # Navigate to "Code" cell
            + exam.code # Enter code
            + '{Tab}' # Tab out of cell
        )










