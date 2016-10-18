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

print "</body></html>"
