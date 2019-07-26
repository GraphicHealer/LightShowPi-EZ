#!/usr/bin/python

#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Ken B

import cgi
import cgitb
import os
import sys
import configparser
from time import sleep

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
sys.path.insert(0, HOME_DIR + '/py')
import hardware_controller 

state_file = HOME_DIR + '/web/microweb/config/webstate.cfg'
state = configparser.RawConfigParser()
state.read_file(open(state_file))
config_file = state.get('microweb','config')

hc = hardware_controller.Hardware(param_config=config_file)
cm = hc.cm

cgitb.enable()  # for troubleshooting
form = cgi.FieldStorage()
channelon = form.getvalue("channelon", "")
channeloff = form.getvalue("channeloff", "")
message = form.getvalue("message", "")

if message:
    if message == 'Shutdown':
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        os.system('pkill -f "chromium"')
        sleep(2.0)
#        hc.turn_off_lights()
        os.system("shutdown -h now")
    if message == 'Reboot':
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        os.system('pkill -f "chromium"')
        sleep(2.0)
#        hc.turn_off_lights()
        os.system("reboot")

if channelon:
    hc.initialize(False)
    os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
    os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
    hc.set_light(int(channelon)-1,False,1.0)

if channeloff:
    hc.initialize(False)
    os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
    os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
    hc.set_light(int(channeloff)-1,False,0.0)


print ("Content-type: text/html")
print

print ("""
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>LightShowPi Web Controls</title>
        <meta name="description" content="A very basic web interface for LightShowPi">
        <meta name="author" content="Ken B">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="shortcut icon" href="/favicon.png">
        <meta name="mobile-web-app-capable" content="yes">
        <link rel="icon" sizes="196x196" href="/favicon.png">
        <link rel="apple-touch-icon" sizes="152x152" href="/favicon.png">
        <link rel="stylesheet" href="/css/style.css">
    </head>
    <body>
            <h2> LightShowPi Web Controls </h2>
            <h3> Tools </h3>

            <form method="post" action="web_controls.cgi">
                <input id="playlist" type="submit" value="Back">
            </form>

            <form method="post" action="tools.cgi">
                <input type="hidden" name="message" value="Reboot"/>
                <input id="playlist" type="submit" value="Reboot">
            </form>

            <form method="post" action="tools.cgi" onsubmit="return confirm('Really Shutdown?');">
                <input type="hidden" name="message" value="Shutdown"/>
                <input id="playlist" type="submit" value="Shutdown">
            </form>

     
""") 


print ('<table class="centered-content">')
for channel in range(cm.hardware.gpio_len):
    channel = channel + 1
    print ('<tr>')
    print ('<td>Channel ' + str(channel) + '</td>')
    print ('<td id="onoff"><form method="post" action="tools.cgi?channelon=' + str(channel) + '">')
    print ('<input id="channelonoff" type="submit" name="itemon' + str(channel) + '" value="On">')
    print ('</form></td>')
    print ('<td id="onoff"><form method="post" action="tools.cgi?channeloff=' + str(channel) + '">')
    print ('<input id="channelonoff" type="submit" name="itemoff' + str(channel) + '" value="Off">')
    print ('</form><td>')
    print ('</tr>')

print ('</table>')


print ("</body></html>")
