#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Ryan Jennings
# Author: Chris Usey
# Author: Todd Giles (todd@lightshowpi.org)
# Author: Tom Enos (tomslick.ca@gmail.com)

"""Control the Raspberry pi hardware.

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
import atexit
import signal
import threading
import os
from multiprocessing.managers import BaseManager

from collections import defaultdict

import configuration_manager
import led_module
import networking

args = None


def exit_function():
    """atexit function"""
    if args:
        if not args.state == "on":
            hc.turn_off_lights()
        if args.state == "random_pattern":
            exit_event.set()
            time.sleep(3)
            hc.turn_off_lights()


atexit.register(exit_function)

# Remove traceback on Ctrl-C
#signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))
signal.signal(signal.SIGINT, signal.SIG_IGN)

# load configuration
cm = configuration_manager.Configuration()


# Test if running on a RaspberryPi
is_a_raspberryPI = Platform.platform_detect() == 1

if is_a_raspberryPI:
    import wiringpi
else:
    # if this is not a RPi
    import wiring_pi as wiringpi

    logging.debug("Not running on a raspberryPI")

class LEDManager(BaseManager):
    pass

class Hardware(object):
    def __init__(self):
        self.cm = cm

        # list to store the Channels instances in
        self.channels = list()

        # network setup if used
        self.network = networking.Networking(cm)
        self.server = self.network.networking == "server"
        self.playing = self.network.playing
        self.broadcast = self.network.broadcast

        self.led = None
        if self.cm.configs.led:
            self.led = list()
            if self.cm.configs.led_multiprocess:
                LEDManager.register('LED', led_module.Led)      
                for lc in self.cm.configs.led:
                    self.cm.set_led(config_file=lc)
                    self.ledmanager = LEDManager()
                    self.ledmanager.start()
                    self.led.append(self.ledmanager.LED(self.cm.led))
            else:
                for lc in self.cm.configs.led:
                    self.cm.set_led(config_file=lc)
                    self.led.append(led_module.Led(self.cm.led))

        self.create_lights()
        self.set_overrides()

    # Methods
    @staticmethod
    def enable_device():
        """enable the specified device """
        try:
            devices = cm.hardware.devices

            for key in devices.keys():
                device = key
                device_slaves = devices[key]

                if device.lower() == "mcp23008":
                    for slave in device_slaves:
                        params = slave
                        wiringpi.mcp23008Setup(int(params['pinBase']),
                                               int(params['i2cAddress'],
                                                   16))

                elif device.lower() == "mcp23s08":
                    for slave in device_slaves:
                        params = slave
                        wiringpi.mcp23s08Setup(int(params['pinBase']),
                                               int(params['spiPort'],
                                                   16),
                                               int(params['devId']))

                elif device.lower() == "mcp23016":
                    for slave in device_slaves:
                        params = slave
                        wiringpi.mcp23016Setup(int(params['pinBase']),
                                               int(params['i2cAddress'],
                                                   16))

                elif device.lower() == "mcp23017":
                    for slave in device_slaves:
                        params = slave
                        wiringpi.mcp23017Setup(int(params['pinBase']),
                                               int(params['i2cAddress'],
                                                   16))

                elif device.lower() == "mcp23s17":
                    for slave in device_slaves:
                        params = slave
                        wiringpi.mcp23s17Setup(int(params['pinBase']),
                                               int(params['spiPort'],
                                                   16),
                                               int(params['devId']))

                elif device.lower() == "sr595":
                    for slave in device_slaves:
                        params = slave
                        wiringpi.sr595Setup(int(params['pinBase']),
                                            int(params['numPins']),
                                            int(params['dataPin']),
                                            int(params['clockPin']),
                                            int(params['latchPin']))

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

    def create_lights(self):
        """
        Create a Channel instance for each gpio pin to be used,
        setting up
        """
        for channel in range(cm.hardware.gpio_len):
            self.channels.append(Channel(cm.hardware.gpio_pins[channel],
                                         cm.hardware.is_pin_pwm[channel],
                                         cm.hardware.active_low_mode,
                                         cm.hardware.pwm_range,
                                         cm.hardware.piglow,
                                         self.led))

    def set_overrides(self):
        """
        Set override flags if they are to be used
        """
        for channel in range(cm.hardware.gpio_len):
            self.channels[channel].set_always_off(
                channel + 1 in cm.lightshow.always_off_channels)
            self.channels[channel].set_always_on(
                channel + 1 in cm.lightshow.always_on_channels)
            self.channels[channel].set_inverted(
                channel + 1 in cm.lightshow.invert_channels)

    def set_pins_as_outputs(self):
        """Set all the configured pins as outputs."""
        for pin in range(cm.hardware.gpio_len):
            self.set_pin_as_output(pin)

    def set_pins_as_inputs(self):
        """Set all the configured pins as inputs."""
        for pin in range(cm.hardware.gpio_len):
            self.set_pin_as_input(pin)

    def set_pin_as_output(self, pin):
        """
        Set the specified pin as an output.

        :param pin: int, index of pin in gpio_pins
        """
        self.channels[pin].set_as_output()

    def set_pin_as_input(self, pin):
        """
        Set the specified pin as an input.

        :param pin: int, index of pin in gpio_pins
        """
        self.channels[pin].set_as_input()

    def turn_on_lights(self, use_always_onoff=False):
        """
        Turn on all the lights

        But leave off all lights designated to be always off if specified.

        :param use_always_onoff: int or boolean, should always on/off be used
        """
        for pin in range(cm.hardware.physical_gpio_len):
            self.set_light(pin, use_always_onoff, 1.0)

        if self.led:
            for led_instance in self.led:
                led_instance.all_set_on = True
                led_instance.all_leds_on()

    def turn_off_lights(self, use_always_onoff=False):
        """
        Turn off all the lights

        But leave on all lights designated to be always on if specified.

        :param use_always_onoff: int or boolean, should always on/off be used
        """
        for pin in range(cm.hardware.physical_gpio_len):
            self.set_light(pin, use_always_onoff, 0)

        if self.led:
            for led_instance in self.led:
                led_instance.all_set_on = False
                led_instance.all_leds_off()

    # turn_off_light and turn_on_light are left in for compatibility
    # with external scripts and will be removed in future versions
    def turn_off_light(self, pin, use_overrides=False):
        """
        Turn off the specified light

        Taking into account various overrides if specified.

        :param pin: index of pin in cm.hardware.gpio_pins
        :type pin: int

        :param use_overrides: should overrides be used
        :type use_overrides: bool
        """
        self.set_light(pin, use_overrides, 0)

    def turn_on_light(self, pin, use_overrides=False, brightness=1.0):
        """
        Turn off the specified light

        Taking into account various overrides if specified.

        :param pin: index of pin in cm.hardware.gpio_pins
        :type pin: int

        :param use_overrides: should overrides be used
        :type use_overrides: bool
        """
        self.set_light(pin, use_overrides, brightness)

    def set_light(self, pin, use_overrides=False, brightness=1.0):
        """Set the brightness of the specified light
        
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
        if not self.playing and self.server:
            self.broadcast(cm.hardware.gpio_pins.index(cm.hardware.gpio_pins[pin]),
                           brightness)

        self.channels[pin].set_action(use_overrides, brightness)

    def clean_up(self):
        """
        Clean up and end the lightshow

        Turn off all lights and set the pins as inputs
        """
        self.network.unset_playing()
        self.turn_off_lights()
        self.set_pins_as_inputs()

    def initialize(self):
        """Set pins as outputs and start all lights in the off state."""
        wiringpi.wiringPiSetup()
        self.enable_device()
        self.set_pins_as_outputs()
        self.turn_off_lights()


class Channel(object):
    """
    Channel class
    """

    def __init__(self, pin_number, pin_mode, active_low_mode, pwm_max, piglow=False, led=None):
        self.pin_number = pin_number
        self.pwm = pin_mode

        self.pwm_max = pwm_max
        self.active_low_mode = active_low_mode

        self.pwm_on = pwm_max * int(not active_low_mode)
        self.pwm_off = pwm_max * int(active_low_mode)

        self.inout = 'Not set'
        self.always_on = False
        self.always_off = False
        self.inverted = False
        self.is_led = False
        self.led_m = led

        if pin_number > 999:
            self.is_led = True
            self.pin_number -= 1000
            self.action = lambda b: self.led_m.write(self.pin_number, int(b * 255))
            self.active_low_mode = False
        else:
            if self.pwm:
                self.action = lambda b: wiringpi.softPwmWrite(self.pin_number,
                                                              int(b * self.pwm_max))
            elif piglow:
                self.action = lambda b: wiringpi.analogWrite(self.pin_number + 577, int(b * 255))
            else:
                self.action = lambda b: wiringpi.digitalWrite(self.pin_number, int(b > 0.5))

    def set_as_input(self):
        """
        set up this pin as input
        """
        self.inout = 'pin is input'
        if not self.is_led:
            wiringpi.pinMode(self.pin_number, 0)

    def set_as_output(self):
        """
        set up this pin as output
        """
        self.inout = 'pin is output'
        if not self.is_led:
            if self.pwm:
                wiringpi.softPwmCreate(self.pin_number, 0, self.pwm_max)
            else:
                wiringpi.pinMode(self.pin_number, 1)

    def set_always_on(self, value):
        """
        Should this channel be always on

        :param value: boolean
        """
        self.always_on = value

    def set_always_off(self, value):
        """
        Should this channel be always off

        :param value: boolean
        """
        self.always_off = value

    def set_inverted(self, value):
        """
        Should this channel be inverted

        :param value: boolean
        """
        self.inverted = value

    def set_action(self, use_overrides=False, brightness=1.0):
        """
        Turn this light on or off, or some value in-between

        Taking into account various overrides if specified.
        :param use_overrides: int or boolean, should overrides be used
        :param brightness: float, between 0.0 and 1.0, brightness of light
        0.0 is full off
        1.0 is full on

        """
        if self.active_low_mode and not self.is_led:
            brightness = 1.0 - brightness

        if use_overrides and not self.is_led:
            if self.always_off:
                brightness = 0
            elif self.always_on:
                brightness = 1

            if self.inverted:
                brightness = 1 - brightness

        self.action(brightness)


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
        if not cm.hardware.is_pin_pwm[pin]:
            brightness = 1

        hc.set_light(pin, use_overrides=override, brightness=brightness)


def light_off(pins, override=False, brightness=0.0):
    """work around to make custom channel mapping work with hardware tests"""
    if ccm:
        pins = ccm_map[pins]
    else:
        pins = [pins]

    if len(pins) == 0:
        return

    for pin in pins:
        hc.set_light(pin, use_overrides=override, brightness=brightness)


def fade(from_test=False):
    """Fade lights in and out in sequence"""
    # Test fading in and out for each light configured in pwm mode
    if not from_test:
        print "Press <CTRL>-C to stop"

    if ccm:
        print "custom channel mapping is being used"
        print "multiple channels may display that the same time"

    while True:
        for light in lights:
            if ccm:
                for p in ccm_map[light]:
                    print "channel %s : gpio pin number %d" % (str(p + 1), cm.hardware.gpio_pins[p])
            else:
                print "channel %s : gpio pin number %d" % (
                    str(light + 1), cm.hardware.gpio_pins[light])

            print

            if cm.hardware.is_pin_pwm[light]:
                for _ in range(flashes):
                    for brightness in range(0, cm.hardware.pwm_range + 1):
                        # fade in
                        light_on(light, False, float(brightness) / cm.hardware.pwm_range)
                        time.sleep(sleep / cm.hardware.pwm_range)
                    for brightness in range(cm.hardware.pwm_range - 1, -1, -1):
                        # fade out
                        light_on(light, False, float(brightness) / cm.hardware.pwm_range)
                        time.sleep(sleep / cm.hardware.pwm_range)
            else:
                print "channel %s not set to pwm mode" % light

        if from_test:
            return


def flash(from_test=False):
    """Flash lights in sequence"""
    if not from_test:
        print "Press <CTRL>-C to stop"

    if ccm:
        print "custom channel mapping is being used"
        print "multiple channels may display that the same time"

    while True:
        for light in lights:
            if ccm:
                for p in ccm_map[light]:
                    print "channel %s : gpio pin number %d" % (str(p + 1), cm.hardware.gpio_pins[p])
            else:
                print "channel %s : gpio pin number %d" % (
                    str(light + 1), cm.hardware.gpio_pins[light])

            print

            for _ in range(flashes):
                light_on(light, False, 1.0)
                time.sleep(sleep)
                light_off(light, False, 0.0)
                time.sleep(sleep)
        if from_test:
            return


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
        # here we just loop over the gpio pins and do something with them
        # except the last one
        for light in lights[:-1]:
            # turn off all the lights
            for l in lights:
                light_off(l, False, 0.0)

            # then turn on one
            light_on(light, False, 1.0)

            # wait a little bit
            time.sleep(.02)

        # to make the transition back smoother we handle the last pin here
        light_off(lights[-2], False, 0.0)
        light_on(lights[-1], False, 1.0)

        # this loop walks it back the other way
        for light in lights[::-1][:-1]:
            # turn off all the lights
            for l in lights:
                light_off(l, False, 0.0)

            # then turn on one
            light_on(light, False, 1.0)

            # wait a little bit
            time.sleep(.02)

        # again to make it smoother handle the first pin like the last pin
        light_off(lights[::-1][-2], False, 0.0)
        light_on(lights[::-1][-1], False, 1.0)


def random_pattern():
    """Display a random pattern of lights

    This will turn your lights on in a random pattern.  It will read the pin modes
    and use that for the channels you have set.  pwm fade for pwm mode and flash
    for onoff mode.

    From the command line you can set lights to work in groups by using the
    --lights_in_group option (default 1)
    --lights_in_group is the number of lights that you wish to be bound as a group.
    if set to 3, 3 channels will be bound to the first group, and this will continue
    until all channels have been use in order of pin assignment with the last
    group containing the all leftover channels in the case of odd assignment.

    and you can adjust the speed of fade with the --pwm_speed option (default .5).

    If you wish to alter the pattern delay the --sleep' (default 0.5 seconds) is
    the minimum between transitions and the maximum is defined as max_pause
    (default 4 time min_pause) in this function.  This value is a random time
    between the min and max values and not a guarantee of exact time between
    transitions and will change for every transitions.

    --pwm_speed is the time it takes for full on or full off measured in seconds.
    .5 is half a second and 1 is a full second

    A complete command string would look like
    sudo python hardware_controller --random_pattern --lights_in_group=2 --sleep=.75 --pwm_speed=1.5

    Initial implementation Thanks to Russell Pyburn.
    """
    # your gpio pins
    pins = cm.hardware.gpio_pins

    min_pause = sleep * 1000

    # min and max time to pause before restarting light group
    max_pause = min_pause * 4.0

    light_group = list()
    step_range = [_ for _ in range(cm.hardware.pwm_range)]
    step_range.extend([_ for _ in range(cm.hardware.pwm_range, -1, -1)])

    def the_lights(exit_e, lits):
        while True:
            if exit_e.is_set():
                break

            time.sleep(random.randrange(min_pause, max_pause) * .001)

            # activate the lights
            for stp in step_range:
                for pin in lits:
                    light_on(pins.index(pin), True, stp * .01)

                time.sleep(pwm_speed / float(cm.hardware.pwm_range))

    # start the threads
    for group in range(0, len(pins), lights_per_group):
        light_group.append(threading.Thread(target=the_lights, args=(
            exit_event, pins[group:group + lights_per_group],)))
        light_group[-1].setDaemon(True)
        light_group[-1].start()

    print "press <ctrl-c> to exit"
    while True:
        time.sleep(.1)


def dance():
    """
    dancing pair

    Start at each end and dance to the other using pwm or onoff
    """
    # the gpio pins in reversed order
    lights2 = lights[::-1]

    # get cm.hardware.pwm_range from the hc module
    # this is the max value for the pwm channels
    pwm_max = cm.hardware.pwm_range

    # working loop, we will do this sequence 10 times then end
    while True:
        # here we just loop over the gpio pins and turn them on and off
        # with the pwm feature of lightshowpi
        for light in range(int(len(lights) / 2)):
            if cm.hardware.is_pin_pwm[light]:
                for brightness in range(0, pwm_max):
                    # fade in
                    light_on(lights[light], False, float(brightness) / pwm_max)
                    light_on(lights2[light], False, float(brightness) / pwm_max)
                    time.sleep(.1 / pwm_max)

                for brightness in range(pwm_max - 1, -1, -1):
                    # fade out
                    light_on(lights[light], False, float(brightness) / pwm_max)
                    light_on(lights2[light], False, float(brightness) / pwm_max)
                    time.sleep(.1 / pwm_max)
            else:
                light_on(lights[light], False, 1.0)
                light_on(lights2[light], False, 1.0)
                time.sleep(.5)
                light_off(lights[light], False, 0.0)
                light_off(lights2[light], False, 0.0)

        for light in range(int(len(lights) / 2) - 1, -1, -1):
            if cm.hardware.is_pin_pwm[light]:
                for brightness in range(0, pwm_max):
                    # fade in
                    light_on(lights[light], False, float(brightness) / pwm_max)
                    light_on(lights2[light], False, float(brightness) / pwm_max)
                    time.sleep(.1 / pwm_max)

                for brightness in range(pwm_max - 1, -1, -1):
                    # fade out
                    light_on(lights[light], False, float(brightness) / pwm_max)
                    light_on(lights2[light], False, float(brightness) / pwm_max)
                    time.sleep(.1 / pwm_max)
            else:
                light_on(lights[light], False, 1.0)
                light_on(lights2[light], False, 1.0)
                time.sleep(.5)
                light_off(lights[light], False, 0.0)
                light_off(lights2[light], False, 0.0)


def step():
    """Test fading in and out for each light configured in pwm mode"""
    print "Press <CTRL>-C to stop"
    while True:
        for light in lights:
            print "channel %s " % light
            for brightness in range(0, cm.hardware.pwm_range):
                # fade in
                light_on(light, False, float(brightness) / cm.hardware.pwm_range)
                time.sleep(sleep / cm.hardware.pwm_range)

        for light in reversed(lights):
            print "channel %s " % light
            for brightness in range(cm.hardware.pwm_range - 1, -1, -1):
                # fade out
                if cm.hardware.is_pin_pwm[light]:
                    light_on(light, False, float(brightness) / cm.hardware.pwm_range)
                else:
                    light_off(light, False, 0)
                time.sleep(sleep / cm.hardware.pwm_range)


def test():
    model, header = Platform.get_model()

    print "We are going to do some basic tests to make sure"
    print "your hardware is working as expected."
    print "Raspberry Pi %s" % model
    print "You have %s channels defined" % str(cm.hardware.gpio_len)
    print "They are using gpio pins %s" % ", ".join(map(str, cm.hardware.gpio_pins))
    print "You have configured your relays as active %s" % (
        "low" if cm.hardware.active_low_mode else "high")
    print "pin_modes are %s " % ", ".join(cm.hardware.pin_modes)
    print "custom_channel_mapping %s being used" % ("is" if ccm else "is not")

    if ccm:
        print "[%s]" % ", ".join(map(str, cm.audio_processing.custom_channel_mapping))

    print "\nFirst we are going to flash each light in order to see if they are all working"

    raw_input("Press Enter to continue....")

    flash(True)

    print "If everything went correctly you should have seen each of your channels"
    print "flash one at a time in order of assignment."

    while True:
        answer = raw_input("Did you see all channels flash in order? (yes/no) ").lower()
        yes = ['yes', 'y', 'yep', 'ja', 'si', 'oui']
        no = ['no', 'n', 'nope', 'nein', 'non']

        if answer in yes or answer in no:
            if answer in yes:
                print "Great, your basic config is ready for you to start with\n\n"

                sys.exit(1)

            if answer in no:
                print "Lets make sure you're using the correct gpio pins"
                print "Here is what the %s header looks like\n" % model
                print header
                print
                print "Make sure you are using the correct pins as listed above"

                if ccm:
                    print "Disable custom channel mapping to help with debugging your config"

                print "After you have made these corrections please rerun this test\n\n"

                sys.exit(1)

        print "Please answer yes or no"


# def main():
# """main"""
# hc.initialize()
# hc.network.unset_playing()
#
#     if args.test:
#         test()
#         return
#
#     if args.cleanup:
#         clean_up()
#
#     elif args.lights_off:
#         for light in lights:
#             light_off(light, False, 0.0)
#
#     elif args.lights_on:
#         for light in lights:
#             light_on(light, False, 1.0)
#
#     elif args.fade:
#         fade()
#
#     elif args.flash:
#         flash()
#
#     elif args.random_pattern:
#         random_pattern()
#
#     elif args.cylon:
#         cylon()
#
#     elif args.dance:
#         dance()
#
#     elif args.step:
#         step()
#
#     else:
#         parser.print_help()


def main():
    """main"""
    hc.initialize()
    hc.network.unset_playing()

    if args.test:
        test()
        return

    if state == "cleanup":
        hc.clean_up()

    elif state == "off":
        if len(lights) != cm.hardware.gpio_len:
            for light in lights:
                light_off(light)
        else:
            hc.turn_off_lights(use_always_onoff=True)

    elif state == "on":
        if len(lights) != cm.hardware.gpio_len:
            for light in lights:
                light_on(light)
        else:
            hc.turn_on_lights(use_always_onoff=True)

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
    hc = Hardware()

    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

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
                        help='turn off, on, flash, fade, random_pattern, cylon, '
                             'dance, step or cleanup')
    parser.add_argument('--test', action="store_true",
                        help='Run a basic hardware test')

    parser.add_argument('--light', default='-1',
                        help='the lights to act on (comma delimited list), -1 for all lights')
    parser.add_argument('--sleep', default=0.5,
                        help='how long to sleep between flashing or fading a light')
    parser.add_argument('--flashes', default=2,
                        help='the number of times to flash or fade each light')
    parser.add_argument('--lights_in_group', default=1,
                        help='number of light in a group')
    parser.add_argument('--pwm_speed', default=0.5,
                        help='time in seconds to full on or off')

    args = parser.parse_args()
    state = args.state
    sleep = float(args.sleep)

    flashes = int(args.flashes)
    lights_per_group = int(args.lights_in_group)
    pwm_speed = float(args.pwm_speed)
    # use custom_channel_mapping if defined.
    ccm = False
    lights = [int(lit) for lit in args.light.split(',')]

    if -1 in lights:
        lights = range(0, cm.hardware.gpio_len)

        if cm.audio_processing.custom_channel_mapping != 0 and len(
                cm.audio_processing.custom_channel_mapping) == cm.hardware.gpio_len:
            ccm = True
            cc = [i - 1 for i in cm.audio_processing.custom_channel_mapping]
            ccm_map = dict()

            for lit in lights:
                ccm_map[lit] = [idx for idx, pin_num in enumerate(cc) if pin_num == lit]

            if len(lights) == cm.hardware.gpio_len:
                lights = range(max(cm.audio_processing.custom_channel_mapping))

    if state == "random_pattern":
        exit_event = threading.Event()

    main()

