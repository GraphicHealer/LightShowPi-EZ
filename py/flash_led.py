#!/usr/bin/env python
# Initial basic test app for turning on and off various GPIO ports
#
# The following script can be used to test a specific GPIO pin.  Enter the pin address as defined
# in the gpio list to test the pin.  Not entering a pin number will go through each pin and activate it.  See
# arguments secion for specific argument details.
#
# Additional Modifications By: Chris Usey (chrisausey@gmail.com)

import time
import wiringpi2 as wiringpi
import argparse 
import ConfigParser
import ast

# get configurations
config = ConfigParser.RawConfigParser()
config.read('/home/pi/py/synchronized_lights.cfg')

gpioList = map(int,config.get('hardware','gpios_to_use').split(',')) # List of pins to use defined by 
activelowmode = config.getboolean('hardware','active_low_mode')
try:
	mcp23017 = ast.literal_eval(config.get('hardware','mcp23017'))
except:
	mcp23017 = 0

wiringpi.wiringPiSetup() # Initialise PIN mode

if (mcp23017):
	print "MCP23017 CONFIGURED"
	wiringpi.mcp23017Setup(mcp23017['pin_base'],mcp23017['i2c_addr'])   # set up the pins and i2c address
else:
	print "MCP2307 NOT CONFIGURED"

parser = argparse.ArgumentParser()
parser.add_argument('--led', type=int, default=-1, help='led to flash (0-24)')
parser.add_argument('--sleep', type=float, default=.5, help='time to sleep between flash')
args = parser.parse_args()

pin = args.led
sleep = args.sleep
GPIOINPUT=0
GPIOOUTPUT=1

if (activelowmode):
	GPIOACTIVE=0
	GPIOINACTIVE=1
else: 
	GPIOACTIVE=1        # Value to set when pin is to be turned on
	GPIOINACTIVE=0      # Value to set when pin is to be turned off

def cleanup():
	# loop through and clean up
	print "Cleaning Up Pins"
	for item in gpioList:
		wiringpi.digitalWrite(item,GPIOINPUT) # Set port to Input
		wiringpi.pinMode(item,GPIOINACTIVE) # Set pin to inactive
	print " "

def intitalizeAll():
	# loop through and clean up
	for item in gpioList:
		print "Initializing Pin: " + str(item)
		wiringpi.pinMode(item,GPIOOUTPUT)
		wiringpi.digitalWrite(item,GPIOINACTIVE) # Set pin to Inactive
		print " "

cleanup()
intitalizeAll()

# Blink the 
count = 0
if (pin == -1):
	print "Blink All pins " + str(count) + " of 5"
	for item in gpioList:
		print "Activating Pin: " + str(item)
		wiringpi.digitalWrite(item,GPIOACTIVE)
		time.sleep(sleep)
		print "Deactivating Pin: " + str(item)
		wiringpi.digitalWrite(item,GPIOINACTIVE)
		time.sleep(sleep)
else:
	while count < 5:
		print "Blink pin " + str(pin) + ": " + str(count) + " of 5"
		print "Activating Pin: " + str(pin)
		wiringpi.digitalWrite(gpioList[pin],GPIOACTIVE)
		time.sleep(sleep)
		print "Deactivating Pin: " + str(pin)
		wiringpi.digitalWrite(gpioList[pin],GPIOINACTIVE)
		time.sleep(sleep)
		count+=1

cleanup()

