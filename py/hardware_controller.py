#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Ryan Jennings
# Author: Chris Usey
# Author: Todd Giles (todd@lightshowpi.com)
# Modifications: Tom Enos
"""
Control the raspberry pi hardware.

The hardware controller handles all interaction with the raspberry pi hardware to turn the lights
on and off.

Third party dependencies:

wiringpi2: python wrapper around wiring pi - https://github.com/WiringPi/WiringPi2-Python
"""

import argparse
import logging
import math
import time
import subprocess
import sys

import configuration_manager as cm
import wiringpi2 as wiringpi

# Get Configurations
hardware_config = cm.hardware()
DEVICES = hardware_config['devices']
GPIO_PINS = hardware_config['gpio_pins']
GPIOLEN = hardware_config['gpiolen']
PIN_MODES = hardware_config['pin_modes']
PWM_MAX = hardware_config['pwm_range']
ACTIVE_LOW_MODE = hardware_config['active_low_mode']
EXPORT_PINS = hardware_config['export_pins']
_GPIO_UTILITY_PATH = hardware_config['gpio_utility_path']

lightshow_config = cm.lightshow()

# Initialize GPIO
GPIOASINPUT = 0
GPIOASOUTPUT = 1


# quicker then using a function and a list index to check if the pin is in pwm mode
is_pin_pwm = list()
for mode in range(len(PIN_MODES)):
    if PIN_MODES[mode] == "pwm":
        is_pin_pwm.append(True)
    else:
        is_pin_pwm.append(False)

# Check ActiveLowMode Configuration Setting
GPIOACTIVE = int(not ACTIVE_LOW_MODE)
PWM_ON = PWM_MAX * int(not ACTIVE_LOW_MODE)
GPIOINACTIVE = int(ACTIVE_LOW_MODE)
PWM_OFF = PWM_MAX * int(ACTIVE_LOW_MODE)


# Functions
def enable_device():
    """enable the specified device """
    try:
        for key in DEVICES.keys():
            device = key
            device_slaves = DEVICES[key]
            
            # mcp23017
            if device.lower() == "mcp23017":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23017Setup(int(params['pinBase']),
                                           int(params['i2cAddress'], 16))
            
            # mcp23s17
            elif device.lower() == "mcp23s17":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23s17Setup(int(params['pinBase']),
                                           int(params['spiPort'], 16),
                                           int(params['devId']))
            
            # TODO: Devices below need testing, these should work but 
            # could not verify due to lack of hardware
            
            # mcp23016
            elif device.lower() == "mcp23016":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23016Setup(int(params['pinBase']),
                                           int(params['i2cAddress'], 16))

            # mcp23s08 - Needs Testing
            elif device.lower() == "mcp23008":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23008Setup(int(params['pinBase']),
                                           int(params['i2cAddress'], 16))

            # mcp23s08 - Needs Testing
            elif device.lower() == "mcp23s08":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23s08Setup(int(params['pinBase']),
                                           int(params['spiPort'], 16),
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
                                          int(params['i2cAddress'], 16))

            else:
                logging.error("Device defined is not supported, please check your devices "
                              "settings: " + str(device))
    except Exception as e:
        logging.debug("Error setting up devices, please check your devices settings.")
        logging.debug(e)


def set_pins_as_outputs():
    """Set all the configured pins as outputs."""
    for pin in range(GPIOLEN):
        set_pin_as_output(pin)


def set_pins_as_inputs():
    """Set all the configured pins as inputs."""
    for pin in range(GPIOLEN):
        set_pin_as_input(pin)


def set_pin_as_output(pin):
    """
    Set the specified pin as an output.

    :param pin: int, index of pin in GPIO_PINS
    """
    if EXPORT_PINS:
        # set pin as output for use in export mode
        subprocess.check_call([_GPIO_UTILITY_PATH, 'export', str(GPIO_PINS[pin]), 'out'])
    else:
        if is_pin_pwm[pin]:
            wiringpi.softPwmCreate(GPIO_PINS[pin], 0, PWM_MAX)
        else:
            wiringpi.pinMode(GPIO_PINS[pin], GPIOASOUTPUT)


def set_pin_as_input(pin):
    """
    Set the specified pin as an input.

    :param pin: int, index of pin in GPIO_PINS
    """
    if EXPORT_PINS:
        # set pin as input for use in export mode 
        subprocess.check_call([_GPIO_UTILITY_PATH, 'export', str(GPIO_PINS[pin]), 'in'])
    else:
        wiringpi.pinMode(GPIO_PINS[pin], GPIOASINPUT)


def turn_off_lights(use_always_onoff=0):
    """
    Turn off all the lights

    But leave on all lights designated to be always on if specified.

    :param use_always_onoff: int or boolean, should always on/off be used
    """
    for pin in range(GPIOLEN):
        turn_off_light(pin, use_always_onoff)


def turn_off_light(pin, use_overrides=0):
    """
    Turn off the specified light

    Taking into account various overrides if specified.
    :param pin: int, index of pin in GPIO_PINS
    :param use_overrides: int or boolean, should overrides be used
    """
    if use_overrides:
        if is_pin_pwm[pin]:
            turn_on_light(pin, use_overrides, 0)
        else:
            if pin + 1 not in lightshow_config['always_on_channels']:
                if pin + 1 not in lightshow_config['invert_channels']:
                    wiringpi.digitalWrite(GPIO_PINS[pin], GPIOINACTIVE)
                else:
                    wiringpi.digitalWrite(GPIO_PINS[pin], GPIOACTIVE)
    else:
        if is_pin_pwm[pin]:
            wiringpi.softPwmWrite(GPIO_PINS[pin], PWM_OFF)
        else:    
            wiringpi.digitalWrite(GPIO_PINS[pin], GPIOINACTIVE)


def turn_on_lights(use_always_onoff=0):
    """
    Turn on all the lights

    But leave off all lights designated to be always off if specified.

    :param use_always_onoff: int or boolean, should always on/off be used
   """
    for pin in range(GPIOLEN):
        turn_on_light(pin, use_always_onoff)

def turn_on_light(pin, use_overrides=0, brightness=1.0):
    """
    Turn on the specified light

    Taking into account various overrides if specified.
    :param pin: int, index of pin in GPIO_PINS
    :param use_overrides: int or boolean, should overrides be used
    :param brightness: float, a float representing the brightness of the lights
    """
    if is_pin_pwm[pin]:
        if math.isnan(brightness):
            brightness = 0.0
        if ACTIVE_LOW_MODE:
            brightness = 1.0 - brightness
        if brightness < 0.0:
            brightness = 0.0
        if brightness > 1.0:
            brightness = 1.0
        if use_overrides:
            if pin + 1 in lightshow_config['always_off_channels']:
                brightness = 0
            elif pin + 1 in lightshow_config['always_on_channels']:
                brightness = 1
            if pin + 1 in lightshow_config['invert_channels']:
                brightness = 1 - brightness
        wiringpi.softPwmWrite(GPIO_PINS[pin], int(brightness * PWM_MAX))
        return

    if use_overrides:
        if pin + 1 not in lightshow_config['always_off_channels']:
            if pin + 1 not in lightshow_config['invert_channels']:
                wiringpi.digitalWrite(GPIO_PINS[pin], GPIOACTIVE)
            else:
                wiringpi.digitalWrite(GPIO_PINS[pin], GPIOINACTIVE)
    else:
        wiringpi.digitalWrite(GPIO_PINS[pin], GPIOACTIVE)


def clean_up():
    """
    Clean up and end the lightshow

    Turn off all lights set the pins as inputs
    """
    turn_off_lights()
    set_pins_as_inputs()


def initialize():
    """Set pins as outputs, and start all lights in the off state."""
    if EXPORT_PINS:
        wiringpi.wiringPiSetupSys()
        logging.info("Running as non root user, disabling pwm mode on all pin")
        for pin in range(GPIOLEN):
            PIN_MODES[pin] = "onoff"
            is_pin_pwm[pin] = False
    else:
        wiringpi.wiringPiSetup()

    enable_device()
    set_pins_as_outputs()
    turn_off_lights()


def load_config():
    global lightshow_config
    logging.info("Reloading config")
    lightshow_config = cm.lightshow()
    # correct for export pins mode
    if EXPORT_PINS:
        for pin in range(GPIOLEN):
            PIN_MODES[pin] = "onoff"
            is_pin_pwm[pin] = False


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
        lights = range(0, len(GPIO_PINS))

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
                    if is_pin_pwm[light]:
                        for _ in range(flashes):
                            for brightness in range(0, PWM_MAX):
                                # fade in
                                turn_on_light(light, 0, float(brightness) / PWM_MAX)
                                time.sleep(sleep / PWM_MAX)
                            for brightness in range(PWM_MAX - 1, -1, -1):
                                # fade out
                                turn_on_light(light, 0, float(brightness) / PWM_MAX)
                                time.sleep(sleep / PWM_MAX)
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
