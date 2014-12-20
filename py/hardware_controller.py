#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Ryan Jennings
# Author: Chris Usey
# Author: Todd Giles (todd@lightshowpi.com)
"""
Control the raspberry pi hardware.

The hardware controller handles all interaction with the raspberry pi hardware to turn the lights
on and off.

Third party dependencies:

wiringpi2: python wrapper around wiring pi - https://github.com/WiringPi/WiringPi2-Python
"""

import argparse
import logging
import time
import subprocess

import configuration_manager as cm
import wiringpi2 as wiringpi


# Get Configurations - TODO(todd): Move more of this into configuration manager
_CONFIG = cm.CONFIG
_GPIO_PINS = [int(pin) for pin in _CONFIG.get('hardware', 'gpio_pins').split(',')]
PIN_MODES = _CONFIG.get('hardware', 'pin_modes').split(',')
_PWM_MAX = int(_CONFIG.get('hardware', 'pwm_range'))
_ACTIVE_LOW_MODE = _CONFIG.getboolean('hardware', 'active_low_mode')
_LIGHTSHOW_CONFIG = cm.lightshow()
_HARDWARE_CONFIG = cm.hardware()
_ALWAYS_ON_CHANNELS = [int(channel) for channel in
                       _LIGHTSHOW_CONFIG['always_on_channels'].split(',')]
_ALWAYS_OFF_CHANNELS = [int(channel) for channel in
                        _LIGHTSHOW_CONFIG['always_off_channels'].split(',')]
_INVERTED_CHANNELS = [int(channel) for channel in
                      _LIGHTSHOW_CONFIG['invert_channels'].split(',')]

_EXPORT_PINS = _CONFIG.getboolean('hardware', 'export_pins')

# Initialize GPIO
_GPIOASINPUT = 0
_GPIOASOUTPUT = 1
GPIOLEN = len(_GPIO_PINS)

if not _EXPORT_PINS:
    wiringpi.wiringPiSetup()
else:
    wiringpi.wiringPiSetupSys()
    logging.info("Running as non root user, disabling pwm mode on all pin")
    PIN_MODES = ["onoff" for _ in range(GPIOLEN)]
    _GPIO_UTILITY_PATH = _CONFIG.get('hardware', 'gpio_utility_path')

# If only a single pin mode is specified
# assume all pins should be in that mode
if len(PIN_MODES) == 1:
    PIN_MODES = [PIN_MODES[0] for _ in range(GPIOLEN)]

# If always on or off you can not use PWM.
# If the channels are always on or off then there is no 
# need for them to be in pwm mode, disabling pwm mode for onoff channels.
if _ALWAYS_ON_CHANNELS != [-1]:
    for channel in _ALWAYS_ON_CHANNELS:
        PIN_MODES[channel - 1] = 'onoff'

if _ALWAYS_OFF_CHANNELS != [-1]:
    for channel in _ALWAYS_OFF_CHANNELS:
        PIN_MODES[channel - 1] = 'onoff'

# ActiveLowMode Configuration Setting
_GPIOACTIVE = int(not _ACTIVE_LOW_MODE)
_PWM_ON = _PWM_MAX * int(not _ACTIVE_LOW_MODE)
_GPIOINACTIVE = int(_ACTIVE_LOW_MODE)
_PWM_OFF = _PWM_MAX * int(_ACTIVE_LOW_MODE)

# Functions
def enable_device():
    """enable the specified device """
    try:
        devices = _HARDWARE_CONFIG['devices']

        for key in devices.keys():
            device = key
            device_slaves = devices[key]
            
            # mcp23017
            if device.lower() == "mcp23017":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23017Setup(int(params['pinBase']),
                                           int(params['i2cAddress'],16))
            
            # mcp23s17
            elif device.lower() == "mcp23s17":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23s17Setup(int(params['pinBase']),
                                           int(params['spiPort'],16),
                                           int(params['devId']))
            
            # TODO: Devices below need testing, these should work but 
            # could not verify due to lack of hardware
            
            # mcp23016
            elif device.lower() == "mcp23016":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23016Setup(int(params['pinBase']),
                                           int(params['i2cAddress'],16))

            # mcp23s08 - Needs Testing
            elif device.lower() == "mcp23008":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23008Setup(int(params['pinBase']),
                                           int(params['i2cAddress'],16))

            # mcp23s08 - Needs Testing
            elif device.lower() == "mcp23s08":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23s08Setup(int(params['pinBase']),
                                           int(params['spiPort'],16),
                                           int(params['devId']))

            # sr595 - Needs Testing
            elif device.lower() == "sr595":
                for slave in device_slaves:
                    params = slave
                    wiringpi.sr595Setup(int(params['pinBase']),
                                        int(params['numPins']),
                                        int(params['dataPin']),
                                        int(params['clockPin']),
                                        int(params['latchPin']))
            
            # pcf8574
            elif device.lower() == "pcf8574":
                for slave in device_slaves:
                    params = slave
                    wiringpi.pcf8574Setup(int(params['pinBase']),
                                          int(params['i2cAddress'],16))

            else:
                logging.error("Device defined is not supported, please check your devices "
                              "settings: " + str(device))
    except Exception as e:
        logging.debug("Error setting up devices, please check your devices settings.")
        logging.debug(e)

def is_pin_pwm(i):
    """Is the pin setup for pwm"""
    return PIN_MODES[i].lower() == "pwm"

def set_pins_as_outputs():
    """Set all the configured pins as outputs."""
    for i in range(GPIOLEN):
        set_pin_as_output(i)

def set_pins_as_inputs():
    """Set all the configured pins as inputs."""
    for i in range(GPIOLEN):
        set_pin_as_input(i)
            
def set_pin_as_output(i):
    """Set the specified pin as an output."""
    if not _EXPORT_PINS:
        wiringpi.pinMode(_GPIO_PINS[i], _GPIOASOUTPUT)
        if is_pin_pwm(i):
            wiringpi.softPwmCreate(_GPIO_PINS[i], 0, _PWM_MAX)
    else:
        # set pin as output for use in export mode
        subprocess.check_call([_GPIO_UTILITY_PATH, 'export', str(_GPIO_PINS[i]), 'out'])

def set_pin_as_input(i):
    """Set the specified pin as an input."""
    if not _EXPORT_PINS:
        wiringpi.pinMode(_GPIO_PINS[i], _GPIOASINPUT)
    else:
        # set pin as input for use in export mode 
        subprocess.check_call([_GPIO_UTILITY_PATH, 'export', str(_GPIO_PINS[i]), 'in'])

def turn_off_lights(usealwaysonoff=0):
    """
    Turn off all the lights

    But leave on all lights designated to be always on if specified.
    """
    for i in range(GPIOLEN):
        if is_pin_pwm(i):
            wiringpi.softPwmWrite(_GPIO_PINS[i], _PWM_OFF)
            continue

        if usealwaysonoff:
            if i + 1 not in _ALWAYS_ON_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOINACTIVE)
        else:
            wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOINACTIVE)

def turn_on_lights(usealwaysonoff=0):
    """
    Turn on all the lights

    But leave off all lights designated to be always off if specified.
    """
    for i in range(GPIOLEN):
        if is_pin_pwm(i):
            wiringpi.softPwmWrite(_GPIO_PINS[i], _PWM_ON)
            continue

        if usealwaysonoff:
            if i + 1 not in _ALWAYS_OFF_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOACTIVE)
        else:
            wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOACTIVE)

def turn_off_light(i, useoverrides=0, brightness=1.0):
    """
    Turn off the specified light

    Taking into account various overrides if specified.
    """
    if is_pin_pwm(i) and not useoverrides:
        wiringpi.softPwmWrite(_GPIO_PINS[i], _PWM_OFF)
        return
    elif is_pin_pwm(i) and useoverrides:
        turn_on_light(i, False, brightness)
        return

    if useoverrides:
        if i + 1 not in _ALWAYS_ON_CHANNELS:
            if i + 1 not in _INVERTED_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOINACTIVE)
            else:
                wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOACTIVE)
    else:
        wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOINACTIVE)

def turn_on_light(i, useoverrides=0, brightness=1.0):
    """
    Turn on the specified light

    Taking into account various overrides if specified.
    """
    if is_pin_pwm(i):
        if _ACTIVE_LOW_MODE:
            brightness = 1.0 - brightness
        if brightness < 0.0:
            brightness = 0.0
        if brightness > 1.0:
            brightness = 1.0
        # if inverted channel, invert brightness
        if i + 1 in _INVERTED_CHANNELS:
            brightness = 1 - brightness
        wiringpi.softPwmWrite(_GPIO_PINS[i], int(brightness * _PWM_MAX))
        return

    if useoverrides:
        if i + 1 not in _ALWAYS_OFF_CHANNELS:
            if i + 1 not in _INVERTED_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOACTIVE)
            else:
                wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOINACTIVE)
    else:
        wiringpi.digitalWrite(_GPIO_PINS[i], _GPIOACTIVE)

def clean_up():
    """
    Clean up and end the lightshow

    Turn off all lights set the pins as inputs
    """
    turn_off_lights()
    set_pins_as_inputs()

def initialize():
    """Set pins as outputs, and start all lights in the off state."""
    enable_device()
    set_pins_as_outputs()
    turn_off_lights()

# __________________Main________________
def main():
    """main"""
    parser = argparse.ArgumentParser()
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
        print "Press <CTRL>-C to stop"
        while True:
            try:
                for light in lights:
                    if is_pin_pwm(light):
                        for _ in range(flashes):
                            for brightness in range(0, _PWM_MAX):
                                # fade in
                                turn_on_light(light, 0, float(brightness) / _PWM_MAX)
                                time.sleep(sleep / _PWM_MAX)
                            for brightness in range(_PWM_MAX - 1, -1, -1):
                                # fade out
                                turn_on_light(light, 0, float(brightness) / _PWM_MAX)
                                time.sleep(sleep / _PWM_MAX)
            except KeyboardInterrupt:
                print "\nstopped"
                clean_up()
                break
    elif state == "flash":
        print "Press <CTRL>-C to stop"
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
                clean_up()
                break
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
