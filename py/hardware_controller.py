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
import configuration_manager as cm

# Get Configurations - TODO(toddgiles): Move more of this into configuration manager
config = cm.config
gpio = map(int,config.get('hardware','gpio_pins').split(',')) # List of pins to use defined by 
activelowmode = config.getboolean('hardware','active_low_mode')
alwaysonchannels = map(int,config.get('lightshow','always_on_channels').split(','))
alwaysoffchannels = map(int,config.get('lightshow','always_off_channels').split(','))
invertedchannels = map(int,config.get('lightshow','invert_channels').split(','))
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

def TurnOffLights(usealwaysonoff = 0):
    for i in range(GPIOLEN):
        if usealwaysonoff:
            if i+1 not in alwaysonchannels:
                wiringpi.digitalWrite(gpio[i], GPIOINACTIVE)
        else:
            wiringpi.digitalWrite(gpio[i], GPIOINACTIVE)

def TurnOnLights(usealwaysonoff = 0):
    for i in range(GPIOLEN):
        if usealwaysonoff:
            if i+1 not in alwaysoffchannels:
                wiringpi.digitalWrite(gpio[i], GPIOACTIVE)
        else:
            wiringpi.digitalWrite(gpio[i], GPIOACTIVE)

def TurnOffLight(i, useoverrides = 0):
    if useoverrides:
        if i+1 not in alwaysonchannels:
            if i+1 not in invertedchannels:
                wiringpi.digitalWrite(gpio[i], GPIOINACTIVE)
            else:
                wiringpi.digitalWrite(gpio[i], GPIOACTIVE)
    else:
        wiringpi.digitalWrite(gpio[i], GPIOINACTIVE)

def TurnOnLight(i, useoverrides = 0):
    if useoverrides:
        if i+1 not in alwaysoffchannels:
            if i+1 not in invertedchannels:
                wiringpi.digitalWrite(gpio[i], GPIOACTIVE)
            else:
                wiringpi.digitalWrite(gpio[i], GPIOINACTIVE)    
    else:
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
    parser.add_argument('--init', action='store_true', default=False, help='initialize hardware pins before running other commands') 
    parser.add_argument('--state', choices=["off", "on", "flash", "cleanup"], help='turn off, on, flash, or cleanup')
    parser.add_argument('--light', default='-1', help='the lights to act on (comma delimited list), -1 for all lights')
    parser.add_argument('--sleep', default=0.1, help='how long to sleep between flashes')
    parser.add_argument('--flashes', default=2, help='the number of times to flash each light')
    args = parser.parse_args()
    state = args.state
    sleep = float(args.sleep)
    flashes = int(args.flashes)

    lights = map(int, args.light.split(','))
    if -1 in lights:
        lights = range(0, len(gpio))

    print lights
    print gpio

    if args.init:
        Initialize()

    if state=="cleanup":
        CleanUp()
    elif state=="off":
        for light in lights:
            TurnOffLight(light)
    elif state=="on":
        for light in lights:
            TurnOnLight(light)
    elif state=="flash":
        while True:
            try:
                for light in lights:
                    print "channel %s " % light
                    for _ in range(flashes):
                        TurnOnLight(light)
                        time.sleep(sleep)
                        TurnOffLight(light)
                        time.sleep(sleep)
            except KeyboardInterrupt:
                print "\nstopped"
                for light in lights:
                    TurnOffLight(light)
                break
            break
    else:
        parser.print_help()
