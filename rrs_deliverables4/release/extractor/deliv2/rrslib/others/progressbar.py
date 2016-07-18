#!/usr/bin/env python
# -*- coding: utf-8 -*-


import curses
import time
import sys

# The current module
MODULE = sys.modules[__name__]

COLORS = "BLUE GREEN CYAN RED MAGENTA YELLOW WHITE BLACK".split()
# List of terminal controls, you can add more to the list.
CONTROLS = {
    'BOL':'cr', 'UP':'cuu1', 'DOWN':'cud1', 'LEFT':'cub1', 'RIGHT':'cuf1',
    'CLEAR_SCREEN':'clear', 'CLEAR_EOL':'el', 'CLEAR_BOL':'el1',
    'CLEAR_EOS':'ed', 'BOLD':'bold', 'BLINK':'blink', 'DIM':'dim',
    'REVERSE':'rev', 'UNDERLINE':'smul', 'NORMAL':'sgr0',
    'HIDE_CURSOR':'cinvis', 'SHOW_CURSOR':'cnorm'
}

# List of numeric capabilities
VALUES = {
    'COLUMNS':'cols', # Width of the terminal (None for unknown)
    'LINES':'lines',  # Height of the terminal (None for unknown)
    'MAX_COLORS': 'colors',
}

def setup():
    """Set the terminal control strings"""
    # Initializing the terminal
    curses.setupterm()
    # Get the color escape sequence template or '' if not supported
    # setab and setaf are for ANSI escape sequences
    bgColorSeq = curses.tigetstr('setab') or curses.tigetstr('setb') or ''
    fgColorSeq = curses.tigetstr('setaf') or curses.tigetstr('setf') or ''

    for color in COLORS:
        # Get the color index from curses
        colorIndex = getattr(curses, 'COLOR_%s' % color)
        # Set the color escape sequence after filling the template with index
        setattr(MODULE, color, curses.tparm(fgColorSeq, colorIndex))
        # Set background escape sequence
        setattr(
            MODULE, 'BG_%s' % color, curses.tparm(bgColorSeq, colorIndex)
        )
    for control in CONTROLS:
        # Set the control escape sequence
        setattr(MODULE, control, curses.tigetstr(CONTROLS[control]) or '')
    for value in VALUES:
        # Set terminal related values
        setattr(MODULE, value, curses.tigetnum(VALUES[value]))


def render(text):
    """Helper function to apply controls easily
    Example:
    apply("%(GREEN)s%(BOLD)stext%(NORMAL)s") -> a bold green text
    """
    return text % MODULE.__dict__

import curses
setup()


class ProgressBar(object):
    """Terminal progress bar class"""
    TEMPLATE = (
     '%(percent)-2s%% %(color)s%(progress)s%(normal)s%(empty)s %(message)s\n'
    )
    PADDING = 7

    def __init__(self, color=None, width=None, block='█', empty=' '):
        """
        color -- color name (BLUE GREEN CYAN RED MAGENTA YELLOW WHITE BLACK)
        width -- bar width (optinal)
        block -- progress display character (default '█')
        empty -- bar display character (default ' ')
        """
        if color:
            self.color = ''
        else:
            self.color = ''
        if width and width < COLUMNS - self.PADDING:
            self.width = width
        else:
            # Adjust to the width of the terminal
            self.width = COLUMNS - self.PADDING
        self.block = block
        self.empty = empty
        self.progress = None
        self.lines = 0

    def render(self, percent, message = ''):
        """Print the progress bar
        percent -- the progress percentage %
        message -- message string (optional)
        """
        inline_msg_len = 0
        if message:
            # The length of the first line in the message
            inline_msg_len = len(message.splitlines()[0])
        if inline_msg_len + self.width + self.PADDING > COLUMNS:
            # The message is too long to fit in one line.
            # Adjust the bar width to fit.
            bar_width = COLUMNS - inline_msg_len -self.PADDING
        else:
            bar_width = self.width

        # Check if render is called for the first time
        if self.progress != None:
            self.clear()
        self.progress = (bar_width * percent) / 100
        data = self.TEMPLATE % {
            'percent': percent,
            'color': self.color,
            'progress': self.block * self.progress,
            'normal': NORMAL,
            'empty': self.empty * (bar_width - self.progress),
            'message': message
        }
        sys.stdout.write(data)
        sys.stdout.flush()
        # The number of lines printed
        self.lines = len(data.splitlines())

    def clear(self):
        """Clear all printed lines"""
        sys.stdout.write(
            self.lines * (UP + BOL + CLEAR_EOL)
        )

if __name__ == '__main__':
    p = ProgressBar('green', width=20, block='▣', empty='□')
    for i in range(101):
        p.render(i, 'step %s\nProcessing...\nDescription: write something.' % i)
        time.sleep(0.1)
