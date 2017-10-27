#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Anthony Tod (big.red.frog@gmail.com)

"""Curses based renderer for bright values

# Handle curses related init and then dynamically render columns of channel brightness 
# values.
# This allows you to shake out the audio to brightness pipeline without having to hang
# your hardware off the pi.
# Launch synchonized_lights.py with the same command line as you normally would, and the
# active terminal will be used to render.
#
# To use, in your overrides.cfg which inherits from defaults.cfg
# In the [terminal] section, set
# enabled = True
#
# https://docs.python.org/2/howto/curses.html
# https://en.wikipedia.org/wiki/Curses_(programming_library)
"""

import curses
from timeit import default_timer as timer


class BrightCurses(object):
    """Curses based renderer for bright values
    # Handle curses related init and then dynamically render columns of channel brightness
    # values.
    # This allows you to shake out the audio to brightness pipeline without having to hang
    # your hardware off the pi.
    # Launch synchonized_lights.py with the same command line as you normally would, and the
    # active terminal will be used to render.
    #
    # To use, in your overrides.cfg which inherits from defaults.cfg
    # In the [terminal] section, set
    # enabled = True
    #
    # https://docs.python.org/2/howto/curses.html
    # https://en.wikipedia.org/wiki/Curses_(programming_library)
    """

    def __init__(self, terminal):
        self.config = terminal
        self.last_time = None
        self.stdscr = None

    def init(self, stdscr):
        """Cache the screen reference, clear the screen and display waiting notice

        :param stdscr: window object representing the entire screen
        :type stdscr: curses window object
        """
        self.stdscr = stdscr
        curses.start_color()
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        self.stdscr.clear()
        w_height, w_width = self.stdscr.getmaxyx()
        self.stdscr.addstr("Waiting for preShow"[:w_width - 1])
        self.stdscr.refresh()
        self.last_time = timer()

    def curses_render(self, brightness):
        """Main render code

        :param brightness: row of processed fft data
        :type brightness: list
        """
        index = 0
        self.stdscr.clear()
        w_height, w_width = self.stdscr.getmaxyx()
        max_val = w_height - 3
        c_width = min(6, int((w_width - 1) / len(brightness)))

        # if things are getting really tight remove the gap between columns
        # if we get down to zero width columns then give up
        if c_width < 3:
            gap = 0
        else:
            c_width -= 1
            gap = 1

        # Build the format string for the value display and the column body
        format_bright = "{:0" + str(c_width) + "d}"
        block_str = "X" * c_width

        # Calculate and display interframe ms and frames per second
        now_time = timer()
        frame_time = int((now_time - self.last_time) * 1000)
        diag = "T:" + "{:3d}".format(frame_time) + "ms FPS:" + "{:3d}".format(1000 / frame_time)
        self.stdscr.addstr(0, 0, diag[:w_width - 1])
        self.last_time = now_time

        # render each channel column
        for bright in brightness:
            disp_bright = format_bright.format(int(min(0.999999, bright) * (10 ** c_width)))
            bright_height = int(bright * max_val)

            # render each column row
            for y in range(bright_height):
                # there is a rounding / aliasing issue with deciding if we are above the threshold
                # but this should be good enough
                if y > (max_val / 2) - 1:
                    c_pair = 1
                else:
                    c_pair = 0
                self.stdscr.addstr(max_val - y, index * (c_width + gap),
                                   block_str,
                                   curses.color_pair(c_pair))
            self.stdscr.addstr(w_height - 1, index * (c_width + gap), disp_bright)
            index += 1
        self.stdscr.refresh()
