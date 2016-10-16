#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Anthony Tod (big.red.frog@gmail.com)

"""Curses based renderer for bright values

# Handle curses related init and then dynamically render columns of channel brightness 
# values.
# This allows you to shake out the audio to brightness pipeline without having to hang
# your hardware off the pi.
# Launch synchonized_lights.py with the same command line as you normally would, and the
# active terminal will be used to render.

"""

import curses
from timeit import default_timer as timer

class BrightCurses(object):
    """Curses based renderer for bright values
    """

    def __init__(self, terminal ):
        self.config = terminal

    def init( self, stdscr ):
        """cache the screen reference, clear the screen and display waiting notice"""
	self.stdscr = stdscr
    	curses.start_color()
	curses.curs_set(0)
    	curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
	self.stdscr.clear()
	wHeight,wWidth = self.stdscr.getmaxyx()
	self.stdscr.addstr("Waiting for preShow"[:wWidth-1] )
        self.stdscr.refresh()
	self.lastTime = timer()

    def cursesRender( self, brightness ):
        """Main render code"""
        index = 0
        self.stdscr.clear()
        wHeight,wWidth = self.stdscr.getmaxyx()
        maxVal = wHeight - 3
        cWidth = min ( 6, int ( ( wWidth - 1 ) / len(brightness)))
        #if things are getting really tight remove the gap between columns
        #if we get down to zero width columns then give up
        if ( cWidth < 3 ):
            gap = 0
        else:
            cWidth -= 1
            gap = 1
        #Build the format string for the value display and the column body
        formatBright = "{:0" + str(cWidth) + "d}"
        blockStr = "X" * cWidth

        #Calculate and display interframe ms and frames per second
	nowTime = timer()
	frametime = int((nowTime-self.lastTime) * 1000)
	diag = "T:" + str( frametime ) + "ms FPS:" + str( 1000 / frametime ) 
        self.stdscr.addstr( 0, 0, diag[:wWidth-1] )
	self.lastTime = nowTime
   
        #render each channel column
        for bright in brightness:
            dispBright = formatBright.format( int( min( 0.999999, bright ) * ( 10 ** cWidth )))
            brightHeight = int ( bright * maxVal )
            #render each column row
            for y in range(brightHeight):
                #there is a rounding / aliasing issue with deciding if we are above the threshold
                #but this should be good enough
		if ( y > ( maxVal / 2 ) - 1 ):
                    cPair = 1
                else:
                    cPair = 0
                self.stdscr.addstr( maxVal - y, index * ( cWidth + gap ), blockStr, curses.color_pair(cPair)  )
            self.stdscr.addstr( wHeight-1, index * ( cWidth + gap ), dispBright )
            index+=1
        self.stdscr.refresh()
	
