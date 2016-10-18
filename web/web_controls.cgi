#!/usr/bin/python

import cgi
import cgitb; cgitb.enable()  # for troubleshooting
import os
from time import sleep

print "Content-type: text/html"
print

print """
<html>

<head>
<meta charset="utf-8">
<title>LightShowPi Web Controls</title>
<meta name="description" content="A very basic web interface for LightshoPi">
<meta name="author" content="Ken B">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- <link rel="stylesheet" href="">
<link rel="shortcut icon" href="">
<meta name="mobile-web-app-capable" content="yes">
<link rel="icon" sizes="196x196" href="">
<link rel="apple-touch-icon" sizes="152x152" href="">
for future use-->

<style>

h1 {
    font-size: 70px;
}

h2 {
    font-size: 40px;
}

input[type="submit"] {
    width: 400px;
    height: 150px;
    font-size: 50px;     
}

</style>
</head>

<body>
<center>

  <h1> LightShowPi Web Controls </h1>
"""

form = cgi.FieldStorage()
message = form.getvalue("message", "")

print """

<br>
  <form method="post" action="web_controls.cgi">
    <input type="hidden" name="message" value="On"/>
    <input type="submit" value="Lights ON">
  </form>
<br>
  <form method="post" action="web_controls.cgi">
    <input type="hidden" name="message" value="Off"/>
    <input type="submit" value="Lights OFF">
  </form>

""" 

if message:
    if message == "On":
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        os.system("python ${SYNCHRONIZED_LIGHTS_HOME}/py/hardware_controller.py --state=on")
    if message == "Off":
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        os.system("python ${SYNCHRONIZED_LIGHTS_HOME}/py/hardware_controller.py --state=off")
    if message == "Start":
        os.system('pkill -f "bash $SYNCHRONIZED_LIGHTS_HOME/bin"')
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py"')
        os.system("${SYNCHRONIZED_LIGHTS_HOME}/bin/play_sms &")
        os.system("${SYNCHRONIZED_LIGHTS_HOME}/bin/check_sms &")
        sleep(1)

cmd = 'pgrep -f "python $SYNCHRONIZED_LIGHTS_HOME/py/synchronized_lights.py"'
if os.system(cmd) == 0:
    print """
<br>
  <form method="post" action="web_controls.cgi">
    <input type="hidden" name="message" value="Start"/>
    <input type="submit" value="Play Next">
  </form>
    """
else:
    print """
<br>
  <form method="post" action="web_controls.cgi">
    <input type="hidden" name="message" value="Start"/>
    <input type="submit" value="START">
  </form>
    """

if message:
    print """

<br>
<h2>Executed command: %s</h2>

    """ % cgi.escape(message)


print "</body></html>"
