# This tool will allow you to convert your old preshow config to the
# new preshow_configuration.
# usage
# python convert_old_preshow_to_new.py

import collections
import json
import os
import sys

print "This will generate a new config file with the old style preshow removed"
print "It will not change any of your existing files, a new files will be added"
print "to your config folder, and you can decide how to use it."
print
question = raw_input("Would you like to proceed? (Y to continue) :")
if not question in ["y", "Y"]:
    sys.exit(0)

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
if not HOME_DIR:
    print("Need to setup SYNCHRONIZED_LIGHTS_HOME environment variable, "
          "see readme")
    sys.exit()

CONFIG_DIR = HOME_DIR + '/config/'

# hack to get the configuration_manager to load from a different directory
path = list(sys.path)

# insert script location and configuration_manager location into path
sys.path.insert(0, HOME_DIR + "/py")

# import the configuration_manager so we save ourselves a lot or work
import configuration_manager as cm

# get a copy of the configuration to work with
config = cm.CONFIG

# the old 
old_preshow = list(config.get('lightshow','preshow').split(','))

# an ordered dict so it looks pretty going back in
preshow = collections.OrderedDict()
preshow['transitions'] = []

# the work horse
for transition in old_preshow:
    transition = transition.split(':')
    if len(transition) == 0 or (len(transition) == 1 and len(transition[0]) == 0):
        continue
    if len(transition) != 2:
        continue
    transition_config = dict()
    transition_type = str(transition[0]).lower()
    if not transition_type in ['on', 'off']:
        continue
    transition_config['type'] = transition_type
    transition_config['duration'] = float(transition[1])
    preshow['transitions'].append(transition_config)

# add the audio option, setting as no audio
preshow['audio_file'] = 'null'

# format preshow_configuration and put it in 
data = "\n" + str(json.dumps(preshow, indent=4))
config.set('lightshow', 'preshow_configuration', data)

# remove old preshow for the last time
config.remove_option('lightshow', 'preshow')

# write new config file to config folder and name new.cfg
with open(CONFIG_DIR + "new.cfg", "w") as new_config:
    config.write(new_config)

# let the user know
print
print "Your updated config file is located in the config folder and named new.cfg"
print "It contains all the info from your current config files, you can delete"
print "any items you do not want or need to override from the defaults.cfg"
print "but all you really new to do is rename it to override.cfg and your ready"
print "to go, if you also has the old_preshow config in .lights.cfg you should"
print "remove that option from that file"

# restore path
sys.path[:] = path



