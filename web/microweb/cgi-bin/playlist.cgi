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
import fcntl
import csv
from time import sleep

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
sys.path.insert(0, HOME_DIR + '/py')
import hardware_controller as hc 
cm = hc.cm

cgitb.enable()  # for troubleshooting
form = cgi.FieldStorage()
itemnext = form.getvalue("itemnumber", "")

if itemnext:
    itemnext = int(itemnext) + 1
#    cm.update_state('song_to_play', str(itemnext -1))
    cm.update_state('play_now', str(itemnext))

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
        <center>
            <h2> LightShowPi Web Controls </h2>
            <h3> Playlist </h3>

            <form method="post" action="web_controls.cgi">
                <input id="playlist" type="submit" value="Back">
            </form>

     
""" 

if itemnext:
    itemnext -= 1
else:
    itemnext = int(cm.get_state('song_to_play', "0"))

with open(cm.lightshow.playlist_path, 'rb') as playlist_fp:
    fcntl.lockf(playlist_fp, fcntl.LOCK_SH)
    playlist = csv.reader(playlist_fp, delimiter='\t')
    
    itemnumber = 0
    for song in playlist:
        print '<form method="post" action="playlist.cgi?itemnumber=' + str(itemnumber) + '">'
        if itemnumber == itemnext:
            input_id = 'playnext'
        else:
            input_id = 'playitem'
        print '<input id="' + input_id + '" type="submit" name="item' + str(itemnumber) + '" value="' + song[0] + '">'
        print '</form>'
        itemnumber += 1

    fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

print "</body></html>"
