#!/usr/bin/env python
#
# Author: Todd Giles (todd.giles@gmail.com)
#
# Feel free to use as you'd like, but I'd love to hear back from you on any
# improvements, changes, etc...

"""Configuration management for the lightshow.

Configuration files are all located in the <homedir>/config directory.  This
file contains tools to manage these configuration files.
"""

# standard python imports
import ConfigParser
import fcntl
import os
import datetime
import ast

# third party imports

# local imports
import log as l

# The home directory and configuration directory for the application.
home_dir = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
config_dir = home_dir + '/config'

# Load configuration file, loads defaults from config directory, and then
# overrides from the same directory cfg file, then from /home/pi/.lights.cfg
# and then from ~/.lights.cfg (which will be the root's home).
config = ConfigParser.RawConfigParser()
config.readfp(open(config_dir + '/defaults.cfg'))
config.read([config_dir + '/overrides.cfg',
    'home/pi/.lights.cfg',
     os.path.expanduser('~/.lights.cfg')])

# Load configuration section as dictionary
def _as_dict(section):
  return dict(x for x in config.items(section))

# Retrieve light show configuration
_lightshow_config = {}
def lightshow():
  global _lightshow_config
  if len(_lightshow_config) == 0:
    _lightshow_config = _as_dict('lightshow')
    
    # Parse out the preshow and replace it with the preshow config
    # consiting of transitions to on or off for various durations.
    preshow = dict()
    preshow['transitions'] = []
    for transition in _lightshow_config['preshow'].split(','):
      try:
        transition = transition.split(':')
        if len(transition) != 2:
          l.log("Preshow transition definition should be in the form " 
              + "[on|off]:<duration> - " + transition.join(':'))
          continue
        transition_config = dict()
        type = str(transition[0]).lower()
        if not type in ['on', 'off']:
          l.log("Preshow transition type must either 'on' or 'off': " + type)
          continue
        transition_config['type'] = type
        transition_config['duration'] = float(transition[1])
        preshow['transitions'].append(transition_config)
      except:
        l.log("Unable to parse preshow transition: " + transition.join(':'))
    _lightshow_config['preshow'] = preshow
  
  return _lightshow_config

# Retrieves and validates sms configuration
_sms_config = {}
_who_can = {}
def sms():
  global _sms_config, _who_can
  if len(_sms_config) == 0:
    _sms_config = _as_dict('sms')
    _who_can = dict()
    _who_can['all'] = set()

    # Commands
    _sms_config['commands'] = map(str.strip, _sms_config['commands'].split(','))
    for cmd in _sms_config['commands']:
      try:
        _sms_config[cmd + '_aliases'] = map(str.strip, _sms_config[cmd + '_aliases'].split(','))
      except:
        _sms_config[cmd + '_aliases'] = []
      _who_can[cmd] = set()

    # Groups / Permissions
    _sms_config['groups'] = map(str.strip, _sms_config['groups'].split(','))
    _sms_config['throttled_groups'] = dict()
    for group in _sms_config['groups']:
      try:
        _sms_config[group + '_users'] = map(str.strip, _sms_config[group + '_users'].split(','))
      except:
        _sms_config[group + '_users'] = []
      try:
        _sms_config[group + '_commands'] = map(str.strip, _sms_config[group + '_commands'].split(','))
      except:
        _sms_config[group + '_commands'] = []
      for cmd in _sms_config[group + '_commands']:
        for user in _sms_config[group + '_users']:
          _who_can[cmd].add(user)

      # Throttle
      try:
        throttled_group_definitions = map(str.strip, _sms_config[group + '_throttle'].split(','))
        throttled_group = dict()
        for definition in throttled_group_definitions:
          definition = definition.split(':')
          if len(definition) != 2:
            l.log(group + "_throttle definitions should be in the form "
              + "[command]:<limit> - " + definition.join(':'))
            continue
          throttle_command = definition[0]
          throttle_limit = int(definition[1])
          throttled_group[throttle_command] = throttle_limit
        _sms_config['throttled_groups'][group] = throttled_group
      except:
        l.log("Throttle definition either does not exist or is configured incorrectly for group: " + group)

    # Blacklist
    _sms_config['blacklist'] = map(str.strip, _sms_config['blacklist'].split(','))

  return _sms_config

# Retrieves the songs
_songs = []
def songs():
  global _songs
  if len(_songs) == 0:
    pass # TODO(toddgiles): Load playlist
  return _songs

# Sets the list of songs (if loaded elsewhere, as is done by check_sms)
def set_songs(songs):
  global _songs
  _songs = songs


##############################
# Application State Utilities
##############################

# Load application state configuration file from config directory.
state = ConfigParser.RawConfigParser()
state_section = 'do_not_modify'
state_file = config_dir + '/state.cfg'

# Ensure state file has been created
if not os.path.isfile(state_file):
  open(state_file, 'a').close()

# Force the state to be reloaded from disk
def load_state():
  global state
  with open(state_file) as f:
    fcntl.lockf(f, fcntl.LOCK_SH)
    state.readfp(f, state_file)
    fcntl.lockf(f, fcntl.LOCK_UN)
load_state() # Do an initial load

# Get the value of a specific application state variable, or the specified
# default it not able to load
def get_state(name, default=''):
  global state, state_section
  try:
    return state.get(state_section, name)
  except:
    return default

# Update the application state (name / value pair)
def update_state(name, value):
  global state, state_section, config_dir
  value = str(value)
  l.log('Updating application state: {' + name + ', ' + value + '}', 2)
  try:
    state.add_section(state_section)
  except ConfigParser.DuplicateSectionError:
    pass # Ok, it's already there
  state.set(state_section, name, value)
  with open(state_file, 'wb') as f:
    fcntl.lockf(f, fcntl.LOCK_EX)
    state.write(f)
    fcntl.lockf(f, fcntl.LOCK_UN)

# Returns True iff a user has permission to execute the given command
def hasPermission(user, cmd):
  global _who_can
  blacklisted = user in sms()['blacklist']
  return not blacklisted and (user in _who_can['all']
      or 'all' in _who_can[cmd]
      or user in _who_can[cmd])

# Returns True if the throttle has been exceeded and False if it has not been exceeded or is not throttled
def isThrottleExceeded(cmd, user):
  # Load throttle state
  load_state()
  throttlestate = ast.literal_eval(get_state('throttle_settings','{}'))
  processcommandflag = -1

  # ANALYZE THROTTLE TIMING
  currenttimestamp = datetime.datetime.now()
  throttletimelimit = _sms_config['throttle_time_limit_seconds_seconds']
  throttlestarttime = datetime.datetime.strptime(throttlestate['throttle_timestamp_start'],'%Y-%m-%d %H:%M:%S.%f') if "throttle_timestamp_start" in throttlestate else currenttimestamp
  throttlestoptime = throttlestarttime + datetime.timedelta(seconds=int(throttletimelimit))

  # compare times and see if we need to reset the throttle state
  if ((currenttimestamp == throttlestarttime) or (throttlestoptime < currenttimestamp)):
    # there is no time recorded or the time has expired reset the throttle state
    throttlestate = {}
    throttlestate['throttle_timestamp_start'] = str(currenttimestamp)
    update_state('throttle_settings', throttlestate)

  # ANALYZE THE THROTTLE COMMANDS AND LIMITS
  allthrottlelimit = -1
  cmdthrottlelimit = -1

  # Check to see what group belongs to starting with the first group declared
  for group in _sms_config['groups']:
    userlist = _sms_config[group + "_users"]
    if user in userlist:
      # The user belongs to this group, check if there are any throttle definitions
      if group in _sms_config['throttled_groups']:
        # The group has throttle commands defined, now check if the command is defined
        throttledcommands = _sms_config['throttled_groups'][group]
         # Check if all command exists
        if "all" in throttledcommands:
          allthrottlelimit = int(throttledcommands['all']) 

        # Check if the command passed is defined
        if cmd in throttledcommands:
          cmdthrottlelimit = int(throttledcommands[cmd])

        # A throttle was found, we no longer want to check anymore groups
        break

  # PROCESS THE THROTTLE SETTINGS THAT WERE FOUND FOR THE GROUP
  if allthrottlelimit == -1 and cmdthrottlelimit == -1:
    # No throttle limits were found for the group
    return False
  else:
    # Throttle limits were found, check them against throttle state limits
    groupthrottlestate = throttlestate[group] if group in throttlestate else {}
    groupthrottlecmdlimit = int(groupthrottlestate[cmd]) if cmd in groupthrottlestate else 0

  # Check to see if we need to apply "all"
  if allthrottlelimit != -1:
    groupthrottlealllimit = int(groupthrottlestate['all']) if 'all' in groupthrottlestate else 0

    # Check if "all" throttle limit has been reached
    if groupthrottlealllimit < allthrottlelimit:
      # Not Reached, bump throttle and record
      groupthrottlealllimit = groupthrottlealllimit + 1
      groupthrottlestate['all'] = groupthrottlealllimit
      throttlestate[group] = groupthrottlestate
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
      throttlestate[group] = groupthrottlestate
      processcommandflag = False

  # Record the throttle state and return
  update_state('throttle_settings', throttlestate)

  return processcommandflag

