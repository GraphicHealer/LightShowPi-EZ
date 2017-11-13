#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Todd Giles (todd@lightshowpi.org)
# Author: Tom Enos (tomslick.ca@gmail.com)
#

"""Configuration management for the lightshow.

Configuration files are all located in the <homedir>/config directory. This file contains tools to
manage these configuration files.
"""

import ConfigParser
import ast
import csv
import datetime
import fcntl
import logging
import os
import os.path
import sys
import warnings
import json
import shlex
from collections import defaultdict

# The home directory and configuration directory for the application.
HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")

if not HOME_DIR:
    print("Need to setup SYNCHRONIZED_LIGHTS_HOME environment variable, "
          "see readme")
    sys.exit()

CONFIG_DIR = HOME_DIR + '/config'
LOG_DIR = HOME_DIR + '/logs'


def _as_list(list_str, delimiter=','):
    """Return a list of items from a delimited string (after stripping whitespace).

    :param list_str: string to turn into a list
    :type list_str: str

    :param delimiter: split the string on this
    :type delimiter: str

    :return: string converted to a list
    :rtype: list
    """
    return [str.strip(item).rstrip() for item in list_str.split(delimiter)]


class Configuration(object):
    """Configuration management for the lightshow.

    Configuration files are all located in the <homedir>/config directory. This file contains tools
    to manage these configuration files.
    """

    def __init__(self, sms=False):
        self.gpio_len = None
        self.playlist = None
        self.playlist_path = None

        # path and file locations
        self.home_dir = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
        self.config_dir = self.home_dir + "/config/"
        self.log_dir = self.home_dir + "/logs/"
        self.state_file = self.config_dir + "state.cfg"

        # ConfigParsers
        self.config = ConfigParser.RawConfigParser(allow_no_value=True)
        self.state = ConfigParser.RawConfigParser()

        self.state_section = 'do_not_modify'

        self.load_config()

        # Ensure state file has been created
        if not os.path.isfile(self.state_file):
            open(self.state_file, 'w').close()

        self.load_state()

        # synchronized_lights and check_sms both use configuration_manager
        # let them only use the parts they need, saving a little memory and time.
        if not sms:
            self.hardware = None
            self.lightshow = None
            self.audio_processing = None
            self.network = None
            self.fm = None
            self.terminal = None
            self.led = None
            self.configs = None

            self.set_hardware()
            self.set_fm()
            self.set_configs()
            self.set_lightshow()
            self.set_audio_processing()
            self.set_network()
            self.set_terminal()
        else:
            self.sms = None
            self.who_can = dict()
            self.throttle_state = dict()
            self.set_sms()

    def load_config(self):
        """Load config files into ConfigParser instance"""
        self.config.readfp(open(self.config_dir + 'defaults.cfg'))

        overrides = list()
        overrides.append(self.config_dir + "overrides.cfg")
        self.config.read(overrides)

    # handle the program state / next 3 methods
    def load_state(self):
        """Force the state to be reloaded form disk."""
        with open(self.state_file) as state_fp:
            fcntl.lockf(state_fp, fcntl.LOCK_SH)
            self.state.readfp(state_fp, self.state_file)
            fcntl.lockf(state_fp, fcntl.LOCK_UN)

    def get_state(self, name, default=""):
        """
        Get application state

        Return the value of a specific application state variable, or the specified
        default if not able to load it from the state file

        :param name: option to load from state file
        :type name: str

        :param default: return if not able to load option from state file
        :type default: str

        :return: the current state
        :rtype: str
        """
        try:
            return self.state.get(self.state_section, name)
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return default

    def update_state(self, name, value):
        """Update the application state (name / value pair)

        :param name: option name to update
        :type name: str

        :param value: value to update option name to
        :type value: str
        """
        value = str(value)
        logging.info('Updating application state {%s: %s}', name, value)

        if not self.state.has_section(self.state_section):
            self.state.add_section(self.state_section)

        self.state.set(self.state_section, name, value)

        with open(self.state_file, 'wb') as state_fp:
            fcntl.lockf(state_fp, fcntl.LOCK_EX)
            self.state.write(state_fp)
            fcntl.lockf(state_fp, fcntl.LOCK_UN)

    def set_configs(self):

        configs = dict()

        if self.config.get('configs', 'led_config') == "":
            configs["led"] = list()
        else:
            configs["led"] = self.config.get('configs', 'led_config').split(",")

        configs["led_multiprocess"] = self.config.getboolean('configs','led_multiprocess')
            
        self.configs = Section(configs)

    def set_hardware(self):
        """
        Retrieves the hardware configuration parsing it from the Config Parser as necessary.
        """
        hrdwr = dict()
        devices = dict()
        try:
            devices = json.loads(self.config.get('hardware', 'devices'))
        except Exception as error:
            logging.error("devices not defined or not in JSON format." + str(error))
        hrdwr["devices"] = devices

        for device_type, settings in hrdwr["devices"].iteritems():
            for count in range(len(settings)):
                for k, v in settings[count].iteritems():
                    settings[count][k] = v if not isinstance(v, str) else int(v, 16)

        g_pins = self.config.get('hardware', 'gpio_pins')
        try:
            hrdwr["gpio_pins"] = map(int, g_pins.split(","))
        except (AttributeError, ValueError):
            hrdwr["gpio_pins"] = list()

        self.gpio_len = len(hrdwr["gpio_pins"])

        hrdwr["gpio_len"] = len(hrdwr["gpio_pins"])
        hrdwr["physical_gpio_len"] = hrdwr["gpio_len"]

        temp = self.config.get('hardware', 'pin_modes').split(",")
        if len(temp) != 1:
            hrdwr["pin_modes"] = temp
        else:
            hrdwr["pin_modes"] = [temp[0] for _ in range(self.gpio_len)]

        hrdwr["is_pin_pwm"] = [True if pin == "pwm" else False for pin in hrdwr["pin_modes"]]

        hrdwr["pwm_range"] = int(self.config.get('hardware', 'pwm_range'))
        hrdwr["active_low_mode"] = self.config.getboolean('hardware', 'active_low_mode')
        hrdwr["piglow"] = self.config.getboolean('hardware', 'piglow')

        self.hardware = Section(hrdwr)

    def set_terminal(self):
        """
        Retrieves the terminal configuration parsing it from the Config Parser as necessary.
        """
        term = dict()
        term["enabled"] = self.config.getboolean('terminal', 'enabled')
        self.terminal = Section(term)

    def set_led(self, config_file):
        """
        Retrieves the led configuration parsing it from the Config Parser as necessary.
        """

        self.led_config = ConfigParser.RawConfigParser(allow_no_value=True)
        self.led_config.readfp(open(self.config_dir + config_file))

        led = dict()

        lc = self.led_config.get('led', 'led_configuration').upper()
        lconn = self.led_config.get('led', 'led_connection').upper()
        st = self.led_config.get('led', 'strip_type').upper()
        sst = ["APA102", "LPD8806", "WS2801", "WS2811", "WS2812",
               "WS2812B", "NEOPIXEL", "WS2811_400", "APA104",
               "TM1803", "TM1804", "TM1809", "UCS1903", "SM16716",
               "LPD1886", "P9813"]

        if lconn in ["SERIAL", "SPI", "SACN"]:
            led["led_configuration"] = lc
            led["led_connection"] = lconn
        else:
            led["led_configuration"] = None
            led["led_connection"] = None

        if st in sst[0:3] and lconn == "SPI":
            led["strip_type"] = st
        elif lconn in ["SERIAL"] and st in sst:
            led["strip_type"] = st
        else:
            led["strip_type"] = None

        led["enable_multicast"] = self.led_config.getboolean('led', 'enable_multicast')

        # if multicast is enabled setup broadcast flag and broadcast address
        # TODO: possibly need to manage broadcast address a little differently in future to handle more customization
        if led["enable_multicast"]:
            led["sacn_address"] = "239.255.0.1"
            led["sacn_broadcast"] = True
        else:
            led["sacn_address"] = self.led_config.get('led', 'sacn_address')
            led["sacn_broadcast"] = False
        
        led["sacn_port"] = self.led_config.getint('led', 'sacn_port')
        led["universe_boundary"] = self.led_config.getint('led', 'universe_boundary')
        led["universe_start"] = self.led_config.getint('led', 'universe_start')

        c_order = self.led_config.get('led', 'channel_order').upper()
        if c_order in ["RGB", "RBG", "GRB", "GBR", "BRG", "BGR"]:
            led["channel_order"] = c_order
        else:
            led["channel_order"] = "RGB"
        
        led["led_channel_configuration"] = self.led_config.get('led', 'led_channel_configuration').upper()

        led_count = self.led_config.getint('led', 'led_channel_count')
        if led["led_configuration"]:

            led["led_count"] = led_count
            gpio_len = self.hardware.get("gpio_len")

            if led["led_channel_configuration"] == "MIRROR":
                led["led_count"] = gpio_len
            
            elif led["led_channel_configuration"] == "LEDONLY":
                self.hardware.set_value("gpio_len", led_count)
                self.hardware.set_value("physical_gpio_len", 0) 
                
                if led_count > gpio_len:
                    gpio_pins = self.hardware.get("gpio_pins")
                    gpio_pins.extend([_ + 1000 for _ in range(led_count - gpio_len)])
                    self.hardware.set_value("gpio_pins", gpio_pins)

                    pin_modes = self.hardware.get("pin_modes")
                    pin_modes.extend(["pwm" for _ in range(led_count - gpio_len)])
                    self.hardware.set_value("pin_modes", pin_modes)

                    is_pin_pwm = self.hardware.get("is_pin_pwm")
                    is_pin_pwm.extend([True for _ in range(led_count - gpio_len)])
                    self.hardware.set_value("is_pin_pwm", is_pin_pwm)

            elif led["led_channel_configuration"] == "EXTEND":
                self.hardware.set_value("gpio_len", gpio_len + led_count)
                self.hardware.set_value("physical_gpio_len", gpio_len)

                gpio_pins = self.hardware.get("gpio_pins")
                gpio_pins.extend([_ + 1000 for _ in range(led_count)])
                self.hardware.set_value("gpio_pins", gpio_pins)

                pin_modes = self.hardware.get("pin_modes")
                pin_modes.extend(["pwm" for _ in range(led_count)])
                self.hardware.set_value("pin_modes", pin_modes)

                is_pin_pwm = self.hardware.get("is_pin_pwm")
                is_pin_pwm.extend([True for _ in range(led_count)])
                self.hardware.set_value("is_pin_pwm", is_pin_pwm)
        else:
            led["led_count"] = 0

        led["max_brightness"] = self.led_config.getint('led', 'max_brightness')
        led["per_channel"] = self.led_config.getint('led', 'per_channel')

        led["pattern_color_map"] = self.led_config.get('led', 'pattern_color_map').upper()
        led["pattern_color"] = map(int, self.led_config.get('led', 'pattern_color').split(","))
        led["pattern_type"] = self.led_config.get('led', 'pattern_type').upper()

        device_id = self.led_config.getint('led', 'device_id')
        if 0 <= device_id <= 255:
            led["device_id"] = device_id
        else:
            led["device_id"] = None

        led["device_address"] = self.led_config.get('led', 'device_address')
        led["hardware_id"] = self.led_config.get('led', 'hardware_id')
        if led["hardware_id"] == "":
            led["hardware_id"] = "1D50:60AB"
        led["baud_rate"] = self.led_config.getint('led', 'baud_rate')
        led["update_throttle"] = self.led_config.getint('led', 'update_throttle')

        led["matrix_width"] = self.led_config.getint('led', 'matrix_width')
        led["matrix_height"] = self.led_config.getint('led', 'matrix_height')
        led["matrix_pattern_type"] = self.led_config.get('led', 'matrix_pattern_type').upper()

        file_name = self.led_config.get('led', 'image_path').replace('$SYNCHRONIZED_LIGHTS_HOME',
                                                                 self.home_dir)
        if os.path.isfile(file_name):
            led["image_path"] = file_name
        else:
            led["image_path"] = self.home_dir + "/16xstar.gif"

        self.led = Section(led)

    def set_fm(self):
        """
        Retrieves the fm configuration parsing it from the Config Parser as necessary.
        """
        fm = dict()
        fm["enabled"] = self.config.getboolean('fm', 'fm')
        fm["frequency"] = self.config.get('fm', 'frequency')
        self.fm = Section(fm)

    def set_network(self):
        """
        Retrieves the network configuration parsing it from the Config Parser as necessary.
        """
        ntwrk = dict()
        ntwrk["networking"] = self.config.get('network', 'networking')
        ntwrk["port"] = self.config.getint('network', 'port')
        ntwrk["buffer"] = self.config.getint('network', 'buffer')

        if len(self.config.get('network', 'channels')) == 0:
            channels = [_ for _ in range(self.gpio_len)]
        else:
            channels = map(int, self.config.get('network', 'channels').split(","))

        temp = defaultdict()
        for channel in range(len(channels)):
            temp[channels[channel]] = channel

        ntwrk["channels"] = temp

        self.network = Section(ntwrk)

    def set_lightshow(self):
        """
        Retrieve the lightshow configuration loading and parsing it from a file as necessary.
        """
        lghtshw = dict()
        ls = 'lightshow'
        lghtshw["mode"] = self.config.get(ls, 'mode')
        lghtshw["use_fifo"] = self.config.getboolean(ls, 'use_fifo')
        lghtshw["fifo"] = "/tmp/audio"
        lghtshw["audio_in_card"] = self.config.get(ls, 'audio_in_card')
        lghtshw["audio_out_card"] = self.config.get(ls, 'audio_out_card')

        if lghtshw["use_fifo"]:
            lghtshw["audio_out_card"] = ""

        lghtshw["input_channels"] = self.config.getint(ls, 'input_channels')
        lghtshw["input_sample_rate"] = self.config.getint(ls, 'input_sample_rate')

        lghtshw["songname_command"] = self.config.get(ls, 'songname_command')

        command_string = self.config.get(ls, 'stream_command_string')
        lghtshw["stream_command_string"] = shlex.split(command_string)

        lghtshw["stream_song_delim"] = self.config.get(ls, 'stream_song_delim')
        lghtshw["stream_song_exit_count"] = self.config.getint(ls, 'stream_song_exit_count')

        playlist_path = self.config.get(ls, 'playlist_path')
        playlist_path = playlist_path.replace('$SYNCHRONIZED_LIGHTS_HOME', self.home_dir)
        if playlist_path:
            lghtshw["playlist_path"] = playlist_path
        else:
            lghtshw["playlist_path"] = "/home/pi/music/.playlist"

        lghtshw["randomize_playlist"] = self.config.getboolean(ls, 'randomize_playlist')

        on_c = "always_on_channels"
        lghtshw[on_c] = map(int, self.config.get(ls, on_c).split(","))
        off_c = "always_off_channels"
        lghtshw[off_c] = map(int, self.config.get(ls, off_c).split(","))
        ic = "invert_channels"
        lghtshw[ic] = map(int, self.config.get(ls, ic).split(","))

        # setup up preshow
        preshow = None
        preshow_configuration = self.config.get(ls, 'preshow_configuration')
        preshow_script = self.config.get(ls, 'preshow_script')

        if preshow_configuration and not preshow_script:
            try:
                preshow = json.loads(preshow_configuration)
            except (ValueError, TypeError) as error:
                msg = "Preshow_configuration not defined or not in JSON format."
                logging.error(msg + str(error))
        else:
            if os.path.isfile(preshow_script):
                preshow = preshow_script

        lghtshw['preshow'] = preshow

        # setup postshow
        postshow = None
        postshow_configuration = self.config.get(ls, 'postshow_configuration')
        postshow_script = self.config.get(ls, 'postshow_script')

        if postshow_configuration and not postshow_script:
            try:
                postshow = json.loads(postshow_configuration)
            except (ValueError, TypeError) as error:
                msg = "Postshow_configuration not defined or not in JSON format."
                logging.error(msg + str(error))
        else:
            if os.path.isfile(postshow_script):
                postshow = postshow_script

        lghtshw['postshow'] = postshow
        lghtshw["decay_factor"] = self.config.getfloat(ls, 'decay_factor')
        lghtshw["attenuate_pct"] = self.config.getfloat(ls, 'attenuate_pct')
        lghtshw["light_delay"] = self.config.getfloat(ls, 'light_delay')

        lghtshw["log_level"] = self.config.get(ls, 'log_level').upper()

        # Standard Deviation
        lghtshw["SD_low"] = self.config.getfloat(ls, 'SD_low')
        lghtshw["SD_high"] = self.config.getfloat(ls, 'SD_high')

        self.lightshow = Section(lghtshw)

    def set_audio_processing(self):
        """
        Retrieve the audio processing configuration loading and parsing it from a file as necessary.
        """
        audio_prcssng = dict()
        audio_prcssng["chunk_size"] = self.config.getint('audio_processing', 'chunk_size')
        audio_prcssng["min_frequency"] = \
            self.config.getfloat('audio_processing', 'min_frequency')
        audio_prcssng["max_frequency"] = \
            self.config.getfloat('audio_processing', 'max_frequency')
        temp = self.config.get('audio_processing', 'custom_channel_mapping')
        audio_prcssng["custom_channel_mapping"] = \
            map(int, temp.split(',')) if temp else 0
        temp = self.config.get('audio_processing', 'custom_channel_frequencies')
        audio_prcssng["custom_channel_frequencies"] = \
            map(int, temp.split(',')) if temp else 0

        self.audio_processing = Section(audio_prcssng)

    def set_sms(self):
        """
        Retrieves and validates sms configuration loading and parsing it from a file as necessary.
        """
        shrtmssgsrvc = dict(self.config.items('sms'))
        self.who_can["all"] = set()
        shrtmssgsrvc['commands'] = _as_list(self.config.get('sms', 'commands'))
        shrtmssgsrvc['throttle_time_limit_seconds'] = int(
            self.config.get('sms', 'throttle_time_limit_seconds'))

        shrtmssgsrvc['enable'] = self.config.getboolean('sms', 'enable')
        shrtmssgsrvc['groups'] = _as_list(self.config.get('sms', 'groups'))
        shrtmssgsrvc['blacklist'] = _as_list(self.config.get('sms', 'blacklist'))
        shrtmssgsrvc['unknown_command_response'] = self.config.get('sms',
                                                                   'unknown_command_response')
        shrtmssgsrvc['list_songs_per_sms'] = self.config.getint('sms', 'list_songs_per_sms')
        shrtmssgsrvc['list_songs_per_page'] = self.config.getint('sms', 'list_songs_per_page')

        playlist_path = self.config.get('lightshow', 'playlist_path')
        playlist_path = playlist_path.replace('$SYNCHRONIZED_LIGHTS_HOME', self.home_dir)

        if playlist_path:
            shrtmssgsrvc["playlist_path"] = playlist_path
        else:
            shrtmssgsrvc["playlist_path"] = "/home/pi/music/.playlist"

        # Commands
        for cmd in shrtmssgsrvc['commands']:
            try:
                shrtmssgsrvc[cmd + '_aliases'] = _as_list(shrtmssgsrvc[cmd + '_aliases'])
            except KeyError:
                shrtmssgsrvc[cmd + '_aliases'] = []
            self.who_can[cmd] = set()

        # Groups / Permissions
        shrtmssgsrvc['throttled_groups'] = dict()
        for group in shrtmssgsrvc['groups']:
            try:
                shrtmssgsrvc[group + '_users'] = _as_list(shrtmssgsrvc[group + '_users'])
            except KeyError:
                shrtmssgsrvc[group + '_users'] = []

            try:
                shrtmssgsrvc[group + '_commands'] = _as_list(shrtmssgsrvc[group + '_commands'])
            except KeyError:
                shrtmssgsrvc[group + '_commands'] = []

            for cmd in shrtmssgsrvc[group + '_commands']:
                for user in shrtmssgsrvc[group + '_users']:
                    self.who_can[cmd].add(user)

            # Throttle
            try:
                throttled_group_definitions = _as_list(shrtmssgsrvc[group + '_throttle'])
                throttled_group = dict()

                for definition in throttled_group_definitions:
                    definition = definition.split(':')

                    if len(definition) != 2:
                        gtd = "_throttle definitions should be in the form [command]:<limit> - "
                        warnings.warn(group + gtd + ":".join(definition))
                        continue

                    throttle_command = definition[0]
                    throttle_limit = int(definition[1])
                    throttled_group[throttle_command] = throttle_limit

                shrtmssgsrvc['throttled_groups'][group] = throttled_group
            except KeyError:
                warnings.warn(
                    "Throttle definition either does not exist or is configured" +
                    "incorrectly for group: " + group)

        shrtmssgsrvc["log_level"] = self.config.get('sms', 'log_level').upper()

        self.sms = Section(shrtmssgsrvc)

    def get_playlist(self, play_list=None):
        play_list = play_list or self.playlist_path

        with open(play_list, 'rb') as playlist_fp:
            fcntl.lockf(playlist_fp, fcntl.LOCK_SH)
            playlist = csv.reader(playlist_fp, delimiter='\t')
            songs = list()

            for song in playlist:
                if len(song) < 2 or len(song) > 4:
                    log.error('Invalid playlist.  Each line should be in the form: '
                              '<song name><tab><path to song>')
                    log.warning('Removing invalid entry')
                    print "Error found in playlist"
                    print "Deleting entry:", song
                    continue

                elif len(song) > 2:
                    song[2] = set(song[2].split(','))

                elif len(song) == 2:
                    song.append(set())

                songs.append(song)

            fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

        self.playlist = songs

        return songs

    def set_playlist(self, songs):
	self.playlist = songs

    def write_playlist(self, songs, playlist=None):
        playlist = playlist or self.playlist_path

        with open(playlist, 'wb') as playlist_fp:
            fcntl.lockf(playlist_fp, fcntl.LOCK_EX)
            writer = csv.writer(playlist_fp, delimiter='\t')

            for song in songs:
                if len(song[2]) > 0:
                    song[2] = ",".join(song[2])
                else:
                    del song[2]

            writer.writerows(songs)
            fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

	self.playlist = songs

    def has_permission(self, user, cmd):
        """Returns True if a user has permission to execute the given command
        :param user: the user trying to execute the command
        :type user: str

        :param cmd: the command at question
        :type cmd: str

        :return: user has permission
        :rtype: bool
        """
        blacklisted = user in self.sms.blacklist
        return not blacklisted and (user in self.who_can['all']
                                    or 'all' in self.who_can[cmd]
                                    or user in self.who_can[cmd])

    def is_throttle_exceeded(self, cmd, user):
        """Returns True if the throttle has been exceeded and False otherwise

        :param cmd: the command at question
        :type cmd: str

        :param user: the user trying to execute the command
        :type user: str

        :return: has throttle been exceeded
        :rtype: bool
        """
        # Load throttle STATE
        self.load_state()
        self.throttle_state = ast.literal_eval(self.get_state('throttle', '{}'))
        process_command_flag = -1

        # Analyze throttle timing
        current_time_stamp = datetime.datetime.now()
        throttle_time_limit = self.sms.throttle_time_limit_seconds

        if "throttle_timestamp_start" in self.throttle_state:
            throttle_start_time = datetime.datetime.strptime(
                self.throttle_state['throttle_timestamp_start'], '%Y-%m-%d %H:%M:%S.%f')
        else:
            throttle_start_time = current_time_stamp

        delta = datetime.timedelta(seconds=int(throttle_time_limit))
        throttle_stop_time = throttle_start_time + delta

        # Compare times and see if we need to reset the throttle STATE
        if (current_time_stamp == throttle_start_time) or (throttle_stop_time < current_time_stamp):
            # There is no time recorded or the time 
            # has expired reset the throttle STATE
            self.throttle_state = dict()
            self.throttle_state['throttle_timestamp_start'] = str(current_time_stamp)
            self.update_state('throttle', self.throttle_state)

        # ANALYZE THE THROTTLE COMMANDS AND LIMITS
        all_throttle_limit = -1
        cmd_throttle_limit = -1

        # Check to see what group belongs to starting with the first 
        # group declared
        throttled_group = None
        for group in self.sms.groups:
            user_list = self.sms.get(group + "_users")

            if user in user_list:
                # The user belongs to this group, check if there are any 
                # throttle definitions
                if group in self.sms.throttled_groups:
                    # The group has throttle commands defined, now check if 
                    # the command is defined
                    throttled_commands = self.sms.throttled_groups[group]

                    # Check if all command exists
                    if "all" in throttled_commands:
                        all_throttle_limit = int(throttled_commands['all'])

                    # Check if the command passed is defined
                    if cmd in throttled_commands:
                        cmd_throttle_limit = int(throttled_commands[cmd])

                    # A throttle definition was found, we no longer need to 
                    # check anymore groups
                    if all_throttle_limit != -1 or cmd_throttle_limit != -1:
                        throttled_group = group
                        break

        # Process the throttle settings that were found for the throttled group
        if not throttled_group:
            # No throttle limits were found for any group
            return False
        else:
            # Throttle limits were found, check them against throttle STATE 
            # limits
            if throttled_group in self.throttle_state:
                group_throttle_state = self.throttle_state[throttled_group]
            else:
                group_throttle_state = dict()

            if cmd in group_throttle_state:
                group_throttle_cmd_limit = int(group_throttle_state[cmd])
            else:
                group_throttle_cmd_limit = 0

        # Check to see if we need to apply "all"
        if all_throttle_limit != -1:

            if 'all' in group_throttle_state:
                group_throttle_all_limit = int(group_throttle_state['all'])
            else:
                group_throttle_all_limit = 0

            # Check if "all" throttle limit has been reached
            if group_throttle_all_limit < all_throttle_limit:
                # Not Reached, bump throttle and record
                group_throttle_all_limit += 1
                group_throttle_state['all'] = group_throttle_all_limit
                self.throttle_state[throttled_group] = group_throttle_state
                process_command_flag = False
            else:
                # "all" throttle has been reached we don't want to process 
                # anything else
                return True

        # Check to see if we need to apply "cmd"
        if cmd_throttle_limit != -1:
            if group_throttle_cmd_limit < cmd_throttle_limit:
                # Not reached, bump throttle
                group_throttle_cmd_limit += 1
                group_throttle_state[cmd] = group_throttle_cmd_limit
                self.throttle_state[throttled_group] = group_throttle_state
                process_command_flag = False

        # Record the updated throttle STATE and return
        self.update_state('throttle', self.throttle_state)

        return process_command_flag


class Section(object):
    def __init__(self, config):
        self.config = config
        self.set_values(self.config)

    def set_config(self, config):
        self.config = config
        self.set_values(self.config)

    def get_config(self):
        return self.config

    def set_value(self, key, value):
        setattr(self, key, value)

    def set_values(self, dict_of_items):
        """Create class instance variables from key, value pairs

        :param dict_of_items: a dict containing key, value pairs to set
        :type dict_of_items: dict
        """
        for key, value in dict_of_items.iteritems():
            setattr(self, key, value)

    def get(self, item):
        """Get class instance variables from string

        :param item:
        :type item: str

        :return: object of item type
        :rtype: object
        """
        return getattr(self, item)


if __name__ == "__main__":
    # prints the current configuration
    cm = Configuration()
    sms_cm = Configuration(True)
    print "Home directory set:", HOME_DIR
    print "Config directory set:", CONFIG_DIR
    print "Logs directory set:", LOG_DIR

    print "\nHardware Configuration"
    for h_key, h_value in cm.hardware.config.iteritems():
        print h_key, "=", h_value

    print "\nLightshow Configuration"
    for l_key, l_value in cm.lightshow.config.iteritems():
        print l_key, "=", l_value

    print "\nAudio Processing Configuration"
    for a_key, a_value in cm.audio_processing.config.iteritems():
        print a_key, "=", a_value

    print "\nNetwork Configuration"
    for nkey, nvalue in cm.network.config.iteritems():
        print nkey, "=", nvalue

    print "\nSMS Configuration"
    for s_key, s_value in sms_cm.sms.config.iteritems():
        print s_key, "=", s_value

    for wc_key, wc_value in sms_cm.who_can.iteritems():
        print wc_key, "=", wc_value

    print "\nLED Configuration"
    for lc in cm.configs.led:
        cm.set_led(config_file=lc)
        for led_key, led_value in cm.led.config.iteritems():
            print led_key, "=", led_value

    print "\nTerminal Configuration" 
    for tkey, tvalue in cm.terminal.config.iteritems(): 
        print tkey, "=", tvalue

