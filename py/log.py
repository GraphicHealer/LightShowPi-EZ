#!/usr/bin/env python

"""Provide simple logging support for scripts"""

import time

verbosity = 1

def log(msg, verbose_level=1, show_time=True):
  """Log a message to stdout""" 
  global verbosity
  if verbosity >= verbose_level:
    if show_time:
      timestr = time.strftime("%b %d %Y %H:%M:%S", time.localtime())
      print "[" + timestr + "] " + msg
    else:
      print msg

