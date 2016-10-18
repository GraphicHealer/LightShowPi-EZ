#!/usr/bin/python

import cgi
import cgitb; cgitb.enable()  # for troubleshooting
import os

print "Content-type: text/html"
print

print """
<html>

<head>
<title>LightShowPi Web Controls</title>
<style>

h1 {
    font-size: 70px;
}

input[type="submit"] {
    width: 300px;
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

  <form method="post" action="web_controls.cgi">
    <input type="hidden" name="message" value="On"/>
    <input type="submit" value="ON">
  </form>

  <form method="post" action="web_controls.cgi">
    <input type="hidden" name="message" value="Off"/>
    <input type="submit" value="OFF">
  </form>

  <form method="post" action="web_controls.cgi">
    <input type="hidden" name="message" value="Start"/>
    <input type="submit" value="START">
  </form>

""" 

if message:
    print """

<p>Executed command: %s</p>

    """ % cgi.escape(message)
    if message == "On":
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py/synchronized_lights.py"')
        os.system("python ${SYNCHRONIZED_LIGHTS_HOME}/py/hardware_controller.py --state=on")
    if message == "Off":
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py/synchronized_lights.py"')
        os.system("python ${SYNCHRONIZED_LIGHTS_HOME}/py/hardware_controller.py --state=off")
    if message == "Start":
        os.system('pkill -f "python $SYNCHRONIZED_LIGHTS_HOME/py/synchronized_lights.py"')
        os.system("python ${SYNCHRONIZED_LIGHTS_HOME}/py/synchronized_lights.py &")

print "</body></html>"
