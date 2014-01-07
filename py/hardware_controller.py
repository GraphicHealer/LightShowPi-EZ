#!/usr/bin/env python
#
# Author: Ryan Jennings
# Author: Chris Usey
#
# Based on original work from Todd Giles (todd.giles@gmail.com)
"""Control the raspberry pi hardware.

The hardware controller handles all interaction with the raspberry pi hardware to turn the lights
on and off.

Third party dependencies:

wiringpi2: python wrapper around wiring pi - https://github.com/WiringPi/WiringPi2-Python
"""

import argparse
import ast
import logging
import time

import configuration_manager as cm
import wiringpi2 as wiringpi


# Get Configurations - TODO(toddgiles): Move more of this into configuration manager
_CONFIG = cm.CONFIG
_GPIO_PINS = [int(pin) for pin in _CONFIG.get('hardware', 'gpio_pins').split(',')]
PIN_MODES = _CONFIG.get('hardware', 'pin_modes').split(',')
_ACTIVE_LOW_MODE = _CONFIG.getboolean('hardware', 'active_low_mode')
_LIGHTSHOW_CONFIG = cm.lightshow()
_ALWAYS_ON_CHANNELS = [int(channel) for channel in
                       _LIGHTSHOW_CONFIG['always_on_channels'].split(',')]
_ALWAYS_OFF_CHANNELS = [int(channel) for channel in
                        _LIGHTSHOW_CONFIG['always_off_channels'].split(',')]
_INVERTED_CHANNELS = [int(channel) for channel in
                      _LIGHTSHOW_CONFIG['invert_channels'].split(',')]
try:
    _MCP23017 = ast.literal_eval(_CONFIG.get('hardware', 'mcp23017'))
except:
    _MCP23017 = 0

# Initialize GPIO
GPIOASINPUT = 0
GPIOASOUTPUT = 1
GPIOLEN = len(_GPIO_PINS)
wiringpi.wiringPiSetup()

# If only a single pin mode is specified, assume all pins should be in that mode
if len(PIN_MODES) == 1:
    PIN_MODES = [PIN_MODES[0] for _ in range(GPIOLEN)]

# Activate Port Expander If Defined
if _MCP23017:
    logging.info("Initializing MCP23017 Port Expander")
    # set up the pins and i2c address
    wiringpi.mcp23017Setup(_MCP23017['pin_base'], _MCP23017['i2c_addr'])

# Check ActiveLowMode Configuration Setting
if _ACTIVE_LOW_MODE:
    # Enabled
    GPIOACTIVE = 0
    GPIOINACTIVE = 1
else:
    # Disabled
    GPIOACTIVE = 1
    GPIOINACTIVE = 0


# Functions
def is_pin_pwm(i):
    return PIN_MODES[i].lower() == "pwm"

def set_pins_as_outputs():
    '''Set all the configured pins as outputs.'''
    for i in range(GPIOLEN):
        set_pin_as_output(i)

def set_pins_as_inputs():
    '''Set all the configured pins as inputs.'''
    for i in range(GPIOLEN):
        set_pin_as_input(i)

def set_pin_as_output(i):
    '''Set the specified pin as an output.'''
    wiringpi.pinMode(_GPIO_PINS[i], GPIOASOUTPUT)
    if is_pin_pwm(i):
        wiringpi.softPwmCreate(i, 0, 100)

def set_pin_as_input(i):
    '''Set the specified pin as an input.'''
    wiringpi.pinMode(_GPIO_PINS[i], GPIOASINPUT)

def turn_off_lights(usealwaysonoff=0):
    '''Turn off all the lights, but leave on all lights designated to be always on if specified.'''
    for i in range(GPIOLEN):
        if usealwaysonoff:
            if i + 1 not in _ALWAYS_ON_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[i], GPIOINACTIVE)
        else:
            wiringpi.digitalWrite(_GPIO_PINS[i], GPIOINACTIVE)

def turn_on_lights(usealwaysonoff=0):
    '''Turn on all the lights, but leave off all lights designated to be always off if specified.'''
    for i in range(GPIOLEN):
        if usealwaysonoff:
            if i + 1 not in _ALWAYS_OFF_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[i], GPIOACTIVE)
        else:
            wiringpi.digitalWrite(_GPIO_PINS[i], GPIOACTIVE)

def turn_off_light(i, useoverrides=0):
    '''Turn off the specified light, taking into account various overrides if specified.'''
    if is_pin_pwm(i):
        # No overrides avaialble for pwm mode pins
        wiringpi.softPwmWrite(i, 0)
        return

    if useoverrides:
        if i + 1 not in _ALWAYS_ON_CHANNELS:
            if i + 1 not in _INVERTED_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[i], GPIOINACTIVE)
            else:
                wiringpi.digitalWrite(_GPIO_PINS[i], GPIOACTIVE)
    else:
        wiringpi.digitalWrite(_GPIO_PINS[i], GPIOINACTIVE)

def turn_on_light(i, useoverrides=0, brightness=100):
    '''Turn on the specified light, taking into account various overrides if specified.'''
    if is_pin_pwm(i):
        # No overrides avaialble for pwm mode pins
        wiringpi.softPwmWrite(i, brightness)
        return

    if useoverrides:
        if i + 1 not in _ALWAYS_OFF_CHANNELS:
            if i + 1 not in _INVERTED_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[i], GPIOACTIVE)
            else:
                wiringpi.digitalWrite(_GPIO_PINS[i], GPIOINACTIVE)
    else:
        wiringpi.digitalWrite(_GPIO_PINS[i], GPIOACTIVE)

def clean_up():
    '''Turn off all lights, and set the pins as inputs.'''
    turn_off_lights()
    set_pins_as_inputs()

def initialize():
    '''Set pins as outputs, and start all lights in the off state.'''
    set_pins_as_outputs()
    turn_off_lights()


# __________________Main________________
def main():
    '''main'''

    parser = argparse.ArgumentParser()
    parser.add_argument('--init', action='store_true', default=False,
                        help='initialize hardware pins before running other commands')
    parser.add_argument('--state', choices=["off", "on", "flash", "fade", "cleanup"],
                        help='turn off, on, flash, or cleanup')
    parser.add_argument('--light', default='-1',
                        help='the lights to act on (comma delimited list), -1 for all lights')
    parser.add_argument('--sleep', default=0.5,
                        help='how long to sleep between flashing or fading a light')
    parser.add_argument('--flashes', default=2,
                        help='the number of times to flash or fade each light')
    args = parser.parse_args()
    state = args.state
    sleep = float(args.sleep)
    flashes = int(args.flashes)

    lights = [int(light) for light in args.light.split(',')]
    if -1 in lights:
        lights = range(0, len(_GPIO_PINS))

    if args.init:
        initialize()

    if state == "cleanup":
        clean_up()
    elif state == "off":
        for light in lights:
            turn_off_light(light)
    elif state == "on":
        for light in lights:
            turn_on_light(light)
    elif state == "fade":
        # Test fading in and out for each light configured in pwm mode
        while True:
            try:
                for light in lights:
                    if is_pin_pwm(light):
                        for _ in range(flashes):
                            for brightness in range(0, 101, 10):
                                # fade in
                                turn_on_light(light, 0, brightness)
                                time.sleep(sleep / 11)
                            for brightness in range(100, -1, -10):
                                # fade out
                                turn_on_light(light, 0, brightness)
                                time.sleep(sleep / 11)
            except KeyboardInterrupt:
                print "\nstopped"
                for light in lights:
                    turn_off_light(light)
                break
    elif state == "flash":
        while True:
            try:
                for light in lights:
                    print "channel %s " % light
                    for _ in range(flashes):
                        turn_on_light(light)
                        time.sleep(sleep)
                        turn_off_light(light)
                        time.sleep(sleep)
            except KeyboardInterrupt:
                print "\nstopped"
                for light in lights:
                    turn_off_light(light)
                break
            break
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
