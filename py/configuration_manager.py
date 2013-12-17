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
