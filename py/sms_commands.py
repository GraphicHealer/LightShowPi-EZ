#!/usr/bin/env python
#
# Author: Todd Giles (todd.giles@gmail.com)
# 
# Initial admin commands inspired by work done by Chris Usey (chris.usey@gmail.com)
#
# Feel free to use, just send any enhancements back our way ;)

"""SMS commmand definition file.

Available SMS commands must be defined in the configuration file. Each command
must also have a matching function defined in this file with a name in the
form 'def sms_commandname(user, args)'.  For example, the command help would
have a matching function definition for 'def sms_help(user, args)'. The user
argument will include the cell number of the user who made the request
and the 'args' argument is a string containing all the text in the sms message
after the command name itself.  So following the 'help' example, if a user with
the cell phone number 1 (123) 456-7890 texted 'help me please!!!' then the
function sms_help will be called with arguments user = '+11234567890:', and 
args = ' me please!!!'.

The function should return a string that will then be sent back to the user
in a return text message. Return an empty string if you'd rather no text 
message be sent in response to the command.

To install the command, simply instantiate an instance of SmsCommand for the
command you've created (see examples below). Note that new commands may be
defined in their own files if desired.
"""

# standard python imports
import re
import subprocess

# third party imports

# local imports
import configuration_manager as cm
import hardware_controller as hc
import log as l

config = cm.sms()
command_names = config['commands']

# SMS command class. The class keeps track of all commands instantiated, so to
# install a new command, simply instantiate it.
class SmsCommand:
  commands = {}

  def __init__(self, name, func):
    self.name = name.lower()
    if not self.name in command_names:
      raise ValueError(name + ' command not defined in configuration file')
    self.func = func
    SmsCommand.commands[self.name] = self

  def execute(self, user, args):
    return self.func(user, args)

# Attempt to execute a command for the specified user.
def execute(command, user):
  global command_names

  # Deterimine the name of the command and arguments from the full
  # command (taking into account aliases).
  name = ''
  args = ''
  for command_name in command_names:
    if bool(re.match(command_name, command, re.I)):
      name = command_name
      args = command[len(command_name):]
    else:
      try:
        for command_alias in config[command_name + '_aliases']:
          if bool(re.match(command_alias, command, re.I)):
            name = command_name
            args = command[len(command_alias):]
            break
      except KeyError:
        pass # No aliases defined, that's fine - keep looking
    if name:
      break

  # If no command found, assume we're executing the default command
  if not name:
    name = config['default_command']
    args = command

  # Verify this command is installed
  if not name in SmsCommand.commands:
    raise ValueError(name
        + ' command must be installed by calling SmsCommand(\''
        + name + '\', <handler>)')

  # Verify the user has permission to execute this command
  if not cm.hasPermission(user, name):
    return config['unauthorized_response'].format(cmd=name, user=user)

  # Execute the command
  return SmsCommand.commands[name].execute(user, args.strip())

# Returns a list of available commands for the requesting user.
def sms_help(user, args):
  global command_names
  help_msg = "Commands:\n"
  for cmd in command_names:
    if cm.hasPermission(user, cmd):
      help = cm.sms()[cmd + '_description']
      if help:
        help_msg += help + "\n"
  return help_msg
SmsCommand('help', sms_help)

# Lists songs from the playlist
# TODO(toddgiles): Add paging support for large playlists.
def sms_list(user, args):
  songlist = ['Vote by texting the song #:\n']
  division = 0
  index = 1
  for song in cm.songs():
    songlist[division] += str(index) + ' - ' + song[0] + '\n'
    index += 1
    if (index - 1) % 4 == 0:
      division += 1
      songlist.append('')
  return songlist
SmsCommand('list', sms_list)

# Interrupts whatever is going on, and plays the requested song.
def sms_play(user, args):
  if len(args) == 0 or not args.isdigit():
    cm.update_state('play_now', -1)
    return 'Skipping straight ahead to the next show!'
  else:
    song = int(args)
    if song < 1 or song > len(cm.songs()):
      return 'Sorry, the song you requested ' + args + ' is out of range :('
    else:
      cm.update_state('play_now', song)
      return '"' + cm.songs()[song - 1][0] + '" coming right up!'
SmsCommand('play', sms_play)

# Changes the system volume
def sms_volume(user, args):
  # Sanitize the input before passing to volume script
  if '-' in args:
    sanitized_cmd = '-'
  elif '+' in args:
    sanitized_cmd = '+'
  elif args.isdigit():
    vol = int(args)
    if vol < 0 or vol > 100:
      return 'volume must be between 0 and 100'
    sanitized_cmd = str(vol)
  else:
    return cm.sms()['volume_description']

  # Execute the sanitized command and handle result
  volscript = cm.home_dir + '/bin/vol'
  output, error = subprocess.Popen(volscript + ' ' + sanitized_cmd,
      shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if error:
    l.log('volume request failed: ' + str(error))
    return 'volume request failed'
  else:
    return 'volume = ' + str(output)
SmsCommand('volume', sms_volume)

# Casts a vote for the next song to be played.
def sms_vote(user, args):
  if args.isdigit():
    song_num = int(args)
    if user != 'Me' and song_num > 0 and song_num <= len(cm.songs()):
      song = cm.songs()[song_num-1]
      song[2].add(user)
      l.log('Song requested: ' + str(song))
      return 'Thank you for requesting "' + song[0] \
          + '", we\'ll notify you when it starts!'
  else:
    return cm.sms()['unknown_command_response']
SmsCommand('vote', sms_vote)
