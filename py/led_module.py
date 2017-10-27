#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Tom Enos (tomslick.ca@gmail.com)
# Author: Ken B


"""wrapper module for Bibliopixel for use with lightshowpi

"""

import atexit
import importlib
import math
import numpy

import bibliopixel.colors as colors
import bibliopixel.image as image

from bibliopixel.led import *
from bibliopixel.drivers.driver_base import *
from lightshow_serial_driver import *
from bibliopixel import log
from PIL import Image, ImageSequence, ImageChops, ImageEnhance

from driver_sacn import DriverSACN

log.setLogLevel(log.WARNING)
# log.setLogLevel(log.DEBUG)

color_map = [list(colors.hue2rgb(c)) for c in range(256)]
scale = colors.color_scale
int_map = [colors.Green for g in range(0, 80)] + \
          [colors.Yellow for y in range(80, 160)] + \
          [colors.Red for r in range(160, 256)]


class Led(object):
    """wrapper module for Bibliopixel for use with lightshowpi"""

    def __init__(self, led_config):
        self.led_config = led_config
        self.driver = None
        self.drops = None
        self.images = None
        self.p_type = None
        self.write_all = None
        self.all_set_on = False
        self.test = False

        self.per_channel = self.led_config.per_channel
        self.pattern_color = self.led_config.pattern_color
        self.pattern_color_map = self.led_config.pattern_color_map

        self.channel_order = getattr(ChannelOrder, self.led_config.channel_order)
        self.last = self.led_config.led_count - 1
        self.rgb = list()
        for x in range(self.led_config.led_count):
            self.rgb.append(color_map[int((float(x) / (self.last + 1)) * 255)])
        self.skip = self.led_config.update_throttle
        self.update_skip = self.skip
        self.max_brightness = self.led_config.max_brightness / 100.0

        if self.led_config.led_configuration == "STRIP":
            self.led_count = self.led_config.led_count * self.led_config.per_channel
        elif self.led_config.led_configuration == "MATRIX":
            self.led_count = self.led_config.matrix_width * self.led_config.matrix_height

        if self.led_config.led_connection == "SPI":
            self.strip_setup()
        elif self.led_config.led_connection == "SERIAL":
            self.serial_setup()
        elif self.led_config.led_connection == "SACN":
            self.sacn_setup()

        if self.led_config.led_configuration == "STRIP":
            self.led = LEDStrip(self.driver)
            self.write_all = self.write_full
        elif self.led_config.led_configuration == "MATRIX":
            self.matrix_setup()
            self.write_all = self.write_matrix

        self.led.setMasterBrightness(int(self.max_brightness * 255))
        atexit.register(self.exit_function)

    def exit_function(self):
        if not self.all_set_on:
            self.all_leds_off()

    def strip_setup(self):
        main_driver = importlib.import_module("bibliopixel.drivers." + self.led_config.strip_type)
        driver = getattr(main_driver, "Driver" + self.led_config.strip_type)
        self.driver = driver(num=self.led_count,
                             c_order=self.channel_order,
                             use_py_spi=True)

    def serial_setup(self):
        strip_type = getattr(LEDTYPE, self.led_config.strip_type)
        self.driver = DriverSerial(type=strip_type,
                                   num=self.led_count,
                                   dev=self.led_config.device_address,
                                   c_order=self.channel_order,
                                   restart_timeout=5,
                                   deviceID=self.led_config.device_id,
                                   hardwareID=self.led_config.hardware_id,
                                   baud_rate=self.led_config.baud_rate)

    def sacn_setup(self):
        self.driver = DriverSACN(num=self.led_count,
                                 host=self.led_config.sacn_address,
                                 port=self.led_config.sacn_port,
                                 universe = self.led_config.universe_start,
                                 universe_boundary=self.led_config.universe_boundary,
                                 broadcast=self.led_config.sacn_broadcast)

    def matrix_setup(self):
        self.images = []
        self.p_type = self.led_config.matrix_pattern_type
        self.led = LEDMatrix(self.driver,
                             width=self.led_config.matrix_width,
                             height=self.led_config.matrix_height,
                             serpentine=True,
                             vert_flip=True,
                             threadedUpdate=False)

        image_path = self.led_config.image_path
        for frame in ImageSequence.Iterator(Image.open(image_path)):
            rgba = Image.new("RGBA", frame.size)
            rgba.paste(frame)
            self.images.append(rgba)

        self.drops = [[0 for _ in range(self.led_config.led_count)] for _ in range(self.led_config.matrix_height)]

    def all_leds_off(self):
        self.led.all_off()
        self.led.update()

    def all_leds_on(self):
        leds = numpy.array([1 for _ in range(self.led_config.led_count)])
        self.update_skip = 0
        self.write_all(leds)

    def write(self, pin, color):
        if self.led_config.led_configuration == "SERIALMATRIX":
            return

        self.led.set(pin, scale(color_map[color], color))

        if pin == self.last or self.test:
            self.led.update()

    def write_full(self, pin_list):
        if self.update_skip != 0:
            self.update_skip -= 1
            if self.update_skip >= 0:
                return

        self.led.all_off()

        brightnesses = pin_list * 255
        brightnesses = brightnesses.astype(int)
        half_channels = self.led_config.per_channel / 2
        midl = int(half_channels)
        pin = 0

        for level, brightness in zip(pin_list, brightnesses):
            sled = pin * self.per_channel

            if self.pattern_color_map == 'MONO':
                rgb = (int(level * self.pattern_color[0]),
                       int(level * self.pattern_color[1]),
                       int(level * self.pattern_color[2]))

            elif self.pattern_color_map == 'FREQ1':
                # rgb = color_map[int((float(pin) / (self.last + 1)) * 255)]
                rgb = self.rgb[pin]
                rgb = (int(rgb[0] * level), int(rgb[1] * level), int(rgb[2] * level))

            elif self.pattern_color_map == 'MAP1':
                rgb = scale(color_map[brightness], brightness)

            elif self.pattern_color_map == 'MAP2':
                rgb = scale(color_map[255 - brightness], brightness)

            else:
                rgb = (brightness, brightness, brightness)

            if self.led_config.pattern_type == 'CBARS':
                mlvl = int(level * midl)
                self.led.fill(rgb, sled + midl - mlvl, sled + midl + mlvl)

            elif self.led_config.pattern_type == 'FULL':
                self.led.fill(rgb, sled, sled + self.led_config.per_channel - 1)

            elif self.led_config.pattern_type == 'LBARS':
                midl = int(half_channels) + sled
                for gled in range(0, int((half_channels) * level)):
                    self.led.set(midl + gled, int_map[int((float(gled) / half_channels) * 255)])
                    self.led.set(midl - gled, int_map[int((float(gled) / half_channels) * 255)])

            pin += 1

        self.led.update()
        self.update_skip = self.skip

    def write_matrix(self, pin_list):
        if self.update_skip != 0:
            self.update_skip -= 1
            if self.update_skip >= 0:
                return

        self.led.all_off()

        if self.p_type == 'SBARS':
            for y in range(self.led_config.matrix_width):
                y_ind = int(((self.last + 1.0) / self.led_config.matrix_width) * y)
                for x_cord in range(int(pin_list[y_ind] * float(self.led_config.matrix_height))):
                    rgb = color_map[int( 255.0 * float(x_cord) / float(self.led_config.matrix_height) )]
                    self.led.set(x_cord, y_ind, rgb)
        if self.p_type == 'MBARS':
            norm_arr = [int(x * 255) for x in pin_list]
            self.drops.append(norm_arr)
            for y_cord in range(self.led_config.matrix_height):
                for x in range(self.led_config.matrix_width):
                    x_ind = int(((self.last + 1.0) / self.led_config.matrix_width) * x)
                    if self.drops[y_cord][x_ind] > 64:
                        rgb = scale(color_map[255 - self.drops[y_cord][x_ind]],
                                    int(self.drops[y_cord][x_ind] * 0.5))
                        self.led.set(x, y_cord, rgb)
            del self.drops[0]
        elif self.p_type == 'IMAGE':
            complete_image = Image.new("RGBA", self.images[0].size)
            for pin in xrange(len(pin_list)):
                if pin_list[pin] > 0.25:
                    complete_image = ImageChops.add_modulo(complete_image, ImageEnhance.Brightness(
                        self.images[pin]).enhance(pin_list[pin]))

            image.showImage(self.led, "",
                            ImageEnhance.Brightness(complete_image).enhance(self.max_brightness * 0.5))

        self.led.update()
        self.update_skip = self.skip
