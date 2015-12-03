#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Ryan Jennings
# Author: Chris Usey
# Author: Todd Giles (todd@lightshowpi.com)
# Author: Tom Enos (tomslick.ca@gmail.com)

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
import sys
import Platform
import random

import configuration_manager

from collections import defaultdict

import networking

cm = configuration_manager.Configuration()

is_a_raspberryPI = Platform.platform_detect() == 1

if is_a_raspberryPI:
    import wiringpi2 as wiringpi
else:
    # if this is not a RPi you can't run wiringpi so lets load
    # something in its place
    import wiring_pi_stub as wiringpi

    logging.debug("Not running on a raspberryPI")

_PWM_MAX = cm.hardware.pwm_range
_ACTIVE_LOW_MODE = cm.hardware.active_low_mode

always_on_channels = cm.lightshow.always_on_channels
always_off_channels = cm.lightshow.always_off_channels
inverted_channels = cm.lightshow.invert_channels

# Initialize GPIO
_GPIOASINPUT = 0
_GPIOASOUTPUT = 1
GPIOLEN = cm.hardware.gpio_len

is_pin_pwm = list()
for mode in range(len(cm.hardware.pin_modes)):
    if cm.hardware.pin_modes[mode] == "pwm":
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

# left in for compatibility with external scripts
_GPIO_PINS = cm.hardware.gpio_pins


# Functions
def enable_device():
    """enable the specified device """
    try:
        devices = cm.hardware.devices

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

    :param pin: index of pin in cm.hardware.gpio_pins
    :type pin: int
    """
    if is_pin_pwm[pin]:
        wiringpi.softPwmCreate(cm.hardware.gpio_pins[pin], 0, _PWM_MAX)
    else:
        wiringpi.pinMode(cm.hardware.gpio_pins[pin], _GPIOASOUTPUT)


def set_pins_as_inputs():
    """Set all the configured pins as inputs."""
    for pin in range(GPIOLEN):
        set_pin_as_input(pin)


def set_pin_as_input(pin):
    """Set the specified pin as an input.

    :param pin: index of pin in cm.hardware.gpio_pins
    :type pin: int
    """
    wiringpi.pinMode(cm.hardware.gpio_pins[pin], _GPIOASINPUT)


def turn_off_lights(use_always_onoff=False):
    """
    Turn off all the lights

    But leave on all lights designated to be always on if specified.

    :param use_always_onoff: boolean, should always on/off be used
    :type use_always_onoff: bool
    """
    for pin in range(GPIOLEN):
        set_light(pin, use_always_onoff, 0)


# turn_off_light and turn_on_light are left in for compatibility 
# with external scripts and will be removed in future versions
def turn_off_light(pin, use_overrides=False):
    """
    Turn off the specified light

    Taking into account various overrides if specified.

    :param pin: index of pin in cm.hardware.gpio_pins
    :type pin: int

    :param use_overrides: should overrides be used
    :type use_overrides: bool
    """
    set_light(pin, use_overrides, 0)


def turn_on_light(pin, use_overrides=False, brightness=1.0):
    """
    Turn off the specified light

    Taking into account various overrides if specified.

    :param pin: index of pin in cm.hardware.gpio_pins
    :type pin: int

    :param use_overrides: should overrides be used
    :type use_overrides: bool
    """
    set_light(pin, use_overrides, brightness)


def turn_on_lights(use_always_onoff=False):
    """
    Turn on all the lights

    But leave off all lights designated to be always off if specified.

    :param use_always_onoff: should always on/off be used
    :type use_always_onoff: bool
    """
    for pin in range(GPIOLEN):
        set_light(pin, use_always_onoff)


def set_light(pin, use_overrides=False, brightness=1.0):
    """Set the birghtness of the specified light
    
    Taking into account various overrides if specified.
    The default is full on (1.0)
    To turn a light off pass 0 for brightness
    If brightness is a float between 0 and 1.0 that level 
    will be set.
    
    This function replaces turn_on_light and turn_off_light

    :param pin: index of pin in cm.hardware.gpio_pins
    :type pin: int

    :param use_overrides: should overrides be used
    :type use_overrides: bool

    :param brightness: float, a float representing the brightness of the lights
    :type brightness: float
    """
    if math.isnan(brightness):
        brightness = 0.0

    if _ACTIVE_LOW_MODE:
        brightness = 1.0 - brightness

    if use_overrides:
        if pin + 1 in always_off_channels:
            brightness = 0
        elif pin + 1 in always_on_channels:
            brightness = 1

        if pin + 1 in inverted_channels:
            brightness = 1 - brightness

    if not network.playing and server:
        network.broadcast(cm.hardware.gpio_pins.index(cm.hardware.gpio_pins[pin]), brightness)

    if is_pin_pwm[pin]:
        wiringpi.softPwmWrite(cm.hardware.gpio_pins[pin], int(brightness * _PWM_MAX))
    else:
        wiringpi.digitalWrite(cm.hardware.gpio_pins[pin], int(brightness > 0.5))


def clean_up():
    """
    Clean up and end the lightshow

    Turn off all lights and set the pins as inputs
    """
    network.unset_playing()
    turn_off_lights()
    set_pins_as_inputs()
    try:
        streaming.close()
    except (AttributeError, socket.error, NameError):
        pass


def initialize():
    """Set pins as outputs and start all lights in the off state."""
    wiringpi.wiringPiSetup()
    enable_device()
    set_pins_as_outputs()

    turn_off_lights()

# network setup if used
network = networking.networking(cm, set_light)
server = network.networking == "server"

# test functions
def light_on(pins, override=False, brightness=1.0):
    """work around to make custom channel mapping work with hardware tests"""
    if ccm:
        pins = ccm_map[pins]
    else:
        pins = [pins]

    if len(pins) == 0:
        return

    for pin in pins:
        if not is_pin_pwm[pin]:
            brightness = 1

        set_light(pin, use_overrides=override, brightness=brightness)


def light_off(pins, override=False, brightness=0.0):
    """work around to make custom channel mapping work with hardware tests"""
    if ccm:
        print ccm
        pins = ccm_map[pins]
    else:
        pins = [pins]

    if len(pins) == 0:
        return

    for pin in pins:
        set_light(pin, use_overrides=override, brightness=brightness)


def fade():
    """Fade lights in and out in sequence"""
    # Test fading in and out for each light configured in pwm mode
    print "Press <CTRL>-C to stop"
    while True:
        try:
            for light in lights:
                print "channel %s " % light
                if is_pin_pwm[light]:
                    for _ in range(flashes):
                        for brightness in range(0, _PWM_MAX):
                            # fade in
                            light_on(light, False, float(brightness) / _PWM_MAX)
                            time.sleep(sleep / _PWM_MAX)
                        for brightness in range(_PWM_MAX - 1, -1, -1):
                            # fade out
                            light_on(light, False, float(brightness) / _PWM_MAX)
                            time.sleep(sleep / _PWM_MAX)
                else:
                    print "channel %s not set to pwm mode" % light

        except KeyboardInterrupt:
            print "\nstopped"
            for light in lights:
                light_off(light)
            break


def flash():
    """Flash lights in sequence"""
    print "Press <CTRL>-C to stop"
    while True:
        try:
            for light in lights:
                print "channel %s " % light
                for _ in range(flashes):
                    light_on(light)
                    time.sleep(sleep)
                    light_off(light)
                    time.sleep(sleep)
        except KeyboardInterrupt:
            print "\nstopped"
            for light in lights:
                light_off(light)
            break


def cylon():
    """Cylon

    Lights one channel at a time in order
    Then backs down to the first rapidly
    """
    # pause for 1 second
    time.sleep(1)

    # working loop
    print "Press <CTRL>-C to stop"
    while True:
        try:
            # here we just loop over the gpio pins and do something with them
            # except the last one
            for light in range(len(lights) - 1):
                # turn off all the lights
                for l in lights:
                    light_off(l)

                # then turn on one
                light_on(light)

                # wait a little bit
                time.sleep(.06)

            # to make the transition back smoother we handle the last pin here
            for l in lights:
                light_off(l)
            light_on(light + 1)

            # this loop walks it back the other way
            for light in range(len(lights) - 1, 0, -1):
                # turn off all the lights
                for l in lights:
                    light_off(l)

                # then turn on one
                light_on(light)

                # wait a little bit
                time.sleep(.06)

            # again to make it smoother handle the first pin like the last pin
            for l in lights:
                light_off(l)
            light_on(light - 1)
        except KeyboardInterrupt:
            print "\nstopped"
            for light in lights:
                light_off(light)
            break


def random_pattern():
    """Flash your lights in a random pattern"""
    channels = dict.fromkeys(range(0, len(lights)), [True, time.time()])

    # get a number that is about 50% the length of your gpio's
    # this will be use to make sure that no more then 50% of
    # the light will be off at any one time
    max_off = int(round(len(channels) * .5))

    # start with all the channels on
    for light in lights:
        light_on(light)

    # working loop
    print "Press <CTRL>-C to stop"
    while True:
        try:
            # here we just loop over the gpio pins
            for light in channels:
                # this is where we check to see if we have any light
                # that are turned off
                # if they are off we will check the time to see if we
                # want to turn them back on yet, if we do then turn it on
                if not channels[light][0]:
                    if channels[light][1] < time.time():
                        channels[light][0] = True
                        light_on(light)

            # count the number of channels that are off
            off = [k for (k, v) in channels.iteritems() if not v.count(1)]

            # if less then out max count of light that we chose
            # we can turn one off
            if len(off) < max_off:
                # pick a light at random to turn off
                choice = random.randrange(0, len(lights))
                # if it's on then lets turn it off
                if channels[choice][0]:
                    # pick a duration for that light to be off
                    # default times are between 1/2 and secong and 1.8 seconds
                    duration = random.uniform(0.5, 1.8)

                    # store this informatin in our dict
                    channels[choice] = [False, time.time() + duration]
                    # and turn that light off then continue with the main loop
                    # and do it all over again
                    light_off(choice)
        except KeyboardInterrupt:
            print "\nstopped"
            for light in lights:
                light_off(light)
            break


def dance():
    """
    dancing pair

    Start at each end and dance to the other using pwm or onoff
    """
    # the gpio pins in reversed order
    lights2 = lights[::-1]

    # get _PWM_MAX from the hc module
    # this is the max value for the pwm channels
    pwm_max = _PWM_MAX

    # working loop, we will do this sequence 10 times then end
    while True:
        try:
            # here we just loop over the gpio pins and turn them on and off
            # with the pwm feature of lightshowpi
            for light in range(int(len(lights) / 2)):
                if is_pin_pwm[light]:
                    for brightness in range(0, pwm_max):
                        # fade in
                        light_on(lights[light], 0, brightness=float(brightness) / pwm_max)
                        light_on(lights2[light], brightness=float(brightness) / pwm_max)
                        time.sleep(.1 / pwm_max)

                    for brightness in range(pwm_max - 1, -1, -1):
                        # fade out
                        light_on(lights[light], brightness=float(brightness) / pwm_max)
                        light_on(lights2[light], brightness=float(brightness) / pwm_max)
                        time.sleep(.1 / pwm_max)
                else:
                    light_on(lights[light], 1)
                    light_on(lights2[light], 1)
                    time.sleep(.5)
                    light_off(lights[light], 0)
                    light_off(lights2[light], 0)
                    
            for light in range(int(len(lights) / 2) - 1, -1, -1):
                if is_pin_pwm[light]:
                    for brightness in range(0, pwm_max):
                        # fade in
                        light_on(lights[light], brightness=float(brightness) / pwm_max)
                        light_on(lights2[light], brightness=float(brightness) / pwm_max)
                        time.sleep(.1 / pwm_max)

                    for brightness in range(pwm_max - 1, -1, -1):
                        # fade out
                        light_on(lights[light], brightness=float(brightness) / pwm_max)
                        light_on(lights2[light], brightness=float(brightness) / pwm_max)
                        time.sleep(.1 / pwm_max)
                else:
                    light_on(lights[light], 1)
                    light_on(lights2[light], 1)
                    time.sleep(.5)
                    light_off(lights[light], 0)
                    light_off(lights2[light], 0)

        except KeyboardInterrupt:
            print "\nstopped"
            for light in lights:
                light_off(light)
            break


def step():
    # Test fading in and out for each light configured in pwm mode
    print "Press <CTRL>-C to stop"
    while True:
        try:
            for light in lights:
                print "channel %s " % light
                for brightness in range(0, _PWM_MAX):
                    # fade in
                    light_on(light, False, float(brightness) / _PWM_MAX)
                    time.sleep(sleep / _PWM_MAX)

            for light in reversed(lights):
                print "channel %s " % light
                for brightness in range(_PWM_MAX - 1, -1, -1):
                    # fade out
                    if is_pin_pwm[light]:
                        light_on(light, False, float(brightness) / _PWM_MAX)
                    else:
                        light_off(light, False, 0)
                    time.sleep(sleep / _PWM_MAX)

        except KeyboardInterrupt:
            print "\nstopped"
            for light in lights:
                light_off(light)
            break


def main():
    """main"""
    initialize()
    network.unset_playing()

    if state == "cleanup":
        clean_up()
    elif state == "off":
        for light in lights:
            light_off(light)
    elif state == "on":
        for light in lights:
            light_on(light)
    elif state == "fade":
        fade()
    elif state == "flash":
        flash()
    elif state == "random_pattern":
        random_pattern()
    elif state == "cylon":
        cylon()
    elif state == "dance":
        dance()
    elif state == "step":
        step()
    else:
        parser.print_help()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', choices=["off",
                                            "on",
                                            "flash",
                                            "fade",
                                            "random_pattern",
                                            "cylon",
                                            "dance",
                                            "step",
                                            "cleanup"],
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

    ccm = False
    lights = [int(light) for light in args.light.split(',')]

    if -1 in lights:
        lights = range(0, cm.hardware.gpio_len)

        if cm.audio_processing.custom_channel_mapping != 0 and len(
                cm.audio_processing.custom_channel_mapping) == cm.hardware.gpio_len:
            ccm = True
            cc = [x - 1 for x in cm.audio_processing.custom_channel_mapping]
            ccm_map = dict()

            for light in lights:
                ccm_map[light] = [idx for idx, pin in enumerate(cc) if pin == light]
            if len(lights) == cm.hardware.gpio_len:
                lights = range(max(cm.audio_processing.custom_channel_mapping))
    main()
