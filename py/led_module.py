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
        self.p_num = 0
        self.beats = 0
        self.write_all = None
        self.all_set_on = False
        self.test = False

        self.leds = numpy.array([0 for _ in range(self.led_config.led_count)])

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
            self.led = LEDStrip(self.driver,threadedUpdate=self.led_config.multiprocess)
            self.write_all = self.write_full
        elif self.led_config.led_configuration == "MATRIX":
            self.matrix_setup()
            self.write_all = self.write_matrix

        if self.pattern_color_map == 'MAP1A':
            color_map[255] = self.pattern_color
            self.pattern_color_map = 'MAP1'
        if self.pattern_color_map == 'MAP2A':
            color_map[0] = self.pattern_color
            self.pattern_color_map = 'MAP2'

        self.led.setMasterBrightness(int(self.max_brightness * 255))
#        atexit.register(self.exit_function)

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
                             rotation=MatrixRotation.ROTATE_90,
                             threadedUpdate=self.led_config.multiprocess)

        image_path = self.led_config.image_path
        for frame in ImageSequence.Iterator(Image.open(image_path)):
            rgba = Image.new("RGBA", frame.size)
            rgba.paste(frame)
            self.images.append(rgba)
        self.base_image = Image.new("RGBA", self.images[0].size)

        self.drops = [[0 for _ in range(self.led_config.matrix_height)] for _ in range(self.led_config.matrix_width)]

        self._cY = int(self.led_config.matrix_width / 2)
        self._cX = int(self.led_config.matrix_height / 2)
        self._len = (self.led_config.matrix_width * 2) + (self.led_config.matrix_height * 2) - 2
        self._step = 1

    def all_leds_off(self):
        self.leds = numpy.array([0 for _ in range(self.led_config.led_count)])
        self.led.all_off()
        self.led.update()

    def all_leds_on(self):
        self.leds = numpy.array([1 for _ in range(self.led_config.led_count)])
        self.update_skip = 0
        self.write_all(self.leds)

    def write_leds(self, pin, value):
        self.leds[pin] = value
        self.update_skip = 0
        self.write_all(self.leds)

    def write(self, pin, color):

        self.led.set(pin, scale(color_map[color], color))

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

            elif self.pattern_color_map == 'FREQ1A':
                if brightness < 255:
                    rgb = self.rgb[pin]
                else:
                    rgb = self.pattern_color
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

        if len(self.led_config.matrix_pattern_type) == 1:
            self.p_type = self.led_config.matrix_pattern_type[0]
        else:
            for pin in xrange(len(pin_list)):
                self.beats += pin_list[pin] * (len(pin_list) / (pin + 1)) * 0.002
            if self.beats > self.led_config.beats:
            	self.beats = 0
                self.p_num += 1
                if self.p_num >= len(self.led_config.matrix_pattern_type):
                    self.p_num = 0
            self.p_type = self.led_config.matrix_pattern_type[self.p_num]

        self.led.all_off()

        h = self.led_config.matrix_height
        w = self.led_config.matrix_width

        if self.p_type == 'SBARS':
            for y in range(h):
                y_ind = int((float(len(pin_list)) / h) * y)
                for x_cord in range(int(pin_list[y_ind] * float(w))):
                    rgb = color_map[int( 255.0 * float(x_cord) / float(w) )]
                    self.led.set(y_ind, x_cord, rgb)

        if self.p_type == 'MBARS':
            norm_arr = [int(x * 255) for x in pin_list]
            self.drops.append(norm_arr)
            for y_cord in range(w):
                for x in range(h):
                    x_ind = int((float(len(pin_list)) / h) * x)
                    if self.drops[y_cord][x_ind] > 64:
                        rgb = scale(color_map[255 - self.drops[y_cord][x_ind]],
                                    int(self.drops[y_cord][x_ind] * 0.5))
                        self.led.set(x, w - 1 - y_cord, rgb)
            del self.drops[0]

        elif self.p_type == 'IMAGE':
            complete_image = self.base_image
            for pin in xrange(len(pin_list)):
                if pin_list[pin] > 0.55:
                    complete_image = ImageChops.add_modulo(complete_image, ImageEnhance.Brightness(
                        self.images[pin]).enhance(pin_list[pin]))

            image.showImage(self.led, "",
                            ImageEnhance.Brightness(complete_image).enhance(self.max_brightness * 0.5))

        elif self.p_type == 'PINWHEEL':
            amt = 0

            for pin in xrange(len(pin_list)):
                amt += pin_list[pin] * (len(pin_list) / (pin + 1)) * 0.25
            amt = int(amt)

            pos = 0
            for x in range(h):
                c = colors.hue_helper(pos, self._len, self._step)
                self.led.drawLine(self._cX, self._cY, x, 0, c)
                pos += 1

            for y in range(w):
                c = colors.hue_helper(pos, self._len, self._step)
                self.led.drawLine(self._cX, self._cY, h - 1, y, c)
                pos += 1

            for x in range(h - 1, -1, -1):
                c = colors.hue_helper(pos, self._len, self._step)
                self.led.drawLine(self._cX, self._cY, x, w - 1, c)
                pos += 1

            for y in range(w - 1, -1, -1):
                c = colors.hue_helper(pos, self._len, self._step)
                self.led.drawLine(self._cX, self._cY, 0, y, c)
                pos += 1

            self._step += amt
            if(self._step >= 255):
                self._step = 0

        elif self.p_type == 'CBARS':
            midl = int(h / 2)
            for y in range(w):
                level = pin_list[int((y / float(w)) * float(self.led_config.led_channel_count))]
                brightness = int(255 * level)
                rgb = scale(color_map[brightness], brightness)
                mlvl = int(level * midl)
                self.led.drawLine(midl - mlvl, y,midl + mlvl, y,rgb)

        elif self.p_type == 'CIRCLES':
            for pin in xrange(len(pin_list)):
                rgb = self.rgb[pin]
                c = scale(rgb,int((pin_list[pin]) * 255))
                self.led.drawCircle(self._cX,self._cY,pin,c)

        self.led.update()
        self.update_skip = self.skip
