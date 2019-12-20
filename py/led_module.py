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
import serial
import time

import bibliopixel.colors as colors
import bibliopixel.util.image as image
import bibliopixel.layout.font as font

from bibliopixel.layout.strip import *
from bibliopixel.layout.matrix import *
from bibliopixel.layout.geometry.rotation import *
from bibliopixel.util import log,util
from PIL import Image, ImageSequence, ImageChops, ImageEnhance

from bibliopixel.drivers.ledtype import *
from bibliopixel.drivers.driver_base import *
from bibliopixel.drivers.serial import Serial
from bibliopixel.drivers.serial.devices import Devices
from bibliopixel.drivers.SPI import SPI
from driver_sacn import DriverSACN
from led_color_maps import lspi_color_maps

#log.set_log_level(log.INFO)
log.set_log_level(log.WARNING)
#log.set_log_level(log.DEBUG)

color_map = [list(colors.hue2rgb(c)) for c in range(256)]
scale = colors.color_scale
int_map = [colors.Green for g in range(0, 80)] + \
          [colors.Yellow for y in range(80, 160)] + \
          [colors.Red for r in range(160, 256)]


class Led(object):
    """wrapper module for Bibliopixel for use with lightshowpi"""

    def __init__(self, led_config, serpentine=True, rotation=Rotation.ROTATE_90, vert_flip=True):
        self.led_config = led_config
        self.serpentine = serpentine
        self.rotation = rotation
        self.rotation_180 = rotation + 180
        if self.rotation_180 >= 360:
            self.rotation_180 = self.rotation_180 - 360
        self.vert_flip = vert_flip
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
            if self.led_config.custom_per_channel:
                self.led_count = sum(self.led_config.custom_per_channel)
            else:
                self.led_count = self.led_config.led_count * self.led_config.per_channel

        elif self.led_config.led_configuration == "MATRIX":
            self.led_count = self.led_config.matrix_width * self.led_config.matrix_height

        if self.led_config.led_connection == "SPI":
            self.spi_setup()
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

        self.led.set_brightness(int(self.max_brightness * 255))
#        atexit.register(self.exit_function)

    def exit_function(self):
        if not self.all_set_on:
            self.all_leds_off()

    def spi_setup(self):
        self.driver = SPI(ledtype=self.led_config.strip_type,
                             num=self.led_count,
                             spi_interface='PYDEV',
                             c_order=self.channel_order)

    def serial_setup(self):

        if len(self.led_config.device_address):
            packet = util.generate_header(4, 0)
            com = serial.Serial(self.led_config.device_address, baudrate=self.led_config.baud_rate, timeout=0.2)
            com.write(packet)
            com.read(1)
            time.sleep(1.6)
 
        strip_type = getattr(LEDTYPE, self.led_config.strip_type)
        self.driver = Serial(ledtype=strip_type,
                                   num=self.led_count,
                                   dev=self.led_config.device_address,
                                   c_order=self.channel_order,
                                   restart_timeout=5,
                                   device_id=self.led_config.device_id,
                                   hardwareID=self.led_config.hardware_id,
                                   baudrate=self.led_config.baud_rate)

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
        self.last_type = ""
        self.led = LEDMatrix(self.driver,
                             width=self.led_config.matrix_width,
                             height=self.led_config.matrix_height,
                             serpentine=self.serpentine,
                             vert_flip=self.vert_flip,
                             rotation=self.rotation,
                             threadedUpdate=self.led_config.multiprocess)

        image_path = self.led_config.image_path
        for frame in ImageSequence.Iterator(Image.open(image_path)):
            rgba = Image.new("RGBA", frame.size)
            rgba.paste(frame)
            self.images.append(rgba)
        self.base_image = Image.new("RGBA", self.images[0].size)

        self.drops = [[0 for _ in range(self.led_config.matrix_height)] for _ in range(self.led_config.matrix_width)]

        self._len = (self.led_config.matrix_width * 2) + (self.led_config.matrix_height * 2) - 2
        self._step = 1
        self._bstep = 0
        midx = int(self.led_config.matrix_height / 2)
        if float(midx) == (self.led_config.matrix_height / 2):
            # even number, two center px 
            self.midxa = midx
            self.midxb = midx - 1
        else:
            # odd number, one center px 
            self.midxa = midx
            self.midxb = midx
        midy = int(self.led_config.matrix_width / 2)
        if float(midy) == (self.led_config.matrix_width / 2):
            # even number, two center px 
            self.midya = midy
            self.midyb = midy - 1
        else:
            # odd number, one center px 
            self.midya = midy
            self.midyb = midy

    def all_leds_off(self):
        self.leds = numpy.array([0 for _ in range(self.led_config.led_count)])
        self.led.all_off()
        self.led.push_to_driver()

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

        self.led.push_to_driver()

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
            if self.led_config.custom_per_channel:
                sled = sum(self.led_config.custom_per_channel[0:pin])
                midl = int(self.led_config.custom_per_channel[pin] / 2)
                lastl = self.led_config.custom_per_channel[pin] - 1
            else:
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

            elif self.pattern_color_map in lspi_color_maps.map.keys():
                rgb = scale(lspi_color_maps.map[self.pattern_color_map][255 - brightness], brightness)
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

        self.led.push_to_driver()
        self.update_skip = self.skip

    def mmcm(self,p_type):
        if self.last_type == p_type:
            return
        self.last_type = p_type
        if p_type == 'BANNER':
            self.led.coord_map = make_matrix_coord_map( self.led_config.matrix_width, self.led_config.matrix_height, serpentine=self.serpentine, rotation=self.rotation_180, y_flip=self.vert_flip)
        else:
            self.led.coord_map = make_matrix_coord_map( self.led_config.matrix_width, self.led_config.matrix_height, serpentine=True, rotation=self.rotation, y_flip=self.vert_flip)
            
         
    def write_matrix(self, pin_list):
        if self.update_skip != 0:
            self.update_skip -= 1
            if self.update_skip >= 0:
                return

        if len(self.led_config.matrix_pattern_type) == 1:
            self.p_type = self.led_config.matrix_pattern_type[0]
        else:
            for pin in range(len(pin_list)):
                self.beats += pin_list[pin] * (len(pin_list) / (pin + 1)) * 0.002
            if self.beats > self.led_config.beats and self._bstep == 0:
                self._bstep = 0 
                self.beats = 0
                self.p_num += 1
                if self.p_num >= len(self.led_config.matrix_pattern_type):
                    self.p_num = 0
            self.p_type = self.led_config.matrix_pattern_type[self.p_num]

        self.mmcm(self.p_type)
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
            for pin in range(len(pin_list)):
                if pin_list[pin] > 0.55:
                    complete_image = ImageChops.add_modulo(complete_image, ImageEnhance.Brightness(
                        self.images[pin]).enhance(pin_list[pin]))

            image.showImage(self.led, "",
                            ImageEnhance.Brightness(complete_image).enhance(self.max_brightness * 0.5))

        elif self.p_type == 'PINWHEEL':
            amt = 0

            for pin in range(len(pin_list)):
                amt += pin_list[pin] * (len(pin_list) / (pin + 1)) * 0.25
            amt = int(amt)

            pos = 0
            for x in range(h):
                c = colors.hue_helper(pos, self._len, self._step)
                self.led.drawLine(self.midxa, self.midya, x, 0, c)
                pos += 1

            for y in range(w):
                c = colors.hue_helper(pos, self._len, self._step)
                self.led.drawLine(self.midxb, self.midyb, h - 1, y, c)
                pos += 1

            for x in range(h - 1, -1, -1):
                c = colors.hue_helper(pos, self._len, self._step)
                self.led.drawLine(self.midxb, self.midyb, x, w - 1, c)
                pos += 1

            for y in range(w - 1, -1, -1):
                c = colors.hue_helper(pos, self._len, self._step)
                self.led.drawLine(self.midxa, self.midya, 0, y, c)
                pos += 1

            self._step += amt
            if(self._step >= 255):
                self._step = 0

        elif self.p_type == 'CBARS':
            for y in range(w):
                level = pin_list[int((y / float(w)) * float(self.led_config.led_channel_count))]
                brightness = int(255 * level)
                rgb = scale(color_map[brightness], brightness)
                mlvl = int(level * self.midxa)
                self.led.drawLine(self.midxa - mlvl, y,self.midxb + mlvl, y,rgb)

        elif self.p_type == 'CIRCLES':
            for pin in range(self.led_config.led_channel_count):
                rgb = self.rgb[pin]
                c = scale(rgb,int((pin_list[pin]) * 255))
                self.led.drawCircle(self.midxa,self.midyb,int(pin * ((w / 2) / self.led_config.led_channel_count)),c)

        elif self.p_type == 'BANNER':
            rgb = self.rgb[list(pin_list).index(max(list(pin_list)))] 
# fit 4 characters into width
            text = self.led_config.banner_text[int(self._bstep):int(self._bstep)+4]
# fonts : 6x4 8x6 16x8
            self.led.drawText(text, x = 1, y = 1, color = rgb, bg = colors.Off, font='6x4', font_scale = 1)
# scroll speed 0.1
            self._bstep += 0.1
# scroll with beats
#            self._bstep += (pin_list[0] * 0.2) + (pin_list[1] * 0.1)
            if(self._bstep >= len(self.led_config.banner_text)):
                self._bstep = 0

        self.led.push_to_driver()
        self.update_skip = self.skip
