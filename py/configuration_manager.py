#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Todd Giles (todd@lightshowpi.com)
#
# TODO(todd): Refactor the configuration manager into a configuration manager class (to remove
#                  the extensive use of globals currently used).
# TODO(todd): Add a main and allow running configuration manager alone to view the current
#                  configuration, and potentially edit it.
"""Configuration management for the lightshow.

Configuration files are all located in the <homedir>/config directory. This file contains tools to
manage these configuration files.
"""
# The home directory and configuration directory for the application.

import ConfigParser
import ast
import datetime
import fcntl
import logging
import os
import sys
import warnings


HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
if not HOME_DIR:
    print("Need to setup SYNCHRONIZED_LIGHTS_HOME environment variable, "
          "see readme")
    sys.exit()
CONFIG_DIR = HOME_DIR + '/config'
LOG_DIR = HOME_DIR + '/logs'

# Load configuration file, loads defaults from config directory, and then
# overrides from the same directory cfg file, then from /home/pi/.lights.cfg
# and then from ~/.lights.cfg (which will be the root's home).
CONFIG = ConfigParser.RawConfigParser()
CONFIG.readfp(open(CONFIG_DIR + '/defaults.cfg'))
CONFIG.read([CONFIG_DIR + '/overrides.cfg', '/home/pi/.lights.cfg',
             os.path.expanduser('~/.lights.cfg')])

def _as_dict(section):
    '''Return a dictionary from a configuration section.'''
    return dict(x for x in CONFIG.items(section))

def _as_list(list_str, delimiter=','):
    '''Return a list of items from a delimited string (after stripping whitespace).'''
    return [str.strip(item) for item in list_str.split(delimiter)]

# Retrieve light show configuration
_LIGHTSHOW_CONFIG = {}
def lightshow():
    '''Retrieves the lightshow configuration, loading and parsing it from a file if necessary.'''
    global _LIGHTSHOW_CONFIG
    if len(_LIGHTSHOW_CONFIG) == 0:
        _LIGHTSHOW_CONFIG = _as_dict('lightshow')

        # Parse out the preshow and replace it with the preshow CONFIG
        # consiting of transitions to on or off for various durations.
        preshow = dict()
        preshow['transitions'] = []
        for transition in _as_list(_LIGHTSHOW_CONFIG['preshow']):
            try:
                transition = transition.split(':')
                if len(transition) != 2:
                    logging.error("Preshow transition definition should be in the form"
                                  " [on|off]:<duration> - " + transition.join(':'))
                    continue
                transition_config = dict()
                transition_type = str(transition[0]).lower()
                if not transition_type in ['on', 'off']:
                    logging.error("Preshow transition transition_type must either 'on'"
                          "or 'off': " + transition_type)
                    continue
                transition_config['type'] = transition_type
                transition_config['duration'] = float(transition[1])
                preshow['transitions'].append(transition_config)
            except:
                logging.error("Invalid preshow transition definition: " + transition.join(':'),)
        _LIGHTSHOW_CONFIG['preshow'] = preshow

    return _LIGHTSHOW_CONFIG

_SMS_CONFIG = {}
_WHO_CAN = {}
def sms():
    '''Retrieves and validates sms configuration'''
    global _SMS_CONFIG, _WHO_CAN
    if len(_SMS_CONFIG) == 0:
        _SMS_CONFIG = _as_dict('sms')
        _WHO_CAN = dict()
        _WHO_CAN['all'] = set()

        # Commands
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
                          + "[command]:<limit> - " + definition.join(':'))
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

_SONG_LIST = []
def songs():
    '''Retrieve the song list'''
    if len(_SONG_LIST) == 0:
        pass  # TODO(todd): Load playlist if not already loaded, also refactor the code
              #             that loads the playlist in check_sms and synchronzied_lights such
              #             that we don't duplicate it there.
    return _SONG_LIST

# Sets the list of songs (if loaded elsewhere, as is done by check_sms)
def set_songs(song_list):
    '''Sets the list of songs (if loaded elsewhere, as is done by check_sms for example)'''
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
    '''Force the state to be reloaded form disk.'''
    with open(STATE_FILENAME) as state_fp:
        fcntl.lockf(state_fp, fcntl.LOCK_SH)
        STATE.readfp(state_fp, STATE_FILENAME)
        fcntl.lockf(state_fp, fcntl.LOCK_UN)
load_state()  # Do an initial load

def get_state(name, default=''):
    '''Return the value of a specific application state variable, or the specified default
    if not able to load it from the state file'''
    try:
        return STATE.get(STATE_SECTION, name)
    except:
        return default

def update_state(name, value):
    '''Update the application state (name / value pair)'''
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
    '''Returns True iff a user has permissio to execute the given command'''
    blacklisted = user in sms()['blacklist']
    return not blacklisted and (user in _WHO_CAN['all']
                                or 'all' in _WHO_CAN[cmd]
                                or user in _WHO_CAN[cmd])

def is_throttle_exceeded(cmd, user):
    '''Returns True if the throttle has been exeeded and False otherwise'''
    # Load throttle STATE
    load_state()
    throttlestate = ast.literal_eval(get_state('throttle', '{}'))
    processcommandflag = -1

    # Analyze throttle timing
    currenttimestamp = datetime.datetime.now()
    throttletimelimit = _SMS_CONFIG['throttle_time_limit_seconds']
    throttlestarttime = datetime.datetime.strptime(
        throttlestate['throttle_timestamp_start'], '%Y-%m-%d %H:%M:%S.%f') \
        if "throttle_timestamp_start" in throttlestate else currenttimestamp
    throttlestoptime = throttlestarttime + datetime.timedelta(seconds=int(throttletimelimit))

    # Compare times and see if we need to reset the throttle STATE
    if (currenttimestamp == throttlestarttime) or (throttlestoptime < currenttimestamp):
        # There is no time recorded or the time has expired reset the throttle STATE
        throttlestate = {}
        throttlestate['throttle_timestamp_start'] = str(currenttimestamp)
        update_state('throttle', throttlestate)

    # ANALYZE THE THROTTLE COMMANDS AND LIMITS
    allthrottlelimit = -1
    cmdthrottlelimit = -1

    # Check to see what group belongs to starting with the first group declared
    throttled_group = None
    for group in _SMS_CONFIG['groups']:
        userlist = _SMS_CONFIG[group + "_users"]
        if user in userlist:
            # The user belongs to this group, check if there are any throttle definitions
            if group in _SMS_CONFIG['throttled_groups']:
                # The group has throttle commands defined, now check if the command is defined
                throttledcommands = _SMS_CONFIG['throttled_groups'][group]

                # Check if all command exists
                if "all" in throttledcommands:
                    allthrottlelimit = int(throttledcommands['all'])

                # Check if the command passed is defined
                if cmd in throttledcommands:
                    cmdthrottlelimit = int(throttledcommands[cmd])

                # A throttle definition was found, we no longer need to check anymore groups
                if allthrottlelimit != -1 or cmdthrottlelimit != -1:
                    throttled_group = group
                    break

    # Process the throttle settings that were found for the throttled group
    if not throttled_group:
        # No throttle limits were found for any group
        return False
    else:
        # Throttle limits were found, check them against throttle STATE limits
        groupthrottlestate = \
          throttlestate[throttled_group] if throttled_group in throttlestate else {}
        groupthrottlecmdlimit = \
          int(groupthrottlestate[cmd]) if cmd in groupthrottlestate else 0

    # Check to see if we need to apply "all"
    if allthrottlelimit != -1:
        groupthrottlealllimit = \
          int(groupthrottlestate['all']) if 'all' in groupthrottlestate else 0

        # Check if "all" throttle limit has been reached
        if groupthrottlealllimit < allthrottlelimit:
            # Not Reached, bump throttle and record
            groupthrottlealllimit = groupthrottlealllimit + 1
            groupthrottlestate['all'] = groupthrottlealllimit
            throttlestate[throttled_group] = groupthrottlestate
            processcommandflag = False
        else:
            # "all" throttle has been reached we dont want to process anything else
            return True

    # Check to see if we need to apply "cmd"
    if cmdthrottlelimit != -1:
        if groupthrottlecmdlimit < cmdthrottlelimit:
            # Not reached, bump throttle
            groupthrottlecmdlimit = groupthrottlecmdlimit + 1
            groupthrottlestate[cmd] = groupthrottlecmdlimit
            throttlestate[throttled_group] = groupthrottlestate
            processcommandflag = False

    # Record the updatedthrottle STATE and return
    update_state('throttle', throttlestate)

    return processcommandflag
