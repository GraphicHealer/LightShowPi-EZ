#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Todd Giles (todd@lightshowpi.com)
# Author: Tom Enos

# TODO(todd): Refactor the configuration manager into a configuration manager class (to remove
#                  the extensive use of globals currently used).
# TODO(todd): Add a main and allow running configuration manager alone to view the current
#                  configuration, and potentially edit it.
"""
Configuration management for the lightshow.

Configuration files are all located in the <homedir>/config directory. This file contains tools to
manage these configuration files.
"""
# The home directory and configuration directory for the application.

import sys
sys.dont_write_bytecode = True
import ConfigParser
import ast
import datetime
import fcntl
import logging
import os
import warnings
import json


HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
if not HOME_DIR:
    print("Need to setup SYNCHRONIZED_LIGHTS_HOME environment variable, "
          "see readme")
    sys.exit()
    
CONFIG_DIR = HOME_DIR + '/config'
LOG_DIR = HOME_DIR + '/logs'


def _as_list(list_str, delimiter=','):
    """
    Return a list of items from a delimited string (after stripping whitespace).

    :rtype : list, made from string
    :param list_str: string, string to convert to list
    :param delimiter: string, delimiter for list
    """
    return [str.strip(item) for item in list_str.split(delimiter)]


def hardware():
    """
    Retrieves the hardware configuration

    loading and parsing it from a file if necessary.

    :rtype : dictionary, items in config section
    """
    if len(hardware_config) == 0:
        for key, value in CONFIG.items('hardware'):
            hardware_config[key] = value
        hardware_config['gpio_pins'] = [int(pin) for pin in hardware_config['gpio_pins'].split(',')]
        hardware_config['active_low_mode'] = CONFIG.getboolean('hardware', 'active_low_mode')
        hardware_config['pin_modes'] = hardware_config['pin_modes'].split(',')
        hardware_config['gpiolen'] = len(hardware_config['gpio_pins'])
        if len(hardware_config['pin_modes']) == 1:
            hardware_config['pin_modes'] = \
                [hardware_config['pin_modes'][0] for _ in range(hardware_config['gpiolen'])]
        hardware_config['pwm_range'] = int(hardware_config['pwm_range'])
        hardware_config['export_pins'] = CONFIG.getboolean('hardware', 'export_pins')
        
        # Devices
        devices = dict()

        try:
            devices = json.loads(hardware_config['devices'])
        except Exception as e:
            logging.error("devices not defined or not in JSON format." + str(e))

        hardware_config["devices"] = devices
        
    return hardware_config


def lightshow():
    """
    Retrieve the lightshow configuration

    loading and parsing it from a file as necessary.

    :rtype : dictionary, items in config section
    """
    if len(lightshow_config) == 0:
        for key, value in CONFIG.items('lightshow'):
            lightshow_config[key] = value
        lightshow_config['audio_in_channels'] = CONFIG.getint('lightshow', 'audio_in_channels')
        lightshow_config['audio_in_sample_rate'] = \
            CONFIG.getint('lightshow', 'audio_in_sample_rate')
        lightshow_config['always_on_channels'] = \
            [int(channel) for channel in lightshow_config['always_on_channels'].split(',')]
        lightshow_config['always_off_channels'] = \
            [int(channel) for channel in lightshow_config['always_off_channels'].split(',')]
        lightshow_config['invert_channels'] = \
            [int(channel) for channel in lightshow_config['invert_channels'].split(',')]
        lightshow_config['playlist_path'] = \
            lightshow_config['playlist_path'].replace('$SYNCHRONIZED_LIGHTS_HOME', HOME_DIR)
        lightshow_config['randomize_playlist'] = \
            CONFIG.getboolean('lightshow', 'randomize_playlist')

        # setup up preshow
        preshow = None
        if lightshow_config['preshow_configuration'] and not lightshow_config['preshow_script']:
            try:
                preshow = json.loads(lightshow_config['preshow_configuration'])
            except Exception as e:
                logging.error("Preshow_configuration not defined or not in JSON format." + str(e))
        else:
            if os.path.isfile(lightshow_config['preshow_script']):
                preshow = lightshow_config['preshow_script']

        lightshow_config['preshow'] = preshow

        # setup postshow
        postshow = None
        if lightshow_config['postshow_configuration'] and not lightshow_config['postshow_script']:
            try:
                postshow = json.loads(lightshow_config['postshow_configuration'])
            except Exception as e:
                logging.error("Postshow_configuration not defined or not in JSON format." + str(e))
        else:
            if os.path.isfile(lightshow_config['postshow_script']):
                postshow = lightshow_config['postshow_script']

        lightshow_config['postshow'] = postshow

    return lightshow_config


def audio_processing():
    """
    Retrieve the audio_processing configuration

    loading and parsing it from a file as necessary.

    :rtype : dictionary, items in config section
   """
    if len(audio_config) == 0:
        for key, value in CONFIG.items('audio_processing'):
            audio_config[key] = value
        audio_config['min_frequency'] = float(audio_config['min_frequency'])
        audio_config['max_frequency'] = float(audio_config['max_frequency'])
        if audio_config['custom_channel_mapping']:
            audio_config['custom_channel_mapping'] = \
                [int(channel) for channel in audio_config['custom_channel_mapping'].split(',')]
        else:
            audio_config['custom_channel_mapping'] = 0
        if audio_config['custom_channel_frequencies']:
            audio_config['custom_channel_frequencies'] = \
                [int(channel) for channel in audio_config['custom_channel_frequencies'].split(',')]
        else:
            audio_config['custom_channel_frequencies'] = 0
        audio_config['fm'] = CONFIG.getboolean('audio_processing', 'fm')
        audio_config['chunk_size'] = int(audio_config['chunk_size'])
        
    return audio_config


def sms():
    """
    Retrieves and validates sms configuration

    :rtype : dictionary, items in config section
    """
    if len(_SMS_CONFIG) == 0:
        for key, value in CONFIG.items('sms'):
            _SMS_CONFIG[key] = value

        _WHO_CAN['all'] = set()

        # Commands
        _SMS_CONFIG['enable'] = CONFIG.getboolean('sms', 'enable')
        _SMS_CONFIG['commands'] = _as_list(_SMS_CONFIG['commands'])
        for cmd in _SMS_CONFIG['commands']:
            try:
                _SMS_CONFIG[cmd + '_aliases'] = _as_list(_SMS_CONFIG[cmd + '_aliases'])
            except:
                _SMS_CONFIG[cmd + '_aliases'] = []
            _WHO_CAN[cmd] = set()

        # Groups / Permissions
        _SMS_CONFIG['groups'] = _as_list(_SMS_CONFIG['groups'])
        _SMS_CONFIG['throttled_groups'] = dict()
        for group in _SMS_CONFIG['groups']:
            try:
                _SMS_CONFIG[group + '_users'] = _as_list(_SMS_CONFIG[group + '_users'])
            except:
                _SMS_CONFIG[group + '_users'] = []
            try:
                _SMS_CONFIG[group + '_commands'] = _as_list(_SMS_CONFIG[group + '_commands'])
            except:
                _SMS_CONFIG[group + '_commands'] = []
            for cmd in _SMS_CONFIG[group + '_commands']:
                for user in _SMS_CONFIG[group + '_users']:
                    _WHO_CAN[cmd].add(user)

            # Throttle
            try:
                throttled_group_definitions = _as_list(_SMS_CONFIG[group + '_throttle'])
                throttled_group = dict()
                for definition in throttled_group_definitions:
                    definition = definition.split(':')
                    if len(definition) != 2:
                        warnings.warn(group + "_throttle definitions should be in the form "
                                      + "[command]:<limit> - " + ':'.join(definition))
                        continue
                    throttle_command = definition[0]
                    throttle_limit = int(definition[1])
                    throttled_group[throttle_command] = throttle_limit
                _SMS_CONFIG['throttled_groups'][group] = throttled_group
            except:
                warnings.warn("Throttle definition either does not exist or is configured "
                              "incorrectly for group: " + group)

        # Blacklist
        _SMS_CONFIG['blacklist'] = _as_list(_SMS_CONFIG['blacklist'])

    return _SMS_CONFIG


def load_configs(per_song=None):
    """
    Load configuration file

    loads defaults from config directory, and then
    overrides from the same directory cfg file, then from /home/pi/.lights.cfg
    and then from ~/.lights.cfg (which will be the root's home).
    if per_song is specified loads these configs also

    :param per_song: string, path and filename of per song config
    """
    global hardware_config, lightshow_config, audio_config, _SMS_CONFIG, _WHO_CAN, CONFIG
    hardware_config = dict()
    lightshow_config = dict()
    audio_config = dict()
    _SMS_CONFIG = dict()
    _WHO_CAN = dict()
    
    CONFIG = ConfigParser.RawConfigParser(allow_no_value=True)
    CONFIG.readfp(open(CONFIG_DIR + '/defaults.cfg'))
    CONFIG.read([CONFIG_DIR + '/overrides.cfg', '/home/pi/.lights.cfg',
                os.path.expanduser('~/.lights.cfg')])
    if per_song:
        CONFIG.read([per_song])

    hardware()
    lightshow()
    audio_processing()
    sms()
load_configs()


def per_song_config(song=None):
    """
    Trigger reloading the configs with per song configuration
    
    :param song: string, path and filename of per song config
    """
    load_configs(song)

_SONG_LIST = []


def songs(playlist_file=None):
    """
    Retrieve the song list

    :rtype : list of lists, playlist data
    :param playlist_file: string, path and filename of playlist
    """
    if playlist_file is not None:
        with open(playlist_file, 'r') as playlist_fp:
            fcntl.lockf(playlist_fp, fcntl.LOCK_SH)
            playlist = []
            for song in playlist_fp.readlines():
                if len(song) < 2 or len(song) > 4:
                    logging.warn('Invalid playlist enrty.  Each line should be in the form: '
                                 '<song name><tab><path to song>')
                    continue
                playlist.append(song.strip().split('\t'))
            fcntl.lockf(playlist_fp, fcntl.LOCK_UN)
        set_songs(playlist)
    return _SONG_LIST


def update_songs(playlist_file, playlist):
    """
    Update the song list

    :param playlist_file: string, path and filename of playlist
    :param playlist: list of lists, playlist data
    """
    with open(playlist_file, 'w') as playlist_fp:
        fcntl.lockf(playlist_fp, fcntl.LOCK_EX)
        for song in playlist:
            playlist_fp.write('\t'.join(song) + "\r\n")
    set_songs(playlist)


def set_songs(song_list):
    """
    Sets the list of songs

    :param song_list: list of lists, playlist data
    """
    global _SONG_LIST
    _SONG_LIST = song_list


##############################
# Application State Utilities
##############################

# Load application state configuration file from CONFIG directory.
STATE = ConfigParser.RawConfigParser()
STATE_SECTION = 'do_not_modify'
STATE_FILENAME = CONFIG_DIR + '/state.cfg'

# Ensure state file has been created
if not os.path.isfile(STATE_FILENAME):
    open(STATE_FILENAME, 'a').close()


def load_state():
    """Force the state to be reloaded form disk."""
    with open(STATE_FILENAME) as state_fp:
        fcntl.lockf(state_fp, fcntl.LOCK_SH)
        STATE.readfp(state_fp, STATE_FILENAME)
        fcntl.lockf(state_fp, fcntl.LOCK_UN)
# Do an initial load
load_state()


def get_state(name, default=''):
    """
    Get application state

    Return the value of a specific application state variable, or the specified
    default if not able to load it from the state file
    :rtype : string, specific application state variable or default
    :param name: string, section name
    :param default: object, value to return if not able to load it from the state file
    """
    try:
        return STATE.get(STATE_SECTION, name)
    except:
        return default


def update_state(name, value):
    """
    Update the application state (name / value pair)

    :param name: string, section name
    :param value: int or string, value to store in application state
    """
    value = str(value)
    logging.info('Updating application state {%s: %s}', name, value)
    try:
        STATE.add_section(STATE_SECTION)
    except ConfigParser.DuplicateSectionError:
        pass  # Ok, it's already there
    STATE.set(STATE_SECTION, name, value)
    with open(STATE_FILENAME, 'wb') as state_fp:
        fcntl.lockf(state_fp, fcntl.LOCK_EX)
        STATE.write(state_fp)
        fcntl.lockf(state_fp, fcntl.LOCK_UN)


def has_permission(user, cmd):
    """
    Returns True iff a user has permission to execute the given command

    :rtype : boolean, is the user blacklisted
    :param user: string, user in user list
    :param cmd: string command in command list
    """
    blacklisted = user in sms()['blacklist']
    return not blacklisted and (user in _WHO_CAN['all']
                                or 'all' in _WHO_CAN[cmd]
                                or user in _WHO_CAN[cmd])


def is_throttle_exceeded(cmd, user):
    """
    Returns True if the throttle has been exceeded and False otherwise

    :rtype : boolean, True is throttle has been exceeded
    :param cmd: string, user in user list
    :param user: string command in command list
    """
    # Load throttle STATE
    load_state()
    throttle_state = ast.literal_eval(get_state('throttle', '{}'))
    process_command_flag = -1

    # Analyze throttle timing
    current_time_stamp = datetime.datetime.now()
    throttle_time_limit = _SMS_CONFIG['throttle_time_limit_seconds']
    throttle_start_time = datetime.datetime.strptime(
        throttle_state['throttle_timestamp_start'], '%Y-%m-%d %H:%M:%S.%f') \
        if "throttle_timestamp_start" in throttle_state else current_time_stamp
    throttle_stop_time = throttle_start_time + datetime.timedelta(seconds=int(throttle_time_limit))

    # Compare times and see if we need to reset the throttle STATE
    if (current_time_stamp == throttle_start_time) or (throttle_stop_time < current_time_stamp):
        # There is no time recorded or the time has
        # expired reset the throttle STATE
        throttle_state = dict()
        throttle_state['throttle_timestamp_start'] = str(current_time_stamp)
        update_state('throttle', throttle_state)

    # ANALYZE THE THROTTLE COMMANDS AND LIMITS
    all_throttle_limit = -1
    cmd_throttle_limit = -1

    # Check to see what group belongs to starting with the first group declared
    throttled_group = None
    for group in _SMS_CONFIG['groups']:
        user_list = _SMS_CONFIG[group + "_users"]
        if user in user_list:
            # The user belongs to this group, check if there
            # are any throttle definitions
            if group in _SMS_CONFIG['throttled_groups']:
                # The group has throttle commands defined,
                # now check if the command is defined
                throttled_commands = _SMS_CONFIG['throttled_groups'][group]

                # Check if all command exists
                if "all" in throttled_commands:
                    all_throttle_limit = int(throttled_commands['all'])

                # Check if the command passed is defined
                if cmd in throttled_commands:
                    cmd_throttle_limit = int(throttled_commands[cmd])

                # A throttle definition was found,
                # we no longer need to check anymore groups
                if all_throttle_limit != -1 or cmd_throttle_limit != -1:
                    throttled_group = group
                    break

    # Process the throttle settings that were found for the throttled group
    if not throttled_group:
        # No throttle limits were found for any group
        return False
    else:
        # Throttle limits were found, check them against throttle STATE limits
        group_throttle_state = \
            throttle_state[throttled_group] if throttled_group in throttle_state else {}
        group_throttle_cmd_limit = \
            int(group_throttle_state[cmd]) if cmd in group_throttle_state else 0

    # Check to see if we need to apply "all"
    if all_throttle_limit != -1:
        group_throttle_all_limit = \
            int(group_throttle_state['all']) if 'all' in group_throttle_state else 0

        # Check if "all" throttle limit has been reached
        if group_throttle_all_limit < all_throttle_limit:
            # Not Reached, bump throttle and record
            group_throttle_all_limit += 1
            group_throttle_state['all'] = group_throttle_all_limit
            throttle_state[throttled_group] = group_throttle_state
            process_command_flag = False
        else:
            # "all" throttle has been reached we
            # dont want to process anything else
            return True

    # Check to see if we need to apply "cmd"
    if cmd_throttle_limit != -1:
        if group_throttle_cmd_limit < cmd_throttle_limit:
            # Not reached, bump throttle
            group_throttle_cmd_limit += 1
            group_throttle_state[cmd] = group_throttle_cmd_limit
            throttle_state[throttled_group] = group_throttle_state
            process_command_flag = False

    # Record the updated_throttle STATE and return
    update_state('throttle', throttle_state)

    return process_command_flag
