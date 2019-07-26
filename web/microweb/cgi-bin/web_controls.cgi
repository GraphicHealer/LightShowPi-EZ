#!/usr/bin/python

#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Ken B

import cgi
import html
import cgitb
import os, stat
import subprocess
import configparser
from time import sleep


cgitb.enable()  # for troubleshooting
form = cgi.FieldStorage()
message = form.getvalue("message", "")

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
volume = subprocess.check_output([HOME_DIR + '/bin/vol'],shell=True).decode()

state_file = HOME_DIR + '/web/microweb/config/webstate.cfg'
state = configparser.RawConfigParser()
state.read_file(open(state_file))
config_file = state.get('microweb','config')
if config_file:
    config_param = '--config=' + config_file + ' '
else:
    config_param = ''
    if os.path.isfile(HOME_DIR + '/config/overrides.cfg'):
        config_file = 'overrides.cfg'
    else:
        config_file = 'defaults.cfg'

cfg_file = HOME_DIR + '/config/' + config_file
cfg = configparser.RawConfigParser()
cfg.read_file(open(cfg_file))
lightshowmode = cfg.get('lightshow','mode')
lightshowstc = cfg.get('lightshow','stream_command_string')

if lightshowmode == "stream-in" and lightshowstc == "pianobar":
    try:
        os.stat('/root/.config/pianobar/ctl')
    except OSError:
        os.system('mkfifo /root/.config/pianobar/ctl')

if message:
    if message == "Volume -":
        if int(volume) - 5 < 0:
            volume = "0"
        else:
            volume = str(int(volume) - 5)
        os.system(HOME_DIR + '/bin/vol ' + volume)
    if message == "Volume +":
        if int(volume) + 5 > 100:
            volume = "100"
        else:
            volume = str(int(volume) + 5)
        os.system(HOME_DIR + '/bin/vol ' + volume)
    if message == "On":
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        os.system("python ${SYNCHRONIZED_LIGHTS_HOME}/py/hardware_controller.py " + config_param + "--state=on")
    if message == "Off":
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        os.system("python ${SYNCHRONIZED_LIGHTS_HOME}/py/hardware_controller.py " + config_param + "--state=off")
        sleep(2)
    if message == "Next" and lightshowmode == "playlist":
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        sleep(1)
    if message == "Next" and lightshowmode == "stream-in" and lightshowstc == "pianobar":
        os.system('echo -n "n" > /root/.config/pianobar/ctl')
        sleep(1)
    if message == "Start":
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        os.popen("${SYNCHRONIZED_LIGHTS_HOME}/bin/play_sms " + config_param + "&")
        os.popen("${SYNCHRONIZED_LIGHTS_HOME}/bin/check_sms " + config_param + "&")
        sleep(1)

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
    <body class="centered-wrapper">
            <h2> LightShowPi Web Controls </h2>

            <table class="centered-content">
            <tr><td>
            <form method="post" action="tools.cgi">
                <input id="tools" type="image" src="/toolsicon64.png" >
            </form>
            </td><td>
            <form method="post" action="settings.cgi">
                <input id="settings" type="image" src="/gearicon64.png" >
            </form>
            </td></tr>
            </table>

            <div id="voldiv">
            <form method="post" action="web_controls.cgi">
                <input id="volDown" type="submit" name="message" value="Volume -">
""")

print ('<div id="volumediv" class="centered-content">' + volume + '</div>')

print ("""
                <input id="volUp" type="submit" name="message" value="Volume +">
            </form>
            </div>
""")
if lightshowmode == "playlist":
    print ("""
            <form method="post" action="playlist.cgi">
                <input id="playlist" type="submit" value="Playlist">
            </form>
""")
print ("""
            <form method="post" action="web_controls.cgi">
                <input type="hidden" name="message" value="On"/>
                <input id="on" type="submit" value="Lights ON">
            </form>
            
            <form method="post" action="web_controls.cgi">
                <input type="hidden" name="message" value="Off"/>
                <input id="off" type="submit" value="Lights OFF">
            </form>
""")

cmd = 'pgrep -f "python $SYNCHRONIZED_LIGHTS_HOME/py/synchronized_lights.py"'
if os.system(cmd) == 0:
    try:
        with open(HOME_DIR + '/logs/now_playing.txt') as f: now_playing = f.read()
    except IOError:
        now_playing = None
        pass
    print ("""
        <form method="post" action="web_controls.cgi">
            <input type="hidden" name="message" value="Next"/>
            <input id="next" type="submit" value="Play Next">
        </form>
""")
else:
    now_playing = None
    print ("""
        <form method="post" action="web_controls.cgi">
            <input type="hidden" name="message" value="Start"/>
            <input id="start" type="submit" value="START">
        </form>
""")

if message:
    print ("""<h2>Executed command: %s</h2>""" % html.escape(message))

if now_playing:
    print ("""<h3>%s<h3>""" % html.escape(now_playing))

print ("</body></html>")
