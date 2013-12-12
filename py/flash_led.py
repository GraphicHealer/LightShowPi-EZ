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
import os
import hardware_controller as hc

# Configurations
home_directory = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
config = ConfigParser.RawConfigParser()
config.read(home_directory + '/py/synchronized_lights.cfg')

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--led', type=int, default=-1, help='led to flash (0-24)')
parser.add_argument('--sleep', type=float, default=.5, help='time to sleep between flash')
args = parser.parse_args()

pin = args.led
sleep = args.sleep

# Cleanup Pins
hc.TurnOffLights()
hc.SetPinsAsInputs()

# Initialize all pins
hc.SetPinsAsOutputs()
hc.TurnOffLights()

# Blink the LED's
count = 0
if (pin == -1):
	print "Blink All pins " + str(count) + " of 5"
	for item in hc.gpio:
		print "Activating Pin: " + str(item)
		#wiringpi.digitalWrite(item,GPIOACTIVE)
		hc.TurnOnLight(item)
		time.sleep(sleep)
		print "Deactivating Pin: " + str(item)
		#wiringpi.digitalWrite(item,GPIOINACTIVE)
		hc.TurnOffLight(item)
		time.sleep(sleep)
else:
	while count < 5:
		print "Blink pin " + str(pin) + ": " + str(count) + " of 5"
		print "Activating Pin: " + str(pin)
		#wiringpi.digitalWrite(gpioList[pin],GPIOACTIVE)
		hc.TurnOnLight(hc.gpio[pin])
		time.sleep(sleep)
		print "Deactivating Pin: " + str(pin)
		#wiringpi.digitalWrite(gpioList[pin],GPIOINACTIVE)
		hc.TurnOffLight(hc.gpio[pin])
		time.sleep(sleep)
		count+=1

# Cleanup Pins
hc.TurnOffLights()
hc.SetPinsAsInputs()

