#!/usr/bin/env python
#
# Author: Todd Giles (todd.giles@gmail.com)
#
# Feel free to use, but do send any improvements back to me - thanks!


"""Provide simple logging support for scripts"""

import time

verbosity = 1

def log(msg, verbose_level=1, show_time=True):
  """Log a message to stdout""" 
  global verbosity
  if verbosity >= verbose_level:
    if show_time:
      timestr = time.strftime("%b %d %Y %H:%M:%S", time.localtime())
      print "[" + timestr + "] " + str(msg)
    else:
      print msg

