#!/usr/bin/python

#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Garrett J

import cgi
import cgitb
import os
import sys
import subprocess
import configparser
import mutagen
import datetime as dt
from crontab import CronTab
from time import sleep

# CRON variables
cron = CronTab(user=True)

for job in cron:
    if job.comment == "start":
        globals()['start'] = job
    if job.comment == "stop":
        globals()['stop'] = job
    if job.comment == "on":
        globals()['on'] = job
    if job.comment == "off":
        globals()['off'] = job

if "start" in globals():
    startTime = dt.time(*list(map(int, str(start).split(' ')[0:2])))
    stopTime = dt.time(*list(map(int, str(stop).split(' ')[0:2])))
    onTime = dt.time(*list(map(int, str(on).split(' ')[0:2])))
    offTime = dt.time(*list(map(int, str(off).split(' ')[0:2])))
else:
    startTime = ''
    stopTime = ''
    onTime = ''
    offTime = ''

cron.remove_all()

micro = cron.new(comment="microweb", command="$SYNCHRONIZED_LIGHTS_HOME/bin/start_microweb >> $SYNCHRONIZED_LIGHTS_HOME/logs/microweb.log 2>&1 &")
start = cron.new(comment="start", command="$SYNCHRONIZED_LIGHTS_HOME/bin/start_music_and_lights >> $SYNCHRONIZED_LIGHTS_HOME/logs/music_and_lights.play 2>&1 &")
stop = cron.new(comment="stop", command="$SYNCHRONIZED_LIGHTS_HOME/bin/stop_music_and_lights >> $SYNCHRONIZED_LIGHTS_HOME/logs/music_and_lights.stop 2>&1 &")
on = cron.new(comment="on", command="python $SYNCHRONIZED_LIGHTS_HOME/py/hardware_controller.py —-state=on >> $SYNCHRONIZED_LIGHTS_HOME/logs/music_and_lights.play 2>&1 &")
off = cron.new(comment="off", command="python $SYNCHRONIZED_LIGHTS_HOME/py/hardware_controller.py —-state=off >> $SYNCHRONIZED_LIGHTS_HOME/logs/music_and_lights.stop 2>&1 &")

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
sys.path.insert(0, HOME_DIR + '/py')

state_file = HOME_DIR + '/web/microweb/config/webstate.cfg'
state = configparser.RawConfigParser()
state.read_file(open(state_file))
config_file = state.get('microweb','config')
if config_file:
    config_param = '--config=' + config_file 
else:
    config_param = None
    config_file = 'defaults.cfg'

cgitb.enable()  # for troubleshooting
form = cgi.FieldStorage()
message = form.getvalue("message", "")


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
            <h3> Schedule </h3>

            <form method="post" action="web_controls.cgi">
                <input id="playlist" type="submit" value="Back">
            </form>
            <p></p>""")

if message:

    if message == 'Save':
        stF = form.getvalue('startTime','').split(':')[0:2]
        spF = form.getvalue('stopTime','').split(':')[0:2]
        onF = form.getvalue('onTime','').split(':')[0:2]
        ofF = form.getvalue('offTime','').split(':')[0:2]
        
        cron.env['SYNCHRONIZED_LIGHTS_HOME'] = HOME_DIR
        
        micro.every_reboot()
        start.setall(dt.time(int(stF[1]),int(stF[0])))
        stop.setall(dt.time(int(spF[1]),int(spF[0])))
        on.setall(dt.time(int(onF[1]),int(onF[0])))
        off.setall(dt.time(int(ofF[1]),int(ofF[0])))
        cron.write()

        startTime = dt.time(*list(map(int, str(start).split(' ')[0:2])))
        stopTime = dt.time(*list(map(int, str(stop).split(' ')[0:2])))
        onTime = dt.time(*list(map(int, str(on).split(' ')[0:2])))
        offTime = dt.time(*list(map(int, str(off).split(' ')[0:2])))

print("""
            <div id="cronlist" class="centered-content">
                <form method="post" action="schedule.cgi">
                    <table>
                        <tbody>
                            <tr>
                                <td>Lights On:</td>
                                <td><input type="time" name="onTime" value=""" +'"'+ str(onTime) +'"'+ """/></td>
                            </tr>
                            <tr>
                                <td>Start Playlist:</td>
                                <td><input type="time" name="startTime" value=""" +'"'+ str(startTime) +'"'+ """/></td>
                            </tr>
                            <tr>
                                <td>Stop Playlist:</td>
                                <td><input type="time" name="stopTime" value=""" +'"'+ str(stopTime) +'"'+ """/></td>
                            </tr>
                            <tr>
                                <td>Lights Off:</td>
                                <td><input type="time" name="offTime" value=""" +'"'+ str(offTime) +'"'+ """/></td>
                            </tr>
                        </tbody>
                    </table>
                    <input type="submit" name="message" value="Save">
                    </p>
                </form>
            </div>

</body></html>
""")
