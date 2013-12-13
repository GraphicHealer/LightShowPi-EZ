#!/usr/bin/env python
#
# Author: Ryan Jennings & Chris Usey
# Based on work from Todd Giles (todd.giles@gmail.com)


import os
import sys
import time
import wiringpi2 as wiringpi
import time
import argparse
import ConfigParser
import ast
import log as l

# Get Configurations
home_directory = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
config = ConfigParser.RawConfigParser()
config.read(home_directory + '/py/synchronized_lights.cfg')
gpio = map(int,config.get('hardware','gpios_to_use').split(',')) # List of pins to use defined by 
alwaysonchannels = map(int,config.get('light_show_settings','always_on_channels').split(','))
alwaysoffchannels = map(int,config.get('light_show_settings','always_off_channels').split(','))
activelowmode = config.getboolean('hardware','active_low_mode')
try:
  mcp23017 = ast.literal_eval(config.get('hardware','mcp23017'))
except:
  mcp23017 = 0



# Initialize GPIO
GPIOASINPUT = 0
GPIOASOUTPUT = 1
GPIOLEN = len(gpio)
wiringpi.wiringPiSetup()



# Activate Port Expander If Defined
if (mcp23017):
  l.log("Initializing MCP23017 Port Expander", 2)
  wiringpi.mcp23017Setup(mcp23017['pin_base'],mcp23017['i2c_addr'])   # set up the pins and i2c address



# Check ActiveLowMode Configuration Setting
if (activelowmode):
    # Enabled
    GPIOACTIVE=0
    GPIOINACTIVE=1
else:
    # Disabled
    GPIOACTIVE=1
    GPIOINACTIVE=0



# Functions
def SetPinsAsOutputs():
    for i in range(GPIOLEN):
        SetPinAsOutput(i)

def SetPinsAsInputs():
    for i in range(GPIOLEN):
        SetPinAsInput(i)

def SetPinAsOutput(i):
    wiringpi.pinMode(gpio[i], GPIOASOUTPUT)

def SetPinAsInput(i):
    wiringpi.pinMode(gpio[i], GPIOASINPUT)

def TurnOffLights():
    for i in range(GPIOLEN):
      if i+1 not in alwaysonchannels:
        TurnOffLight(i)

def TurnOnLights():
    for i in range(GPIOLEN):
      if i+1 not in alwaysoffchannels:
        TurnOnLight(i)

def TurnOffLight(i):
    if i+1 not in alwaysonchannels:
        wiringpi.digitalWrite(gpio[i], GPIOINACTIVE)

def TurnOnLight(i):
    if i+1 not in alwaysoffchannels:
        wiringpi.digitalWrite(gpio[i], GPIOACTIVE)
def CleanUp():
    TurnOffLights()
    SetPinsAsInputs()

def Initialize():
    SetPinsAsOutputs()
    TurnOffLights()

#__________________Main________________
if __name__=="__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--state', choices=["off", "on", "flash", "cleanup", "initialize"], help='turn off, on, flash, cleanup, or initialize')
    args = parser.parse_args()
    state = args.state

    if state=="cleanup":
        CleanUp()
    elif state=="initialize":
        Initialize()
    elif state=="off":
        TurnOffLights()
    elif state=="on":
        TurnOnLights()
    elif state=="flash":
        while True:
            try:
                TurnOnLights()
                for i in range(0,len(gpio)):
                    print "channel %s " % i
                    TurnOffLight(i)
                    time.sleep(.1)
                    TurnOnLight(i)
                    time.sleep(.1)
                    TurnOffLight(i)
                    time.sleep(.1)
                    TurnOnLight(i)
                    time.sleep(.01)
            except KeyboardInterrupt:
                print "\nstopped"
                TurnOffLights()
                break
            break
    else:
        print "invalid state, use on, off, or flash"
