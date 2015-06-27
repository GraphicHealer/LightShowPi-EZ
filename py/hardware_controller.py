#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Ryan Jennings
# Author: Chris Usey
# Author: Todd Giles (todd@lightshowpi.com)

"""Control the raspberry pi hardware.

The hardware controller handles all interaction with the raspberry pi
hardware to turn the lights on and off.

Third party dependencies:

wiringpi2: python wrapper around wiring pi
    https://github.com/WiringPi/WiringPi2-Python
"""

import argparse
import logging
import math
import time
import subprocess
import platform
import configuration_manager as cm

is_a_raspberryPI = "raspberrypi" in platform.uname()

if is_a_raspberryPI:
    import wiringpi2 as wiringpi
else:
    # if this is not a RPi you can't run wiringpi so lets load
    # something in its place
    import wiring_pi_stub as wiringpi
    logging.debug("Not running on a raspberryPI")

# Get Configurations - TODO(todd): Move more of this into configuration manager
_CONFIG = cm.CONFIG

_GPIO_PINS = [int(gpio_pin) for gpio_pin in _CONFIG.get('hardware', 'gpio_pins').split(',')]

PIN_MODES = _CONFIG.get('hardware', 'pin_modes').split(',')

_PWM_MAX = int(_CONFIG.get('hardware', 'pwm_range'))

_ACTIVE_LOW_MODE = _CONFIG.getboolean('hardware', 'active_low_mode')

_LIGHTSHOW_CONFIG = cm.lightshow()

_HARDWARE_CONFIG = cm.hardware()

_ALWAYS_ON_CHANNELS = \
    [int(channel) for channel in _LIGHTSHOW_CONFIG['always_on_channels'].split(',')]

_ALWAYS_OFF_CHANNELS = \
    [int(channel) for channel in _LIGHTSHOW_CONFIG['always_off_channels'].split(',')]

_INVERTED_CHANNELS = \
    [int(channel) for channel in _LIGHTSHOW_CONFIG['invert_channels'].split(',')]

_EXPORT_PINS = _CONFIG.getboolean('hardware', 'export_pins')
_GPIO_UTILITY_PATH = _CONFIG.get('hardware', 'gpio_utility_path')

# Initialize GPIO
_GPIOASINPUT = 0
_GPIOASOUTPUT = 1
GPIOLEN = len(_GPIO_PINS)

# If only a single pin mode is specified, assume all pins should be in that mode
if len(PIN_MODES) == 1:
    PIN_MODES = [PIN_MODES[0] for _ in range(GPIOLEN)]

is_pin_pwm = list()
for mode in range(len(PIN_MODES)):
    if PIN_MODES[mode] == "pwm":
        is_pin_pwm.append(True)
    else:
        is_pin_pwm.append(False)

# Check ActiveLowMode Configuration Setting
if _ACTIVE_LOW_MODE:
    # Enabled
    _GPIOACTIVE = 0
    _PWM_ON = 0
    _GPIOINACTIVE = 1
    _PWM_OFF = _PWM_MAX
else:
    # Disabled
    _GPIOACTIVE = 1
    _PWM_ON = _PWM_MAX
    _GPIOINACTIVE = 0
    _PWM_OFF = 0


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
                                           int(params['i2cAddress'],
                                               16))

            # mcp23s17
            elif device.lower() == "mcp23s17":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23s17Setup(int(params['pinBase']),
                                           int(params['spiPort'],
                                               16),
                                           int(params['devId']))

            # TODO: Devices below need testing, these should work but
            # could not verify due to lack of hardware

            # mcp23016
            elif device.lower() == "mcp23016":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23016Setup(int(params['pinBase']),
                                           int(params['i2cAddress'],
                                               16))

            # mcp23s08 - Needs Testing
            elif device.lower() == "mcp23008":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23008Setup(int(params['pinBase']),
                                           int(params['i2cAddress'],
                                               16))

            # mcp23s08 - Needs Testing
            elif device.lower() == "mcp23s08":
                for slave in device_slaves:
                    params = slave
                    wiringpi.mcp23s08Setup(int(params['pinBase']),
                                           int(params['spiPort'],
                                               16),
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
                                          int(params['i2cAddress'],
                                              16))

            else:
                logging.error("Device defined is not supported, please check "
                              "your devices settings: " + str(device))
    except Exception as error:
        logging.debug("Error setting up devices, please check your devices "
                      "settings.")
        logging.debug(error)


def set_pins_as_outputs():
    """Set all the configured pins as outputs."""
    for pin in range(GPIOLEN):
        set_pin_as_output(pin)


def set_pin_as_output(pin):
    """Set the specified pin as an output.

    :param pin: index of pin in _GPIO_PINS
    :type pin: int
    """
    if _EXPORT_PINS and is_a_raspberryPI:
        # set pin as output for use in export mode
        subprocess.check_call([_GPIO_UTILITY_PATH, 'export', str(_GPIO_PINS[pin]), 'out'])
    else:
        if is_pin_pwm[pin]:
            wiringpi.softPwmCreate(_GPIO_PINS[pin], 0, _PWM_MAX)
        else:
            wiringpi.pinMode(_GPIO_PINS[pin], _GPIOASOUTPUT)


def set_pins_as_inputs():
    """Set all the configured pins as inputs."""
    for pin in range(GPIOLEN):
        set_pin_as_input(pin)


def set_pin_as_input(pin):
    """Set the specified pin as an input.

    :param pin: index of pin in _GPIO_PINS
    :type pin: int
    """
    if _EXPORT_PINS and is_a_raspberryPI:
        # set pin as input for use in export mode
        subprocess.check_call([_GPIO_UTILITY_PATH, 'export', str(_GPIO_PINS[pin]), 'in'])
    else:
        wiringpi.pinMode(_GPIO_PINS[pin], _GPIOASINPUT)


def turn_off_lights(use_always_onoff=False):
    """
    Turn off all the lights

    But leave on all lights designated to be always on if specified.

    :param use_always_onoff: boolean, should always on/off be used
    :type use_always_onoff: bool
    """
    for pin in range(GPIOLEN):
        turn_off_light(pin, use_always_onoff)


def turn_off_light(pin, use_overrides=False):
    """
    Turn off the specified light

    Taking into account various overrides if specified.

    :param pin: index of pin in _GPIO_PINS
    :type pin: int

    :param use_overrides: should overrides be used
    :type use_overrides: bool
    """
    if use_overrides:
        if is_pin_pwm[pin]:
            turn_on_light(pin, use_overrides, _PWM_OFF)
        else:
            if pin + 1 not in _ALWAYS_OFF_CHANNELS:
                if pin + 1 not in _INVERTED_CHANNELS:
                    wiringpi.digitalWrite(_GPIO_PINS[pin], _GPIOINACTIVE)
                else:
                    wiringpi.digitalWrite(_GPIO_PINS[pin], _GPIOACTIVE)
    else:
        if is_pin_pwm[pin]:
            wiringpi.softPwmWrite(_GPIO_PINS[pin], _PWM_OFF)
        else:
            wiringpi.digitalWrite(_GPIO_PINS[pin], _GPIOINACTIVE)


def turn_on_lights(use_always_onoff=False):
    """
    Turn on all the lights

    But leave off all lights designated to be always off if specified.

    :param use_always_onoff: should always on/off be used
    :type use_always_onoff: bool
    """
    for pin in range(GPIOLEN):
        turn_on_light(pin, use_always_onoff)


def turn_on_light(pin, use_overrides=False, brightness=1.0):
    """Turn on the specified light

    Taking into account various overrides if specified.

    :param pin: index of pin in _GPIO_PINS
    :type pin: int

    :param use_overrides: should overrides be used
    :type use_overrides: bool

    :param brightness: float, a float representing the brightness of the lights
    :type brightness: float
    """
    if is_pin_pwm[pin]:
        if math.isnan(brightness):
            brightness = 0.0
        if _ACTIVE_LOW_MODE:
            brightness = 1.0 - brightness
        if brightness < 0.0:
            brightness = 0.0
        if brightness > 1.0:
            brightness = 1.0
        if use_overrides:
            if pin + 1 in _ALWAYS_OFF_CHANNELS:
                brightness = 0
            elif pin + 1 in _ALWAYS_ON_CHANNELS:
                brightness = 1
            if pin + 1 in _INVERTED_CHANNELS:
                brightness = 1 - brightness
        wiringpi.softPwmWrite(_GPIO_PINS[pin], int(brightness * _PWM_MAX))
        return

    if use_overrides:
        if pin + 1 not in _ALWAYS_OFF_CHANNELS:
            if pin + 1 not in _INVERTED_CHANNELS:
                wiringpi.digitalWrite(_GPIO_PINS[pin], _GPIOACTIVE)
            else:
                wiringpi.digitalWrite(_GPIO_PINS[pin], _GPIOINACTIVE)
    else:
        wiringpi.digitalWrite(_GPIO_PINS[pin], _GPIOACTIVE)


def clean_up():
    """
    Clean up and end the lightshow

    Turn off all lights and set the pins as inputs
    """
    turn_off_lights()
    set_pins_as_inputs()
    if _EXPORT_PINS:
        subprocess.check_call([_GPIO_UTILITY_PATH, 'unexportall'])


def initialize():
    """Set pins as outputs and start all lights in the off state."""
    if _EXPORT_PINS:
        logging.info("Running as non root user, disabling pwm mode on all pins")

        for pin in range(GPIOLEN):
            PIN_MODES[pin] = "onoff"
            is_pin_pwm[pin] = False

        set_pins_as_outputs()
        wiringpi.wiringPiSetupSys()
    else:
        wiringpi.wiringPiSetup()
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
                    if is_pin_pwm[light]:
                        for _ in range(flashes):
                            for brightness in range(0, _PWM_MAX):
                                # fade in
                                turn_on_light(light, False, float(brightness) / _PWM_MAX)
                                time.sleep(sleep / _PWM_MAX)
                            for brightness in range(_PWM_MAX - 1, -1, -1):
                                # fade out
                                turn_on_light(light, False, float(brightness) / _PWM_MAX)
                                time.sleep(sleep / _PWM_MAX)
            except KeyboardInterrupt:
                print "\nstopped"
                for light in lights:
                    turn_off_light(light)
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
                for light in lights:
                    turn_off_light(light)
                break
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
