#!/usr/bin/env python
# Initial basic test app for turning on and off various GPIO ports
#
# The following script can be used to test a specific GPIO pin.  Enter the pin address as defined
# in the gpio list to test the pin.  Not entering a pin number will go through each pin and activate it.  See
# arguments secion for specific argument details.
#
# Additional Modifications By: Chris Usey (chrisausey@gmail.com)
# - Adapted to use 8 gpio's of the PI and 16 additional gpio's provided by mcp23017 expander chip
# - Adapted to add --activelowmode argument for use with active low relays
# - Adapted to blink all leds if no --led argument is passed or blink specific leds of the led is specified

import time
import wiringpi2 as wiringpi
import argparse 

gpioList=[7,0,1,2,3,4,5,6,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80] # List of pins to use defined by 
pin_base = 65       # lowest available starting number is 65
i2c_addr = 0x20     # A0, A1, A2 pins all wired to GND
GPIOINPUT=0
GPIOOUTPUT=1
GPIOACTIVE=1        # Value to set when pin is to be turned on
GPIOINACTIVE=0      # Value to set when pin is to be turned off

wiringpi.wiringPiSetup() # Initialise PIN mode
wiringpi.mcp23017Setup(pin_base,i2c_addr)   # set up the pins and i2c address

parser = argparse.ArgumentParser()
parser.add_argument('--led', type=int, default=-1, help='led to flash (0-24)')
parser.add_argument('--sleep', type=float, default=.5, help='time to sleep between flash')
parser.add_argument('--activelowmode', type=bool, default=0, help='turn active low mode on and off')

args = parser.parse_args()

pin = args.led
sleep = args.sleep
activelowmode = args.activelowmode

if (activelowmode):
	GPIOACTIVE=0
	GPIOINACTIVE=1

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

