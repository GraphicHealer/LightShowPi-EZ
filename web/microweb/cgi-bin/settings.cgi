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
import subprocess
import ConfigParser
from time import sleep

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
sys.path.insert(0, HOME_DIR + '/py')

state_file = HOME_DIR + '/web/microweb/config/webstate.cfg'
state = ConfigParser.RawConfigParser()
state.readfp(open(state_file))
config_file = state.get('microweb','config')
if config_file:
    config_param = '--config=' + config_file 
else:
    config_param = None


cgitb.enable()  # for troubleshooting
form = cgi.FieldStorage()
message = form.getvalue("message", "")
use_file = form.getvalue("use_file", "")


print "Content-type: text/html"
print

print """
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
            <h3> Settings </h3>

            <form method="post" action="web_controls.cgi">
                <input id="playlist" type="submit" value="Back">
            </form>

            <form method="post" action="settings.cgi">
                <input type="hidden" name="message" value="Show Config"/>
                <input id="playlist" type="submit" value="Show Config">
            </form>

""" 

if use_file:
    config_file = use_file
    state.set('microweb','config',use_file)
    with open(state_file, 'wb') as state_fp:
        state.write(state_fp)

for c_files in os.listdir(HOME_DIR + '/config'):
    if c_files.endswith(".cfg") and "overrides" in c_files:
        print '<form method="post" action="settings.cgi">'
        print '<input type="hidden" name="use_file" value="' + c_files + '"/>'
        if c_files == config_file:
            input_id = "playnext"
        else:
            input_id = "playitem"
        print '<input id="' + input_id + '" type="submit" value="Use ' + c_files + '">'
        print '</form>'

if message:

    if message == 'Show Config':

	if config_param:
            proc = subprocess.Popen(["python", HOME_DIR + "/py/configuration_manager.py", config_param], stdout=subprocess.PIPE)
        else:
            proc = subprocess.Popen(["python", HOME_DIR + "/py/configuration_manager.py"], stdout=subprocess.PIPE)
        out = proc.communicate()[0]
	print '<pre>'
        print out
        print '</pre>'


print "</body></html>"
